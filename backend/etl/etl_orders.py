"""Orders ETL — syncs PetPooja orders for a single date into PostgreSQL.

Uses upsert-by-petpooja_order_id to make syncs idempotent. All monetary
values are stored in paisa (INR × 100) as BigInteger.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from config import settings
from models import Order, OrderItem, SyncLog

from .petpooja_client import PetPoojaClient, PetPoojaError

logger = logging.getLogger("ytip.etl.orders")

# PetPooja sub_order_type → our normalised order_type
ORDER_TYPE_MAP = {
    # New API human-readable sub_order_type values
    "take away": "takeaway",
    "takeaway": "takeaway",
    "delivery": "delivery",
    # Everything else (Dine In, Lawn, Verandah, Hideout, etc.) → dine_in
    # Old numeric codes kept for safety
    "1": "dine_in",
    "2": "takeaway",
    "3": "delivery",
    "dine_in": "dine_in",
}


@dataclass
class SyncResult:
    records_fetched: int = 0
    records_created: int = 0
    records_updated: int = 0
    error: Optional[str] = None


# ------------------------------------------------------------------
# Amount helpers
# ------------------------------------------------------------------

def _to_paisa(value: Any) -> int:
    """Convert a PetPooja monetary value (INR float/str) to paisa int."""
    try:
        return round(float(value) * 100)
    except (TypeError, ValueError):
        return 0


# ------------------------------------------------------------------
# Order mapping
# ------------------------------------------------------------------

def _map_order_fields(
    raw: Dict[str, Any],
    restaurant_id: int,
    target_date: date,
) -> Dict[str, Any]:
    """Map a raw PetPooja API order dict to Order model field values.

    The real API returns a nested structure:
      {"Order": {...}, "OrderItem": [...], "Customer": {}, "Restaurant": {}}
    """
    o = raw.get("Order", {})

    # Determine order type from sub_order_type (more specific than order_type)
    sub_type = str(o.get("sub_order_type", "") or "").strip().lower()
    order_type = ORDER_TYPE_MAP.get(sub_type, "dine_in")

    total_amount = _to_paisa(o.get("total", 0))
    tax_amount = _to_paisa(o.get("tax_total", 0))
    discount_amount = _to_paisa(o.get("discount_total", 0))
    core_total = _to_paisa(o.get("core_total", 0)) or (total_amount - tax_amount)

    # Use actual timestamp from API
    ordered_at = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0)
    created_on = str(o.get("created_on", "")).strip()
    if created_on:
        try:
            ordered_at = datetime.strptime(created_on, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass

    raw_status = str(o.get("status", "")).lower()
    is_cancelled = raw_status == "cancelled"
    if raw_status == "complimentary":
        status = "complimentary"
    elif is_cancelled:
        status = "cancelled"
    else:
        status = "completed"

    payment_mode = str(o.get("payment_type") or "cash").lower().strip()

    return {
        "restaurant_id": restaurant_id,
        "petpooja_order_id": str(o.get("refId") or o.get("orderID", "")),
        "order_number": str(o.get("orderID", "")) or None,
        "order_type": order_type,
        "platform": "direct",
        "payment_mode": payment_mode or "cash",
        "status": status,
        "total_amount": total_amount,
        "tax_amount": tax_amount,
        "discount_amount": discount_amount,
        "tip": _to_paisa(o.get("tip", 0)),
        "service_charge": _to_paisa(o.get("service_charge", 0)),
        "waived_off": _to_paisa(o.get("waivedOff", 0)),
        "subtotal": core_total,
        "net_amount": total_amount - discount_amount,
        "item_count": len(raw.get("OrderItem", [])),
        "table_number": str(o.get("table_no", "") or o.get("sub_order_type", "")) or None,
        "staff_name": None,
        "is_cancelled": is_cancelled,
        "cancel_reason": None,
        "ordered_at": ordered_at,
    }


def _map_item_fields(
    item: Dict[str, Any],
    order_id: int,
    restaurant_id: int,
) -> Dict[str, Any]:
    """Map a raw PetPooja OrderItem dict to OrderItem model field values."""
    unit_price = _to_paisa(item.get("price", 0))
    total_price = _to_paisa(item.get("total", 0)) or unit_price
    quantity = int(item.get("quantity", 1) or 1)
    if quantity < 1:
        quantity = 1

    return {
        "restaurant_id": restaurant_id,
        "order_id": order_id,
        "item_name": str(item.get("name", "Unknown")).strip() or "Unknown",
        "category": str(item.get("categoryname", "Uncategorized")).strip() or "Uncategorized",
        "quantity": quantity,
        "unit_price": unit_price,
        "total_price": total_price,
        "item_code": str(item.get("itemcode", "")) or None,
        "special_notes": str(item.get("specialnotes", "")) or None,
        "variation_name": None,
    }


# ------------------------------------------------------------------
# Upsert helpers
# ------------------------------------------------------------------

def _upsert_order(
    db: Session,
    fields: Dict[str, Any],
) -> tuple:
    """Insert or update an Order record. Returns (order, was_created)."""
    petpooja_order_id = fields["petpooja_order_id"]
    restaurant_id = fields["restaurant_id"]

    existing = (
        db.query(Order)
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.petpooja_order_id == petpooja_order_id,
        )
        .first()
    )

    if existing is None:
        order = Order(**fields)
        db.add(order)
        db.flush()
        return order, True

    for key, value in fields.items():
        if key not in ("restaurant_id", "petpooja_order_id"):
            setattr(existing, key, value)
    db.flush()
    return existing, False


def _replace_order_items(
    db: Session,
    order_id: int,
    restaurant_id: int,
    raw_items: List[Dict[str, Any]],
) -> None:
    """Delete existing items for an order then insert fresh ones."""
    db.query(OrderItem).filter(OrderItem.order_id == order_id).delete(
        synchronize_session="fetch"
    )
    for item in raw_items:
        item_fields = _map_item_fields(item, order_id, restaurant_id)
        db.add(OrderItem(**item_fields))
    db.flush()


# ------------------------------------------------------------------
# Public entry point
# ------------------------------------------------------------------

def sync_orders(restaurant: Any, db: Session, target_date: date) -> SyncResult:
    """Sync PetPooja orders for target_date into the database.

    Creates a SyncLog entry (status=running), fetches orders, upserts
    each one, then marks the log complete. Any exception marks the log
    as error and re-raises so the caller (scheduler or API route) can
    handle it.
    """
    sync_log = SyncLog(
        restaurant_id=restaurant.id,
        sync_type="orders",
        status="running",
    )
    db.add(sync_log)
    db.flush()

    result = SyncResult()

    try:
        client = PetPoojaClient(restaurant, settings)
        orders = client.get_orders(target_date)
        result.records_fetched = len(orders)

        for raw_order in orders:
            order_fields = _map_order_fields(raw_order, restaurant.id, target_date)
            order, created = _upsert_order(db, order_fields)

            raw_items = raw_order.get("OrderItem", [])
            if isinstance(raw_items, list):
                _replace_order_items(db, order.id, restaurant.id, raw_items)

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
            "Orders sync complete: restaurant=%s date=%s fetched=%d created=%d updated=%d",
            restaurant.id,
            target_date,
            result.records_fetched,
            result.records_created,
            result.records_updated,
        )

    except PetPoojaError as exc:
        error_msg = str(exc)
        logger.error(
            "PetPooja API error during order sync: restaurant=%s date=%s error=%s",
            restaurant.id,
            target_date,
            error_msg,
        )
        sync_log.status = "error"
        sync_log.error_message = error_msg
        sync_log.completed_at = datetime.utcnow()
        db.flush()
        result.error = error_msg
        raise

    except Exception as exc:
        error_msg = str(exc)
        logger.exception(
            "Unexpected error during order sync: restaurant=%s date=%s",
            restaurant.id,
            target_date,
        )
        sync_log.status = "error"
        sync_log.error_message = error_msg
        sync_log.completed_at = datetime.utcnow()
        db.flush()
        result.error = error_msg
        raise

    return result
