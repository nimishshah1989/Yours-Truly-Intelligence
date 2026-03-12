"""Data status service — query helpers for the /api/data-status endpoint.

Keeps the heavy DB querying logic out of the router file.
All monetary values in paisa (INR x 100).
"""

import logging
from typing import Any, Dict, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import Order, OrderItem, TallyLedgerEntry, TallyVoucher
from services.pl_engine import _categorize_expense, EXPENSE_VOUCHER_TYPES, PURCHASE_VOUCHER_TYPES

logger = logging.getLogger("ytip.data_status_service")


# Static data gap descriptions — known limitations of the current data sources
DATA_GAPS = [
    {
        "field": "cost_price",
        "impact": "Cannot compute per-item margin, BCG matrix, or food cost gap",
        "source": "PetPooja POS",
        "severity": "high",
    },
    {
        "field": "customer_identifiers",
        "impact": "Cannot perform RFM segmentation, cohort analysis, or LTV calculation",
        "source": "PetPooja orders API",
        "severity": "high",
    },
    {
        "field": "void_records",
        "impact": "Cannot detect void/modify anomalies or staff leakage patterns",
        "source": "PetPooja orders API",
        "severity": "medium",
    },
    {
        "field": "inventory_snapshots",
        "impact": "Cannot compute shrinkage, theoretical vs actual consumption",
        "source": "PetPooja inventory API",
        "severity": "medium",
    },
    {
        "field": "modifier_data",
        "impact": "Cannot compute modifier attach rate or modifier revenue contribution",
        "source": "PetPooja orders API",
        "severity": "low",
    },
    {
        "field": "staff_assignments",
        "impact": "Cannot rank staff efficiency or flag individual discount abuse",
        "source": "PetPooja orders API",
        "severity": "low",
    },
]


def _safe_date_str(val: Any) -> Optional[str]:
    """Convert a date/datetime/None to ISO string safely."""
    if val is None:
        return None
    return val.isoformat() if hasattr(val, "isoformat") else str(val)


