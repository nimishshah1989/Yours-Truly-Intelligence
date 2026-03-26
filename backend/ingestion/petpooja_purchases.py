"""PetPooja purchase ingestion — vendor purchases for AvT and vendor price tracking.

Endpoint: get_purchase/
Date format: DD-MM-YYYY (max 1-month range)
Requires Cookie: PETPOOJA_API=...

API response shape:
  purchases[].restaurant_details.receiver.receiver_name → vendor_name
  purchases[].restaurant_details.sender.sender_name → department (outlet)
  purchases[].item_details[] → individual line items

Credentials: sub-outlet inventory credentials.
"""

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple

import httpx
from sqlalchemy.orm import Session

from config import settings
from models import PurchaseOrder, SyncLog

logger = logging.getLogger("ytip.ingestion.purchases")

PURCHASE_URL = "https://api.petpooja.com/V1/thirdparty/get_purchase/"
HTTP_TIMEOUT = 30
PAGE_SIZE = 50


# ---------------------------------------------------------------------------
# Sub-outlet registry
# ---------------------------------------------------------------------------

SUB_OUTLETS = {
    "ytc_store": {
        "code": "sbnip54eox",
        "name": "YTC Store",
        "role": "central_warehouse",
    },
    "ytc_kitchen": {
        "code": "bwd6gaon1k",
        "name": "YTC Kitchen",
        "role": "kitchen",
    },
    "ytc_barista": {
        "code": "xg85t7nm1i",
        "name": "YTC Barista",
        "role": "barista",
    },
    "ytc_bakery": {
        "code": "4vwy1ouxzf",
        "name": "YTC Bakery",
        "role": "bakery",
    },
}


def _to_paisa(value: Any) -> int:
    """Convert INR float/str to paisa int using Decimal for precision."""
    try:
        d = Decimal(str(value))
        return int((d * 100).to_integral_value(rounding=ROUND_HALF_UP))
    except Exception:
        return 0


def _get_sub_outlet_credentials() -> Dict[str, str]:
    """Return sub-outlet API credentials from env vars."""
    return {
        "app_key": settings.petpooja_inv_app_key,
        "app_secret": settings.petpooja_inv_app_secret,
        "access_token": settings.petpooja_inv_access_token,
    }


def _get_cookie() -> str:
    """Return cookie header for purchase API."""
    return settings.petpooja_cookie or ""


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

def _parse_purchase_items(
    purchase: Dict, outlet_code: str
) -> List[Dict]:
    """Flatten a single purchase record into per-item rows.

    Each purchase has restaurant_details (sender/receiver) and item_details[].
    We return one dict per item_detail entry.
    """
    items_out: List[Dict] = []
    rd = purchase.get("restaurant_details", {})
    sender = rd.get("sender", {})
    receiver = rd.get("receiver", {})
    vendor_name = receiver.get("receiver_name", "Unknown").strip()
    department = sender.get("sender_name", "").strip()
    purchase_id = str(purchase.get("purchase_id", ""))
    invoice_number = str(purchase.get("invoice_number", ""))
    invoice_date = str(purchase.get("invoice_date", ""))
    payment = purchase.get("payment", "Unpaid")

    for detail in purchase.get("item_details", []):
        items_out.append({
            "purchase_id": purchase_id,
            "invoice_number": invoice_number,
            "invoice_date": invoice_date,
            "vendor_name": vendor_name,
            "department": department,
            "item_name": str(detail.get("itemname", "Unknown")).strip(),
            "item_id": str(detail.get("item_id", "")),
            "quantity": float(detail.get("qty", 0) or 0),
            "unit": str(detail.get("lbl_unit", "kg") or "kg"),
            "price_per_unit": float(detail.get("price", 0) or 0),
            "total_amount": float(detail.get("amount", 0) or 0),
            "category": str(detail.get("category", "") or ""),
            "payment_status": payment,
            "outlet_code": outlet_code,
        })

    return items_out


