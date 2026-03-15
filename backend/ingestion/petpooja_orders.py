"""PetPooja orders ingestion — Phase 1 ETL pipeline.

Fixes all 6 critical bugs from YTIP_Claude_Code_Context.docx:
  BUG 1: Response key is "order_json" NOT "orders"
  BUG 2: T-1 lag — pass D+1 to get day D, filter by order_date == D
  BUG 4: Part Payment — parse Order.part_payment[] array
  BUG 6: Pagination — refId loop until batch < 50
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import httpx
from sqlalchemy.orm import Session

from config import settings
from models import Order, OrderItem, SyncLog

logger = logging.getLogger("ytip.ingestion.orders")

ORDERS_URL = "https://api.petpooja.com/V1/thirdparty/generic_get_orders/"
HTTP_TIMEOUT = 30
PAGE_SIZE = 50

ORDER_TYPE_MAP = {
    "take away": "takeaway",
    "takeaway": "takeaway",
    "delivery": "delivery",
    "pick up": "takeaway",
    "1": "dine_in",
    "2": "takeaway",
    "3": "delivery",
    "dine_in": "dine_in",
}


@dataclass
class SyncResult:
    """Result of a single-date order sync."""

    records_fetched: int = 0
    records_created: int = 0
    records_updated: int = 0
    error: Optional[str] = None


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _to_paisa(value: Any) -> int:
    """Convert INR float/str to paisa int."""
    try:
        return round(float(value) * 100)
    except (TypeError, ValueError):
        return 0


def _get_credentials(restaurant) -> Dict[str, str]:
    """Resolve Orders API credentials from restaurant config or globals."""
    cfg = restaurant.petpooja_config or {}
    return {
        "app_key": cfg.get("app_key") or settings.petpooja_app_key,
        "app_secret": cfg.get("app_secret") or settings.petpooja_app_secret,
        "access_token": cfg.get("access_token") or settings.petpooja_access_token,
        "rest_id": cfg.get("rest_id") or settings.petpooja_rest_id
                    or settings.petpooja_restaurant_id,
    }


# ------------------------------------------------------------------
# Fetch with T-1 correction + pagination (BUG 2 + BUG 6)
# ------------------------------------------------------------------

def fetch_orders(restaurant, target_date: date) -> List[Dict]:
    """Fetch ALL orders for target_date with T-1 correction and pagination.

    BUG 2: PetPooja has a T-1 lag. Pass D+1 as order_date to get day D.
           Then filter the response so only orders with order_date == D remain.
    BUG 6: API caps at 50 records. Loop with refId until batch < 50.
    """
    creds = _get_credentials(restaurant)
    cookie = settings.petpooja_cookie or ""

    # T-1 correction: pass D+1 to get orders for D
    api_date = (target_date + timedelta(days=1)).strftime("%Y-%m-%d")
    target_str = target_date.strftime("%Y-%m-%d")

    all_orders: List[Dict] = []
    ref_id = ""
    page = 0

    while True:
        page += 1
        payload = {
            "app_key": creds["app_key"],
            "app_secret": creds["app_secret"],
            "access_token": creds["access_token"],
            "restID": creds["rest_id"],
            "order_date": api_date,
            "refId": ref_id,
        }

        try:
            with httpx.Client(timeout=HTTP_TIMEOUT) as client:
                resp = client.post(
                    ORDERS_URL, json=payload, headers={"Cookie": cookie}
                )
        except httpx.RequestError as exc:
            raise RuntimeError(f"Orders API network error: {exc}") from exc

        if resp.status_code != 200:
            raise RuntimeError(f"Orders API HTTP {resp.status_code}")

        body = resp.json()
        if str(body.get("success", "0")) != "1":
            msg = body.get("message", "unknown")
            if "no order" in msg.lower() or "no data" in msg.lower():
                break
            raise RuntimeError(f"Orders API error: {msg}")

        # BUG 1: key is "order_json" NOT "orders"
        batch = body.get("order_json", [])
        if not isinstance(batch, list) or not batch:
            break

        all_orders.extend(batch)
        logger.debug(
            "Page %d: %d orders (refId=%s)", page, len(batch), ref_id
        )

        if len(batch) < PAGE_SIZE:
            break

        # Next page: use refId of last record
        last_order = batch[-1].get("Order", {})
        ref_id = str(last_order.get("refId", ""))
        if not ref_id:
            break

    # BUG 2 filter: only keep orders whose order_date matches target
    filtered = [
        o for o in all_orders
        if o.get("Order", {}).get("order_date", "") == target_str
    ]

    logger.info(
        "Fetched orders for date=%s: raw=%d filtered=%d (pages=%d)",
        target_date, len(all_orders), len(filtered), page,
    )
    return filtered


# ------------------------------------------------------------------
# Field mapping
# ------------------------------------------------------------------

def _map_order(raw: Dict, restaurant_id: int, target_date: date) -> Dict:
    """Map raw PetPooja order dict to Order model fields."""
    o = raw.get("Order", {})

    sub_type = str(o.get("sub_order_type", "") or "").strip().lower()
    order_type = ORDER_TYPE_MAP.get(sub_type, "dine_in")

    total_amount = _to_paisa(o.get("total", 0))
    tax_amount = _to_paisa(o.get("tax_total", 0))
    discount_amount = _to_paisa(o.get("discount_total", 0))
    core_total = _to_paisa(o.get("core_total", 0)) or (
        total_amount - tax_amount
    )

    # Timestamp from API
    ordered_at = datetime(
        target_date.year, target_date.month, target_date.day
    )
    created_on = str(o.get("created_on", "")).strip()
    if created_on:
        try:
            ordered_at = datetime.strptime(created_on, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass

    # Status
    raw_status = str(o.get("status", "")).lower()
    is_cancelled = raw_status == "cancelled"
    if raw_status == "complimentary":
        status = "complimentary"
    elif is_cancelled:
        status = "cancelled"
    else:
        status = "completed"

    # BUG 4: Part Payment handling
    payment_mode = str(o.get("payment_type", "") or "cash").lower().strip()
    custom_payment = str(o.get("custom_payment_type", "") or "").strip()
    part_payment_total = 0
    if payment_mode == "part payment":
        parts = o.get("part_payment") or []
        if isinstance(parts, list):
            part_payment_total = sum(
                _to_paisa(p.get("amount", 0))
                for p in parts
                if float(p.get("amount", 0) or 0) > 0
            )

    return {
        "restaurant_id": restaurant_id,
        "petpooja_order_id": str(o.get("refId") or o.get("orderID", "")),
        "order_number": str(o.get("orderID", "")) or None,
        "order_type": order_type,
        "sub_order_type": str(o.get("sub_order_type", "")) or None,
        "platform": "direct",
        "payment_mode": payment_mode or "cash",
        "custom_payment_type": custom_payment or None,
        "status": status,
        "total_amount": total_amount,
        "tax_amount": tax_amount,
        "discount_amount": discount_amount,
        "tip": _to_paisa(o.get("tip", 0)),
        "service_charge": _to_paisa(o.get("service_charge", 0)),
        "waived_off": _to_paisa(
            o.get("waivedOff", o.get("waived_off", 0))
        ),
        "part_payment": part_payment_total,
        "subtotal": core_total,
        "net_amount": total_amount - discount_amount,
        "item_count": len(raw.get("OrderItem", [])),
        "table_number": str(
            o.get("table_no", "") or o.get("sub_order_type", "")
        )
        or None,
        "staff_name": None,
        "is_cancelled": is_cancelled,
        "cancel_reason": None,
        "ordered_at": ordered_at,
    }


def _map_item(
    item: Dict, order_id: int, restaurant_id: int
) -> Dict:
    """Map raw PetPooja OrderItem to OrderItem model fields."""
    unit_price = _to_paisa(item.get("price", 0))
    total_price = _to_paisa(item.get("total", 0)) or unit_price
    quantity = int(item.get("quantity", 1) or 1)
    if quantity < 1:
        quantity = 1

    return {
        "restaurant_id": restaurant_id,
        "order_id": order_id,
        "item_name": str(
            item.get("name", "Unknown")
        ).strip()
        or "Unknown",
        "category": str(
            item.get("categoryname", "Uncategorized")
        ).strip()
        or "Uncategorized",
        "quantity": quantity,
        "unit_price": unit_price,
        "total_price": total_price,
        "item_code": str(item.get("itemcode", "")) or None,
        "special_notes": str(item.get("specialnotes", "")) or None,
        "variation_name": None,
    }


# ------------------------------------------------------------------
# Upsert
# ------------------------------------------------------------------

def _upsert_order(db: Session, fields: Dict) -> Tuple:
    """Insert or update an Order record. Returns (order, was_created)."""
    pp_id = fields["petpooja_order_id"]
    rest_id = fields["restaurant_id"]

    existing = (
        db.query(Order)
        .filter(
            Order.restaurant_id == rest_id,
            Order.petpooja_order_id == pp_id,
        )
        .first()
    )

    if existing is None:
        order = Order(**fields)
        db.add(order)
        db.flush()
        return order, True

    for k, v in fields.items():
        if k not in ("restaurant_id", "petpooja_order_id"):
            setattr(existing, k, v)
    db.flush()
    return existing, False


def _replace_items(
    db: Session,
    order_id: int,
    restaurant_id: int,
    raw_items: List[Dict],
) -> None:
    """Delete existing items for an order then insert fresh ones."""
    db.query(OrderItem).filter(
        OrderItem.order_id == order_id
    ).delete(synchronize_session="fetch")
    for item in raw_items:
        item_fields = _map_item(item, order_id, restaurant_id)
        db.add(OrderItem(**item_fields))
    db.flush()


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def ingest_orders(
    restaurant, db: Session, target_date: date
) -> SyncResult:
    """Fetch and ingest all orders for target_date."""
    sync_log = SyncLog(
        restaurant_id=restaurant.id,
        sync_type="orders",
        status="running",
    )
    db.add(sync_log)
    db.flush()

    result = SyncResult()

    try:
        orders = fetch_orders(restaurant, target_date)
        result.records_fetched = len(orders)

        for raw in orders:
            fields = _map_order(raw, restaurant.id, target_date)
            order, created = _upsert_order(db, fields)

            raw_items = raw.get("OrderItem", [])
            if isinstance(raw_items, list):
                _replace_items(
                    db, order.id, restaurant.id, raw_items
                )

            if created:
                result.records_created += 1
            else:
                result.records_updated += 1

        db.flush()

        sync_log.status = "success"
        sync_log.records_fetched = result.records_fetched
        sync_log.records_created = result.records_created
        sync_log.records_updated = result.records_updated
        sync_log.completed_at = datetime.utcnow()
        db.flush()

        logger.info(
            "Ingestion OK: date=%s fetched=%d created=%d updated=%d",
            target_date,
            result.records_fetched,
            result.records_created,
            result.records_updated,
        )

    except Exception as exc:
        sync_log.status = "error"
        sync_log.error_message = str(exc)
        sync_log.completed_at = datetime.utcnow()
        db.flush()
        result.error = str(exc)
        raise

    return result


def backfill_orders(
    restaurant,
    db: Session,
    start_date: date,
    end_date: date,
) -> List[Tuple[date, SyncResult]]:
    """Backfill orders for [start_date, end_date], committing per day."""
    results: List[Tuple[date, SyncResult]] = []
    current = start_date
    total_days = (end_date - start_date).days + 1
    day_num = 0

    while current <= end_date:
        day_num += 1
        logger.info(
            "Backfill [%d/%d] date=%s restaurant=%s",
            day_num, total_days, current, restaurant.id,
        )
        try:
            result = ingest_orders(restaurant, db, current)
            db.commit()
            logger.info(
                "  OK: fetched=%d created=%d updated=%d",
                result.records_fetched,
                result.records_created,
                result.records_updated,
            )
            results.append((current, result))
        except Exception as exc:
            db.rollback()
            error_msg = str(exc)
            logger.error("  FAILED: %s", error_msg)
            results.append((current, SyncResult(error=error_msg)))
        current += timedelta(days=1)

    return results
