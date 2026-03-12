"""Summary service — pre-compute daily_summary rows from orders.

Aggregates all order data for a given date into the daily_summaries table
using an upsert pattern. Called by the ETL scheduler after each sync.
"""

import logging
from datetime import date
from typing import Optional

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from models import Customer, DailySummary, Order

logger = logging.getLogger("ytip.summary")

# Order type values as stored by PetPooja ETL
ORDER_TYPE_DINE_IN = "dine_in"
ORDER_TYPE_DELIVERY = "delivery"
ORDER_TYPE_TAKEAWAY = "takeaway"


def compute_daily_summary(
    restaurant_id: int, summary_date: date, db: Session
) -> DailySummary:
    """Aggregate orders for a date and upsert into daily_summaries.

    Computes revenue metrics, order counts by type, customer segmentation,
    and JSON breakdowns for platform and payment mode splits.
    Returns the persisted DailySummary object.
    """
    # --- Revenue + order aggregates (non-cancelled only) ---
    stats = (
        db.query(
            func.coalesce(func.sum(Order.total_amount), 0).label("total_revenue"),
            func.coalesce(func.sum(Order.net_amount), 0).label("net_revenue"),
            func.coalesce(func.sum(Order.tax_amount), 0).label("total_tax"),
            func.coalesce(func.sum(Order.discount_amount), 0).label("total_discounts"),
            func.coalesce(func.sum(Order.platform_commission), 0).label("total_commissions"),
            func.count(Order.id).label("total_orders"),
            func.coalesce(func.avg(Order.total_amount), 0).label("avg_order_value"),
        )
        .filter(
            Order.restaurant_id == restaurant_id,
            func.date(Order.ordered_at) == summary_date,
            Order.is_cancelled.is_(False),
        )
        .first()
    )

    total_revenue = int(stats.total_revenue)
    net_revenue = int(stats.net_revenue)
    total_tax = int(stats.total_tax)
    total_discounts = int(stats.total_discounts)
    total_commissions = int(stats.total_commissions)
    total_orders = int(stats.total_orders)
    avg_order_value = int(stats.avg_order_value)

    # --- Cancelled order count ---
    cancelled_orders: int = int(
        db.query(func.count(Order.id))
        .filter(
            Order.restaurant_id == restaurant_id,
            func.date(Order.ordered_at) == summary_date,
            Order.is_cancelled.is_(True),
        )
        .scalar()
        or 0
    )

    # --- Order counts by type (non-cancelled) ---
    type_counts = (
        db.query(
            Order.order_type,
            func.count(Order.id).label("count"),
        )
        .filter(
            Order.restaurant_id == restaurant_id,
            func.date(Order.ordered_at) == summary_date,
            Order.is_cancelled.is_(False),
        )
        .group_by(Order.order_type)
        .all()
    )
    type_map = {row.order_type: int(row.count) for row in type_counts}
    dine_in_orders = type_map.get(ORDER_TYPE_DINE_IN, 0)
    delivery_orders = type_map.get(ORDER_TYPE_DELIVERY, 0)
    takeaway_orders = type_map.get(ORDER_TYPE_TAKEAWAY, 0)

    # --- Payment mode breakdown as JSONB dict ---
    payment_rows = (
        db.query(
            Order.payment_mode,
            func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
            func.count(Order.id).label("count"),
        )
        .filter(
            Order.restaurant_id == restaurant_id,
            func.date(Order.ordered_at) == summary_date,
            Order.is_cancelled.is_(False),
        )
        .group_by(Order.payment_mode)
        .all()
    )
    payment_mode_breakdown = {
        row.payment_mode: {"revenue": int(row.revenue), "count": int(row.count)}
        for row in payment_rows
    }

    # --- Platform revenue breakdown as JSONB dict ---
    platform_rows = (
        db.query(
            Order.platform,
            func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
            func.count(Order.id).label("count"),
        )
        .filter(
            Order.restaurant_id == restaurant_id,
            func.date(Order.ordered_at) == summary_date,
            Order.is_cancelled.is_(False),
        )
        .group_by(Order.platform)
        .all()
    )
    platform_revenue = {
        row.platform: {"revenue": int(row.revenue), "count": int(row.count)}
        for row in platform_rows
    }

    # --- Customer segmentation ---
    unique_customers, new_customers, returning_customers = _compute_customer_counts(
        restaurant_id, summary_date, db
    )

    # --- Upsert ---
    existing: Optional[DailySummary] = (
        db.query(DailySummary)
        .filter_by(restaurant_id=restaurant_id, summary_date=summary_date)
        .first()
    )

    if existing:
        existing.total_revenue = total_revenue
        existing.net_revenue = net_revenue
        existing.total_tax = total_tax
        existing.total_discounts = total_discounts
        existing.total_commissions = total_commissions
        existing.total_orders = total_orders
        existing.avg_order_value = avg_order_value
        existing.dine_in_orders = dine_in_orders
        existing.delivery_orders = delivery_orders
        existing.takeaway_orders = takeaway_orders
        existing.cancelled_orders = cancelled_orders
        existing.unique_customers = unique_customers
        existing.new_customers = new_customers
        existing.returning_customers = returning_customers
        existing.platform_revenue = platform_revenue
        existing.payment_mode_breakdown = payment_mode_breakdown
        db.commit()
        db.refresh(existing)
        logger.info(
            "Daily summary updated: restaurant_id=%d date=%s orders=%d revenue=%d",
            restaurant_id,
            summary_date,
            total_orders,
            total_revenue,
        )
        return existing

    summary = DailySummary(
        restaurant_id=restaurant_id,
        summary_date=summary_date,
        total_revenue=total_revenue,
        net_revenue=net_revenue,
        total_tax=total_tax,
        total_discounts=total_discounts,
        total_commissions=total_commissions,
        total_orders=total_orders,
        avg_order_value=avg_order_value,
        dine_in_orders=dine_in_orders,
        delivery_orders=delivery_orders,
        takeaway_orders=takeaway_orders,
        cancelled_orders=cancelled_orders,
        unique_customers=unique_customers,
        new_customers=new_customers,
        returning_customers=returning_customers,
        platform_revenue=platform_revenue,
        payment_mode_breakdown=payment_mode_breakdown,
    )
    db.add(summary)
    db.commit()
    db.refresh(summary)

    logger.info(
        "Daily summary created: restaurant_id=%d date=%s orders=%d revenue=%d",
        restaurant_id,
        summary_date,
        total_orders,
        total_revenue,
    )
    return summary


def _compute_customer_counts(
    restaurant_id: int, summary_date: date, db: Session
) -> tuple:
    """Compute unique, new, and returning customer counts for the day.

    New = customer's first_visit matches summary_date.
    Returning = has prior visits (total_visits > 1 on this date).
    Returns (unique, new, returning) as ints.
    """
    # Unique customers who placed an order today (via customer_id FK)
    unique: int = int(
        db.query(func.count(func.distinct(Order.customer_id)))
        .filter(
            Order.restaurant_id == restaurant_id,
            func.date(Order.ordered_at) == summary_date,
            Order.is_cancelled.is_(False),
            Order.customer_id.isnot(None),
        )
        .scalar()
        or 0
    )

    # New customers: first_visit == summary_date
    new: int = int(
        db.query(func.count(Customer.id))
        .filter(
            Customer.restaurant_id == restaurant_id,
            Customer.first_visit == summary_date,
        )
        .scalar()
        or 0
    )

    returning = max(0, unique - new)
    return unique, new, returning