# ---------------------------------------------------------------------------
# API fetch with pagination
# ---------------------------------------------------------------------------

def fetch_purchases(
    outlet_code: str,
    start_date: date,
    end_date: date,
    creds: Optional[Dict[str, str]] = None,
    cookie: Optional[str] = None,
) -> List[Dict]:
    """Fetch all purchase records for an outlet in a date range.

    Uses refId-based pagination (50 per page).
    Returns flattened per-item rows.
    """
    if creds is None:
        creds = _get_sub_outlet_credentials()
    if cookie is None:
        cookie = _get_cookie()

    all_items: List[Dict] = []
    ref_id = ""
    page = 0

    while True:
        page += 1
        payload = {
            "app_key": creds["app_key"],
            "app_secret": creds["app_secret"],
            "access_token": creds["access_token"],
            "menuSharingCode": outlet_code,
            "from_date": start_date.strftime("%d-%m-%Y"),
            "to_date": end_date.strftime("%d-%m-%Y"),
            "refId": ref_id,
        }

        headers = {}
        if cookie:
            headers["Cookie"] = cookie

        try:
            with httpx.Client(timeout=HTTP_TIMEOUT) as client:
                resp = client.post(
                    PURCHASE_URL, json=payload, headers=headers
                )
        except httpx.RequestError as exc:
            raise RuntimeError(f"Purchase API network error: {exc}") from exc

        if resp.status_code != 200:
            raise RuntimeError(f"Purchase API HTTP {resp.status_code}")

        body = resp.json()
        if str(body.get("success", "0")) != "1":
            msg = body.get("message", "unknown")
            if "no record" in msg.lower() or "no data" in msg.lower():
                break
            raise RuntimeError(f"Purchase API error: {msg}")

        purchases = body.get("purchases", [])
        if not isinstance(purchases, list) or not purchases:
            break

        for p in purchases:
            all_items.extend(_parse_purchase_items(p, outlet_code))

        if len(purchases) < PAGE_SIZE:
            break

        # Use last purchase_id as refId for next page
        last_id = str(purchases[-1].get("purchase_id", ""))
        if not last_id or last_id == ref_id:
            break
        ref_id = last_id

    logger.info(
        "Fetched %d item rows from outlet=%s from=%s to=%s (pages=%d)",
        len(all_items), outlet_code, start_date, end_date, page,
    )
    return all_items


# ---------------------------------------------------------------------------
# DB upsert
# ---------------------------------------------------------------------------

def _upsert_purchase_items(
    items: List[Dict], restaurant_id: int, db: Session
) -> int:
    """Upsert flattened purchase items into purchase_orders table.

    Dedup key: (restaurant_id, purchase_id, item_name, outlet_code)
    Returns count of newly created records.
    """
    created = 0

    for item in items:
        purchase_id = item.get("purchase_id", "")
        item_name = item.get("item_name", "Unknown")
        outlet_code = item.get("outlet_code", "")

        # Parse date
        raw_date = item.get("invoice_date", "")
        try:
            if "-" in str(raw_date) and len(str(raw_date).split("-")[0]) == 4:
                order_date = datetime.strptime(str(raw_date), "%Y-%m-%d").date()
            else:
                order_date = datetime.strptime(str(raw_date), "%d-%m-%Y").date()
        except (ValueError, TypeError):
            order_date = date.today()

        unit_cost = _to_paisa(item.get("price_per_unit", 0))
        total_cost = _to_paisa(item.get("total_amount", 0))

        # Dedup check
        existing = (
            db.query(PurchaseOrder)
            .filter(
                PurchaseOrder.restaurant_id == restaurant_id,
                PurchaseOrder.purchase_id == purchase_id,
                PurchaseOrder.item_name == item_name,
                PurchaseOrder.outlet_code == outlet_code,
            )
            .first()
        )

        if existing:
            existing.quantity = item.get("quantity", 0)
            existing.unit = item.get("unit", "kg")
            existing.unit_cost = unit_cost
            existing.total_cost = total_cost
            existing.vendor_name = item.get("vendor_name", "Unknown")
            existing.payment_status = item.get("payment_status", "Unpaid")
        else:
            db.add(PurchaseOrder(
                restaurant_id=restaurant_id,
                purchase_id=purchase_id,
                vendor_name=item.get("vendor_name", "Unknown"),
                item_name=item_name,
                quantity=item.get("quantity", 0),
                unit=item.get("unit", "kg"),
                category=item.get("category", ""),
                unit_cost=unit_cost,
                total_cost=total_cost,
                order_date=order_date,
                invoice_number=item.get("invoice_number", ""),
                payment_status=item.get("payment_status", "Unpaid"),
                outlet_code=outlet_code,
                department=item.get("department", ""),
                status="delivered",
            ))
            created += 1

    db.flush()
    return created


