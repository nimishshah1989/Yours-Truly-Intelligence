"""PetPooja wastage ingestion — damaged/expired raw materials.

Endpoint: get_sales/ with slType="wastage"
Date format: DD-MM-YYYY (max 1-month range)
Requires Cookie: PETPOOJA_API=...

Response shape:
  sales[].item_details[] → individual wastage line items
  sales[].item_details[].description → reason (e.g. "Damage By Rat")
"""

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple

import httpx
from sqlalchemy.orm import Session

from config import settings

logger = logging.getLogger("ytip.ingestion.wastage")

SALES_URL = "https://api.petpooja.com/V1/thirdparty/get_sales/"
HTTP_TIMEOUT = 30
PAGE_SIZE = 50


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


def _get_cookie() -> str:
    """Return cookie header."""
    return settings.petpooja_cookie or ""


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

def _parse_wastage_items(
    sale: Dict, outlet_code: str
) -> List[Dict]:
    """Flatten a single wastage sale record into per-item rows."""
    items_out: List[Dict] = []
    sale_id = str(sale.get("sale_id", ""))
    invoice_date = str(sale.get("invoice_date", ""))
    created_on = str(sale.get("created_on", ""))

    for detail in sale.get("item_details", []):
        qty = float(detail.get("qty", 0) or 0)
        price = float(detail.get("price", 0) or 0)
        amount = float(detail.get("amount", 0) or 0)

        items_out.append({
            "sale_id": sale_id,
            "invoice_date": invoice_date,
            "item_id": str(detail.get("item_id", "")),
            "item_name": str(detail.get("itemname", "Unknown")).strip(),
            "category": str(detail.get("category", "") or ""),
            "quantity": qty,
            "unit": str(detail.get("lbl_unit", "kg") or "kg"),
            "price_per_unit": price,
            "total_amount_paisa": _to_paisa(amount),
            "description": str(detail.get("description", "") or ""),
            "created_on": created_on,
            "outlet_code": outlet_code,
        })

    return items_out


# ---------------------------------------------------------------------------
# API fetch with pagination
# ---------------------------------------------------------------------------

