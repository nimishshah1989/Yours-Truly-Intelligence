"""PetPooja purchase ingestion — vendor purchases for AvT and vendor price tracking.

Endpoint: get_purchase/
Date format: DD-MM-YYYY (max 1-month range)
Requires BOTH cookies: PETPOOJA_API + PETPOOJA_CO

Credentials: same inventory credentials as stock.py
"""

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Tuple

import httpx
from sqlalchemy.orm import Session

from config import settings
from models import PurchaseOrder, SyncLog

logger = logging.getLogger("ytip.ingestion.purchases")

PURCHASE_URL = "https://api.petpooja.com/V1/thirdparty/get_purchase/"
HTTP_TIMEOUT = 30


def _to_paisa(value: Any) -> int:
    """Convert INR float/str to paisa int."""
    try:
        return round(float(value) * 100)
    except (TypeError, ValueError):
        return 0


def _get_inv_credentials(restaurant) -> Dict[str, str]:
    """Resolve Inventory API credentials (same as stock.py)."""
    cfg = restaurant.petpooja_config or {}
    return {
        "app_key": cfg.get("inv_app_key") or settings.petpooja_inv_app_key,
        "app_secret": cfg.get("inv_app_secret") or settings.petpooja_inv_app_secret,
        "access_token": cfg.get("inv_access_token") or settings.petpooja_inv_access_token,
        "menuSharingCode": cfg.get("rest_id") or settings.petpooja_rest_id,
    }


def _get_cookies() -> str:
    """Build cookie header string from settings."""
    parts = []
    if settings.petpooja_cookie:
        parts.append(settings.petpooja_cookie)
    if settings.petpooja_co_cookie:
        parts.append(settings.petpooja_co_cookie)
    return "; ".join(parts)


def fetch_purchases(
    restaurant, start_date: date, end_date: date
) -> List[Dict]:
    """Fetch purchase data for a date range (max 1 month).

    Date format: DD-MM-YYYY (not YYYY-MM-DD).
    Requires both PETPOOJA_API and PETPOOJA_CO cookies.
    """
    creds = _get_inv_credentials(restaurant)
    if not creds["app_key"]:
        raise ValueError(
            "Purchase API requires inventory credentials. "
            "Set PETPOOJA_INV_APP_KEY / _SECRET / _ACCESS_TOKEN in .env."
        )

    cookies = _get_cookies()
    if not cookies:
        raise ValueError(
            "Purchase API requires both cookies. "
            "Set PETPOOJA_COOKIE and PETPOOJA_CO_COOKIE in .env."
        )

    payload = {
        "app_key": creds["app_key"],
        "app_secret": creds["app_secret"],
        "access_token": creds["access_token"],
        "menuSharingCode": creds["menuSharingCode"],
        "from_date": start_date.strftime("%d-%m-%Y"),
        "to_date": end_date.strftime("%d-%m-%Y"),
    }

    headers = {"Cookie": cookies}

    logger.info(
        "Fetching purchases: restaurant=%s from=%s to=%s",
        restaurant.id, start_date, end_date,
    )

    try:
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            resp = client.post(PURCHASE_URL, json=payload, headers=headers)
    except httpx.RequestError as exc:
        raise RuntimeError(f"Purchase API network error: {exc}") from exc

    if resp.status_code != 200:
        raise RuntimeError(f"Purchase API HTTP {resp.status_code}")

    body = resp.json()
    if str(body.get("success", "0")) != "1":
        msg = body.get("message", "unknown")
        if "no data" in msg.lower() or "no purchase" in msg.lower():
            return []
        raise RuntimeError(f"Purchase API error: {msg}")

    # Try known response keys
    items = body.get("purchase_json") or body.get("data") or body.get("purchases") or []
    if not isinstance(items, list):
        items = []

    logger.info(
        "Fetched %d purchase records from=%s to=%s", len(items), start_date, end_date
    )
    return items