def build_petpooja_section(rid: int, db: Session) -> Dict[str, Any]:
    """Query PetPooja order and order_item tables for data availability metrics."""
    order_stats = (
        db.query(
            func.count(Order.id).label("count"),
            func.min(func.date(Order.ordered_at)).label("date_from"),
            func.max(func.date(Order.ordered_at)).label("date_to"),
        )
        .filter(Order.restaurant_id == rid)
        .first()
    )
    order_count = int(order_stats.count) if order_stats else 0

    item_stats = (
        db.query(
            func.count(OrderItem.id).label("count"),
            func.count(func.distinct(OrderItem.item_name)).label("unique_items"),
            func.count(func.distinct(OrderItem.category)).label("categories"),
        )
        .filter(OrderItem.restaurant_id == rid)
        .first()
    )
    item_count = int(item_stats.count) if item_stats else 0

    top_items_q = (
        db.query(
            OrderItem.item_name,
            OrderItem.category,
            func.coalesce(func.sum(OrderItem.total_price), 0).label("revenue"),
            func.coalesce(func.sum(OrderItem.quantity), 0).label("quantity"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .filter(OrderItem.restaurant_id == rid, Order.is_cancelled.is_(False))
        .group_by(OrderItem.item_name, OrderItem.category)
        .order_by(func.sum(OrderItem.total_price).desc())
        .limit(5)
        .all()
    )

    order_type_rows = (
        db.query(Order.order_type, func.count(Order.id).label("cnt"))
        .filter(Order.restaurant_id == rid)
        .group_by(Order.order_type)
        .all()
    )
    payment_rows = (
        db.query(Order.payment_mode, func.count(Order.id).label("cnt"))
        .filter(Order.restaurant_id == rid)
        .group_by(Order.payment_mode)
        .all()
    )

    return {
        "orders": {
            "count": order_count,
            "date_from": _safe_date_str(order_stats.date_from) if order_stats else None,
            "date_to": _safe_date_str(order_stats.date_to) if order_stats else None,
            "status": "ok" if order_count > 0 else "empty",
        },
        "order_items": {
            "count": item_count,
            "unique_items": int(item_stats.unique_items) if item_stats else 0,
            "categories": int(item_stats.categories) if item_stats else 0,
            "status": "ok" if item_count > 0 else "empty",
        },
        "top_items": [
            {
                "name": r.item_name,
                "category": r.category,
                "revenue": int(r.revenue),
                "quantity": int(r.quantity),
            }
            for r in top_items_q
        ],
        "cost_price": {
            "count": 0,
            "status": "missing",
            "reason": "PetPooja POS does not provide ingredient COGS per item",
        },
        "staff_data": {
            "count": 0,
            "status": "missing",
            "reason": "Not included in PetPooja orders API",
        },
        "modifiers": {
            "count": 0,
            "status": "missing",
            "reason": "Not captured from PetPooja API",
        },
        "void_records": {
            "count": 0,
            "status": "missing",
            "reason": "Void data not surfaced via PetPooja API",
        },
        "customer_data": {
            "count": 0,
            "status": "missing",
            "reason": "PetPooja orders do not include customer identifiers",
        },
        "inventory": {
            "count": 0,
            "status": "not_configured",
            "reason": (
                "PetPooja inventory API endpoint not yet configured — "
                "contact PetPooja support for raw material stock endpoint"
            ),
        },
        "order_types": {r.order_type.lower(): int(r.cnt) for r in order_type_rows},
        "payment_modes": {r.payment_mode.lower(): int(r.cnt) for r in payment_rows},
    }


def build_tally_section(rid: int, db: Session) -> Dict[str, Any]:
    """Query Tally voucher and ledger entry tables for data availability metrics."""
    voucher_stats = (
        db.query(
            func.count(TallyVoucher.id).label("count"),
            func.min(TallyVoucher.voucher_date).label("date_from"),
            func.max(TallyVoucher.voucher_date).label("date_to"),
        )
        .filter(TallyVoucher.restaurant_id == rid)
        .first()
    )
    voucher_count = int(voucher_stats.count) if voucher_stats else 0

    purchase_stats = (
        db.query(
            func.count(TallyVoucher.id).label("count"),
            func.coalesce(func.sum(TallyVoucher.amount), 0).label("total_amount"),
            func.count(func.distinct(TallyVoucher.party_ledger)).label("vendor_count"),
        )
        .filter(
            TallyVoucher.restaurant_id == rid,
            TallyVoucher.voucher_type.in_(PURCHASE_VOUCHER_TYPES),
            TallyVoucher.is_intercompany.is_(False),
        )
        .first()
    )

    expense_entry_count = (
        db.query(func.count(TallyLedgerEntry.id))
        .join(TallyVoucher, TallyLedgerEntry.voucher_id == TallyVoucher.id)
        .filter(
            TallyLedgerEntry.restaurant_id == rid,
            TallyVoucher.voucher_type.in_(EXPENSE_VOUCHER_TYPES),
            TallyVoucher.is_pp_synced.is_(False),
            TallyVoucher.is_intercompany.is_(False),
            TallyLedgerEntry.is_debit.is_(True),
        )
        .scalar()
    ) or 0

    top_vendors_q = (
        db.query(
            TallyVoucher.party_ledger.label("vendor_name"),
            func.count(TallyVoucher.id).label("invoice_count"),
            func.coalesce(func.sum(TallyVoucher.amount), 0).label("total_amount"),
        )
        .filter(
            TallyVoucher.restaurant_id == rid,
            TallyVoucher.voucher_type.in_(PURCHASE_VOUCHER_TYPES),
            TallyVoucher.is_intercompany.is_(False),
            TallyVoucher.party_ledger.isnot(None),
        )
        .group_by(TallyVoucher.party_ledger)
        .order_by(func.sum(TallyVoucher.amount).desc())
        .limit(8)
        .all()
    )

    expense_rows = (
        db.query(
            TallyLedgerEntry.ledger_name,
            func.coalesce(func.sum(TallyLedgerEntry.amount), 0).label("total"),
        )
        .join(TallyVoucher, TallyLedgerEntry.voucher_id == TallyVoucher.id)
        .filter(
            TallyLedgerEntry.restaurant_id == rid,
            TallyVoucher.voucher_type.in_(EXPENSE_VOUCHER_TYPES),
            TallyVoucher.is_pp_synced.is_(False),
            TallyVoucher.is_intercompany.is_(False),
            TallyLedgerEntry.is_debit.is_(True),
        )
        .group_by(TallyLedgerEntry.ledger_name)
        .all()
    )

    category_totals: Dict[str, int] = {}
    for row in expense_rows:
        category = _categorize_expense(row.ledger_name)
        category_totals[category] = category_totals.get(category, 0) + int(row.total)

    voucher_date_from = _safe_date_str(voucher_stats.date_from) if voucher_stats else None
    voucher_date_to = _safe_date_str(voucher_stats.date_to) if voucher_stats else None

    return {
        "vouchers": {
            "count": voucher_count,
            "date_from": voucher_date_from,
            "date_to": voucher_date_to,
            "status": "ok" if voucher_count > 0 else "empty",
        },
        "food_purchases": {
            "count": int(purchase_stats.count) if purchase_stats else 0,
            "total_amount": int(purchase_stats.total_amount) if purchase_stats else 0,
            "vendor_count": int(purchase_stats.vendor_count) if purchase_stats else 0,
            "status": "ok" if (purchase_stats and int(purchase_stats.count) > 0) else "empty",
        },
        "expense_entries": {
            "count": int(expense_entry_count),
            "status": "ok" if expense_entry_count > 0 else "empty",
        },
        "top_vendors": [
            {
                "vendor_name": r.vendor_name,
                "invoice_count": int(r.invoice_count),
                "total_amount": int(r.total_amount),
            }
            for r in top_vendors_q
        ],
        "expense_summary": {
            "food_cost": category_totals.get("Food & Beverage Cost", 0),
            "labour": category_totals.get("Labour", 0),
            "rent_facility": category_totals.get("Rent & Facility", 0),
            "marketing": category_totals.get("Marketing", 0),
            "other": category_totals.get("Other Opex", 0),
        },
        "voucher_date_from": voucher_date_from,
        "voucher_date_to": voucher_date_to,
    }


def build_data_coverage(petpooja: Dict, tally: Dict) -> Dict[str, str]:
    """Determine coverage level for each analytics module."""
    has_orders = petpooja["orders"]["status"] == "ok"
    has_tally = tally["vouchers"]["status"] == "ok"

    return {
        "revenue": "full" if has_orders else "none",
        "menu_engineering": "partial" if has_orders else "none",
        "cost_margin": "partial" if (has_orders and has_tally) else (
            "limited" if has_tally else "none"
        ),
        "leakage": "limited" if has_orders else "none",
        "customers": "none",
        "operations": "partial" if has_orders else "none",
    }