def fetch_wastage(
    outlet_code: str,
    start_date: date,
    end_date: date,
    creds: Optional[Dict[str, str]] = None,
    cookie: Optional[str] = None,
) -> List[Dict]:
    """Fetch all wastage records for an outlet in a date range.

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
            "slType": "wastage",
        }

        headers = {}
        if cookie:
            headers["Cookie"] = cookie

        try:
            with httpx.Client(timeout=HTTP_TIMEOUT) as client:
                resp = client.post(SALES_URL, json=payload, headers=headers)
        except httpx.RequestError as exc:
            raise RuntimeError(f"Wastage API network error: {exc}") from exc

        if resp.status_code != 200:
            raise RuntimeError(f"Wastage API HTTP {resp.status_code}")

        body = resp.json()
        if str(body.get("success", "0")) != "1":
            msg = body.get("message", "unknown")
            if "no record" in msg.lower() or "no data" in msg.lower():
                break
            raise RuntimeError(f"Wastage API error: {msg}")

        sales = body.get("sales", [])
        if not isinstance(sales, list) or not sales:
            break

        for s in sales:
            all_items.extend(_parse_wastage_items(s, outlet_code))

        if len(sales) < PAGE_SIZE:
            break

        last_id = str(sales[-1].get("sale_id", ""))
        if not last_id or last_id == ref_id:
            break
        ref_id = last_id

    logger.info(
        "Fetched %d wastage items from outlet=%s from=%s to=%s (pages=%d)",
        len(all_items), outlet_code, start_date, end_date, page,
    )
    return all_items


# ---------------------------------------------------------------------------
# DB upsert — uses intelligence models (PetpoojaWastage in schema_v4)
# ---------------------------------------------------------------------------

def _upsert_wastage_items(
    items: List[Dict], restaurant_id: int, db: Session
) -> int:
    """Upsert wastage items into petpooja_wastage table.

    Dedup key: (sale_id, item_id)
    Returns count of newly created records.
    """
    from intelligence.models import PetpoojaWastage

    created = 0

    for item in items:
        sale_id = item.get("sale_id", "")
        item_id = item.get("item_id", "")

        # Parse date
        raw_date = item.get("invoice_date", "")
        try:
            if "-" in str(raw_date) and len(str(raw_date).split("-")[0]) == 4:
                invoice_date = datetime.strptime(str(raw_date), "%Y-%m-%d").date()
            else:
                invoice_date = datetime.strptime(str(raw_date), "%d-%m-%Y").date()
        except (ValueError, TypeError):
            invoice_date = date.today()

        # Parse created_on
        created_on = None
        raw_created = item.get("created_on", "")
        if raw_created:
            try:
                created_on = datetime.strptime(str(raw_created), "%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                pass

        existing = (
            db.query(PetpoojaWastage)
            .filter(
                PetpoojaWastage.sale_id == sale_id,
                PetpoojaWastage.item_id == item_id,
            )
            .first()
        )

        if existing:
            existing.quantity = item.get("quantity", 0)
            existing.price_per_unit = Decimal(str(item.get("price_per_unit", 0)))
            existing.total_amount_paisa = item.get("total_amount_paisa", 0)
        else:
            db.add(PetpoojaWastage(
                restaurant_id=restaurant_id,
                outlet_code=item.get("outlet_code", ""),
                sale_id=sale_id,
                invoice_date=invoice_date,
                item_id=item_id,
                item_name=item.get("item_name", "Unknown"),
                category=item.get("category", ""),
                quantity=item.get("quantity", 0),
                unit=item.get("unit", "kg"),
                price_per_unit=Decimal(str(item.get("price_per_unit", 0))),
                total_amount_paisa=item.get("total_amount_paisa", 0),
                description=item.get("description", ""),
                created_on=created_on,
            ))
            created += 1

    db.flush()
    return created


def ingest_wastage(
    restaurant_id: int,
    db: Session,
    outlet_code: str,
    start_date: date,
    end_date: date,
    creds: Optional[Dict[str, str]] = None,
    cookie: Optional[str] = None,
) -> Tuple[int, int]:
    """Fetch and upsert wastage records for one outlet.

    Returns (items_fetched, items_created).
    """
    from models import SyncLog

    sync_log = SyncLog(
        restaurant_id=restaurant_id,
        sync_type=f"wastage_{outlet_code}",
        status="running",
    )
    db.add(sync_log)
    db.flush()

    try:
        items = fetch_wastage(
            outlet_code, start_date, end_date,
            creds=creds, cookie=cookie,
        )
        created = _upsert_wastage_items(items, restaurant_id, db)

        sync_log.status = "success"
        sync_log.records_fetched = len(items)
        sync_log.records_created = created
        sync_log.completed_at = datetime.utcnow()
        db.flush()

        logger.info(
            "Wastage ingestion OK: outlet=%s from=%s to=%s fetched=%d created=%d",
            outlet_code, start_date, end_date, len(items), created,
        )
        return len(items), created

    except Exception as exc:
        sync_log.status = "error"
        sync_log.error_message = str(exc)
        sync_log.completed_at = datetime.utcnow()
        db.flush()
        raise


def backfill_wastage(
    restaurant_id: int,
    db: Session,
    outlet_code: str,
    start_date: date,
    end_date: date,
    creds: Optional[Dict[str, str]] = None,
    cookie: Optional[str] = None,
) -> int:
    """Backfill wastage in 1-month chunks. Returns total created."""
    total_created = 0
    current = start_date

    while current <= end_date:
        chunk_end = min(current + timedelta(days=30), end_date)
        try:
            _, created = ingest_wastage(
                restaurant_id, db, outlet_code,
                current, chunk_end,
                creds=creds, cookie=cookie,
            )
            db.commit()
            total_created += created
        except Exception as exc:
            db.rollback()
            logger.error(
                "Wastage backfill FAILED: outlet=%s %s to %s — %s",
                outlet_code, current, chunk_end, exc,
            )
        current = chunk_end + timedelta(days=1)

    return total_created