def ingest_purchases(
    restaurant, db: Session, start_date: date, end_date: date
) -> Tuple[int, int]:
    """Fetch and upsert PurchaseOrder records.

    Returns (records_fetched, records_created).
    """
    sync_log = SyncLog(
        restaurant_id=restaurant.id,
        sync_type="purchases",
        status="running",
    )
    db.add(sync_log)
    db.flush()

    try:
        items = fetch_purchases(restaurant, start_date, end_date)
        created = 0

        for raw in items:
            vendor = str(raw.get("vendor_name", raw.get("supplier_name", "Unknown"))).strip()
            item_name = str(raw.get("item_name", raw.get("rawmaterialname", "Unknown"))).strip()

            # Parse date — could be DD-MM-YYYY or YYYY-MM-DD
            raw_date = raw.get("date", raw.get("purchase_date", ""))
            try:
                if "-" in str(raw_date) and len(str(raw_date).split("-")[0]) == 4:
                    order_date = datetime.strptime(str(raw_date), "%Y-%m-%d").date()
                else:
                    order_date = datetime.strptime(str(raw_date), "%d-%m-%Y").date()
            except (ValueError, TypeError):
                order_date = start_date

            qty = float(raw.get("quantity", raw.get("qty", 0)) or 0)
            unit = str(raw.get("unit", raw.get("unitname", "kg")) or "kg")
            unit_cost = _to_paisa(raw.get("unit_cost", raw.get("price", 0)))
            total_cost = _to_paisa(raw.get("total_cost", raw.get("amount", 0)))
            if total_cost == 0 and unit_cost > 0 and qty > 0:
                total_cost = int(unit_cost * qty)

            # Upsert by (restaurant_id, vendor_name, item_name, order_date)
            existing = (
                db.query(PurchaseOrder)
                .filter(
                    PurchaseOrder.restaurant_id == restaurant.id,
                    PurchaseOrder.vendor_name == vendor,
                    PurchaseOrder.item_name == item_name,
                    PurchaseOrder.order_date == order_date,
                )
                .first()
            )

            if existing:
                existing.quantity = qty
                existing.unit = unit
                existing.unit_cost = unit_cost
                existing.total_cost = total_cost
            else:
                db.add(PurchaseOrder(
                    restaurant_id=restaurant.id,
                    vendor_name=vendor,
                    item_name=item_name,
                    order_date=order_date,
                    quantity=qty,
                    unit=unit,
                    unit_cost=unit_cost,
                    total_cost=total_cost,
                    status="completed",
                ))
                created += 1

        db.flush()

        sync_log.status = "success"
        sync_log.records_fetched = len(items)
        sync_log.records_created = created
        sync_log.completed_at = datetime.utcnow()
        db.flush()

        logger.info(
            "Purchase ingestion OK: from=%s to=%s fetched=%d created=%d",
            start_date, end_date, len(items), created,
        )
        return len(items), created

    except Exception as exc:
        sync_log.status = "error"
        sync_log.error_message = str(exc)
        sync_log.completed_at = datetime.utcnow()
        db.flush()
        raise


def backfill_purchases(
    restaurant, db: Session, start_date: date, end_date: date
) -> int:
    """Backfill purchases in 1-month chunks (API limit)."""
    total_created = 0
    current = start_date

    while current <= end_date:
        chunk_end = min(current + timedelta(days=30), end_date)
        try:
            _, created = ingest_purchases(restaurant, db, current, chunk_end)
            db.commit()
            total_created += created
            logger.info("Purchase backfill chunk: %s to %s — %d created", current, chunk_end, created)
        except Exception as exc:
            db.rollback()
            logger.error("Purchase backfill chunk FAILED: %s to %s — %s", current, chunk_end, exc)
        current = chunk_end + timedelta(days=1)

    return total_created


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")

    from database import SessionLocal
    from models import Restaurant

    db = SessionLocal()
    rest = db.query(Restaurant).filter(Restaurant.is_active == True).first()
    if not rest:
        print("No active restaurant found")
        sys.exit(1)

    days = int(sys.argv[1]) if len(sys.argv) > 1 else 90
    end = date.today()
    start = end - timedelta(days=days)
    print(f"Backfilling purchases: {start} to {end}")
    created = backfill_purchases(rest, db, start, end)
    print(f"Done: {created} purchase records created")
    db.close()