# ---------------------------------------------------------------------------
# High-level ingestion
# ---------------------------------------------------------------------------

def ingest_purchases(
    restaurant_id: int,
    db: Session,
    outlet_code: str,
    start_date: date,
    end_date: date,
    creds: Optional[Dict[str, str]] = None,
    cookie: Optional[str] = None,
) -> Tuple[int, int]:
    """Fetch and upsert purchase records for one outlet.

    Returns (items_fetched, items_created).
    """
    sync_log = SyncLog(
        restaurant_id=restaurant_id,
        sync_type=f"purchases_{outlet_code}",
        status="running",
    )
    db.add(sync_log)
    db.flush()

    try:
        items = fetch_purchases(
            outlet_code, start_date, end_date,
            creds=creds, cookie=cookie,
        )
        created = _upsert_purchase_items(items, restaurant_id, db)

        sync_log.status = "success"
        sync_log.records_fetched = len(items)
        sync_log.records_created = created
        sync_log.completed_at = datetime.utcnow()
        db.flush()

        logger.info(
            "Purchase ingestion OK: outlet=%s from=%s to=%s fetched=%d created=%d",
            outlet_code, start_date, end_date, len(items), created,
        )
        return len(items), created

    except Exception as exc:
        sync_log.status = "error"
        sync_log.error_message = str(exc)
        sync_log.completed_at = datetime.utcnow()
        db.flush()
        raise


def backfill_purchases(
    restaurant_id: int,
    db: Session,
    outlet_code: str,
    start_date: date,
    end_date: date,
    creds: Optional[Dict[str, str]] = None,
    cookie: Optional[str] = None,
) -> int:
    """Backfill purchases in 1-month chunks (API limit).

    Returns total items created.
    """
    total_created = 0
    current = start_date

    while current <= end_date:
        chunk_end = min(current + timedelta(days=30), end_date)
        try:
            _, created = ingest_purchases(
                restaurant_id, db, outlet_code,
                current, chunk_end,
                creds=creds, cookie=cookie,
            )
            db.commit()
            total_created += created
            logger.info(
                "Purchase backfill chunk: outlet=%s %s to %s — %d created",
                outlet_code, current, chunk_end, created,
            )
        except Exception as exc:
            db.rollback()
            logger.error(
                "Purchase backfill chunk FAILED: outlet=%s %s to %s — %s",
                outlet_code, current, chunk_end, exc,
            )
        current = chunk_end + timedelta(days=1)

    return total_created


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )

    from database import SessionLocal
    from models import Restaurant

    db = SessionLocal()
    rest = db.query(Restaurant).filter(Restaurant.is_active == True).first()
    if not rest:
        print("No active restaurant found")
        sys.exit(1)

    days = int(sys.argv[1]) if len(sys.argv) > 1 else 90
    outlet = sys.argv[2] if len(sys.argv) > 2 else "sbnip54eox"
    end = date.today()
    start = end - timedelta(days=days)

    print(f"Backfilling purchases: outlet={outlet} {start} to {end}")
    created = backfill_purchases(rest.id, db, outlet, start, end)
    print(f"Done: {created} purchase line items created")
    db.close()
