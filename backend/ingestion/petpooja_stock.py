"""PetPooja stock ingestion — raw material closing stock levels.

Uses INVENTORY credentials (different from Orders API).
API endpoint: get_stock_api/
Date param: "date" (NOT "order_date") — BUG 3 from docx.
Response key: "closing_json"
Returns 925 items: {name, price, unit, qty, restaurant_id, category, sapcode}
"""

import logging
from datetime import date, datetime
from typing import Any, Dict, List

import httpx
from sqlalchemy.orm import Session

from config import settings
from models import InventorySnapshot, SyncLog

logger = logging.getLogger("ytip.ingestion.stock")

STOCK_URL = "https://api.petpooja.com/V1/thirdparty/get_stock_api/"
HTTP_TIMEOUT = 30


def _get_inv_credentials(restaurant) -> Dict[str, str]:
    """Resolve Inventory API credentials (different from Orders API)."""
    cfg = restaurant.petpooja_config or {}
    return {
        "app_key": cfg.get("inv_app_key") or settings.petpooja_inv_app_key,
        "app_secret": (
            cfg.get("inv_app_secret") or settings.petpooja_inv_app_secret
        ),
        "access_token": (
            cfg.get("inv_access_token")
            or settings.petpooja_inv_access_token
        ),
        "menuSharingCode": (
            cfg.get("rest_id") or settings.petpooja_rest_id
        ),
    }


def fetch_stock(restaurant, target_date: date) -> List[Dict]:
    """Fetch raw material closing stock for a single date.

    BUG 3: Param is "date" NOT "order_date".
    Response key is "closing_json".
    """
    creds = _get_inv_credentials(restaurant)
    if not creds["app_key"]:
        raise ValueError(
            "Stock API requires inventory credentials. "
            "Set PETPOOJA_INV_APP_KEY / _SECRET / _ACCESS_TOKEN in .env."
        )

    payload = {
        "app_key": creds["app_key"],
        "app_secret": creds["app_secret"],
        "access_token": creds["access_token"],
        "menuSharingCode": creds["menuSharingCode"],
        "date": target_date.strftime("%Y-%m-%d"),
    }

    logger.info(
        "Fetching stock: restaurant=%s date=%s", restaurant.id, target_date
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

    # Response key per docx: "closing_json"
    items = body.get("closing_json", [])
    if not isinstance(items, list):
        items = []

    logger.info(
        "Fetched %d stock items for date=%s", len(items), target_date
    )
    return items


def ingest_stock(
    restaurant, db: Session, target_date: date
) -> int:
    """Fetch closing stock and store as InventorySnapshot records.

    Returns count of new records created.
    """
    sync_log = SyncLog(
        restaurant_id=restaurant.id,
        sync_type="stock",
        status="running",
    )
    db.add(sync_log)
    db.flush()

    try:
        items = fetch_stock(restaurant, target_date)
        created = 0

        for item in items:
            name = str(
                item.get("name", item.get("item_name", "Unknown"))
            ).strip()
            if not name:
                continue

            unit = str(item.get("unit", "kg") or "kg")
            closing = float(item.get("qty", 0) or 0)

            existing = (
                db.query(InventorySnapshot)
                .filter(
                    InventorySnapshot.restaurant_id == restaurant.id,
                    InventorySnapshot.snapshot_date == target_date,
                    InventorySnapshot.item_name == name,
                )
                .first()
            )

            if existing:
                existing.closing_qty = closing
                existing.unit = unit
            else:
                db.add(
                    InventorySnapshot(
                        restaurant_id=restaurant.id,
                        snapshot_date=target_date,
                        item_name=name,
                        unit=unit,
                        opening_qty=0,
                        closing_qty=closing,
                        consumed_qty=0,
                        wasted_qty=0,
                    )
                )
                created += 1

        db.flush()

        sync_log.status = "success"
        sync_log.records_fetched = len(items)
        sync_log.records_created = created
        sync_log.completed_at = datetime.utcnow()
        db.flush()

        logger.info(
            "Stock ingestion OK: date=%s items=%d created=%d",
            target_date,
            len(items),
            created,
        )
        return created

    except Exception as exc:
        sync_log.status = "error"
        sync_log.error_message = str(exc)
        sync_log.completed_at = datetime.utcnow()
        db.flush()
        raise
