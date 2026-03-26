"""PetPooja stock ingestion — raw material closing stock levels.

Uses INVENTORY credentials (different from Orders API).
API endpoint: get_stock_api/
Date param: "date" (NOT "order_date") — YYYY-MM-DD format.
Response key: "closing_json"

Multi-outlet support: each outlet has its own menuSharingCode.
"""

import logging
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy.orm import Session

from config import settings
from models import InventorySnapshot, SyncLog

logger = logging.getLogger("ytip.ingestion.stock")

STOCK_URL = "https://api.petpooja.com/V1/thirdparty/get_stock_api/"
HTTP_TIMEOUT = 30

# Outlets with stock data
STOCK_OUTLETS = {
    "ytc_store": {"code": "sbnip54eox", "name": "YTC Store"},
    "ytc_barista": {"code": "xg85t7nm1i", "name": "YTC Barista"},
    "ytc_kitchen": {"code": "bwd6gaon1k", "name": "YTC Kitchen"},
    "ytc_bakery": {"code": "4vwy1ouxzf", "name": "YTC Bakery"},
}


def _to_paisa(value: Any) -> int:
    """Convert INR float/str to paisa int."""
    try:
        d = Decimal(str(value))
        return int((d * 100).to_integral_value(rounding=ROUND_HALF_UP))
    except Exception:
        return 0


def _get_sub_outlet_credentials() -> Dict[str, str]:
    """Return sub-outlet API credentials from env."""
    return {
        "app_key": settings.petpooja_inv_app_key,
        "app_secret": settings.petpooja_inv_app_secret,
        "access_token": settings.petpooja_inv_access_token,
    }


def fetch_stock(
    outlet_code: str,
    target_date: date,
    creds: Optional[Dict[str, str]] = None,
) -> List[Dict]:
    """Fetch raw material closing stock for a single date and outlet.

    Date format: YYYY-MM-DD.
    Response key: "closing_json".
    """
    if creds is None:
        creds = _get_sub_outlet_credentials()

    payload = {
        "app_key": creds["app_key"],
        "app_secret": creds["app_secret"],
        "access_token": creds["access_token"],
        "menuSharingCode": outlet_code,
        "date": target_date.strftime("%Y-%m-%d"),
    }

    logger.info(
        "Fetching stock: outlet=%s date=%s", outlet_code, target_date
    )

    try:
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            resp = client.post(STOCK_URL, json=payload)
    except httpx.RequestError as exc:
        raise RuntimeError(f"Stock API network error: {exc}") from exc

    if resp.status_code != 200:
        raise RuntimeError(f"Stock API HTTP {resp.status_code}")

    body = resp.json()
    if str(body.get("success", "0")) != "1":
        raise RuntimeError(
            f"Stock API error: {body.get('message', 'unknown')}"
        )

    items = body.get("closing_json", [])
    if not isinstance(items, list):
        items = []

    logger.info(
        "Fetched %d stock items for outlet=%s date=%s",
        len(items), outlet_code, target_date,
    )
    return items


def _upsert_stock_items(
    items: List[Dict],
    restaurant_id: int,
    target_date: date,
    outlet_code: str,
    db: Session,
) -> int:
    """Upsert stock items into inventory_snapshots with outlet_code.

    Dedup key: (restaurant_id, snapshot_date, item_name, outlet_code)
    Returns count of newly created records.
    """
    created = 0

    for item in items:
        name = str(item.get("name", item.get("item_name", "Unknown"))).strip()
        if not name:
            continue

        unit = str(item.get("unit", "kg") or "kg")
        closing = float(item.get("qty", 0) or 0)
        avg_price = _to_paisa(item.get("price", 0))

        existing = (
            db.query(InventorySnapshot)
            .filter(
                InventorySnapshot.restaurant_id == restaurant_id,
                InventorySnapshot.snapshot_date == target_date,
                InventorySnapshot.item_name == name,
                InventorySnapshot.outlet_code == outlet_code,
            )
            .first()
        )

        if existing:
            existing.closing_qty = closing
            existing.unit = unit
            existing.average_purchase_price = avg_price
        else:
            db.add(InventorySnapshot(
                restaurant_id=restaurant_id,
                snapshot_date=target_date,
                item_name=name,
                unit=unit,
                opening_qty=0,
                closing_qty=closing,
                consumed_qty=0,
                wasted_qty=0,
                outlet_code=outlet_code,
                average_purchase_price=avg_price,
            ))
            created += 1

    db.flush()
    return created


def ingest_stock(
    restaurant_id: int,
    db: Session,
    target_date: date,
    outlet_code: str,
    creds: Optional[Dict[str, str]] = None,
) -> int:
    """Fetch closing stock for one outlet and store as InventorySnapshot records.

    Returns count of new records created.
    """
    sync_log = SyncLog(
        restaurant_id=restaurant_id,
        sync_type=f"stock_{outlet_code}",
        status="running",
    )
    db.add(sync_log)
    db.flush()

    try:
        items = fetch_stock(outlet_code, target_date, creds=creds)
        created = _upsert_stock_items(
            items, restaurant_id, target_date, outlet_code, db
        )

        sync_log.status = "success"
        sync_log.records_fetched = len(items)
        sync_log.records_created = created
        sync_log.completed_at = datetime.utcnow()
        db.flush()

        logger.info(
            "Stock ingestion OK: outlet=%s date=%s items=%d created=%d",
            outlet_code, target_date, len(items), created,
        )
        return created

    except Exception as exc:
        sync_log.status = "error"
        sync_log.error_message = str(exc)
        sync_log.completed_at = datetime.utcnow()
        db.flush()
        raise


def ingest_all_outlets(
    restaurant_id: int,
    db: Session,
    target_date: date,
    creds: Optional[Dict[str, str]] = None,
) -> Dict[str, int]:
    """Fetch stock for ALL sub-outlets and return {outlet_code: count}."""
    results = {}
    for key, outlet in STOCK_OUTLETS.items():
        code = outlet["code"]
        try:
            created = ingest_stock(
                restaurant_id, db, target_date, code, creds=creds,
            )
            db.commit()
            results[code] = created
            logger.info("Stock %s: %d items", outlet["name"], created)
        except Exception as exc:
            db.rollback()
            results[code] = -1
            logger.error("Stock %s FAILED: %s", outlet["name"], exc)
    return results
