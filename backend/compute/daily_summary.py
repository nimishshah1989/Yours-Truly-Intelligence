"""Compute daily summaries from orders data.

Aggregates Order records into DailySummary rows for fast dashboard queries.
Idempotent — uses upsert on (restaurant_id, summary_date).

Revenue = SUM(total_amount) for successful orders only (status == 'completed').
Excludes both cancelled AND complimentary from revenue.
Order count = COUNT(all orders) including cancelled and complimentary.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from models import DailySummary, Order

logger = logging.getLogger("ytip.compute.daily_summary")


def compute_daily_summary(
    db: Session,
    restaurant_id: int,
    summary_date: date,
) -> DailySummary:
    """Aggregate orders for summary_date into a DailySummary row.

    Revenue only counts successful orders (not cancelled).
    Order counts include ALL statuses for transparency.
    """
    start_dt = datetime(
        summary_date.year, summary_date.month, summary_date.day
    )
    end_dt = start_dt + timedelta(days=1)

    base_filter = [
        Order.restaurant_id == restaurant_id,
        Order.ordered_at >= start_dt,
        Order.ordered_at < end_dt,
    ]

    # Total order count (all statuses)
    total_orders = (
        db.query(func.count(Order.id))
        .filter(*base_filter)
        .scalar()
    ) or 0

    # Revenue aggregates (successful only — excludes cancelled AND complimentary)
    # PetPooja "Success" maps to our status "completed"
    revenue_filter = base_filter + [Order.status == "completed"]
    rev = (
        db.query(
            func.coalesce(func.sum(Order.total_amount), 0).label("rev"),
            func.coalesce(func.sum(Order.net_amount), 0).label("net"),
            func.coalesce(func.sum(Order.tax_amount), 0).label("tax"),
            func.coalesce(
                func.sum(Order.discount_amount), 0
            ).label("disc"),
            func.coalesce(
                func.sum(Order.platform_commission), 0
            ).label("comm"),
        )
        .filter(*revenue_filter)
        .first()
    )

    total_revenue = int(rev.rev)
    net_revenue = int(rev.net)
    total_tax = int(rev.tax)
    total_discounts = int(rev.disc)
    total_commissions = int(rev.comm)

    # Order type breakdown (all statuses)
    type_counts = (
        db.query(
            func.sum(
                case((Order.order_type == "dine_in", 1), else_=0)
            ).label("dine_in"),
            func.sum(
                case((Order.order_type == "delivery", 1), else_=0)
            ).label("delivery"),
            func.sum(
                case((Order.order_type == "takeaway", 1), else_=0)
            ).label("takeaway"),
            func.sum(
                case((Order.is_cancelled.is_(True), 1), else_=0)
            ).label("cancelled"),
        )
        .filter(*base_filter)
        .first()
    )

    dine_in = int(type_counts.dine_in or 0)
    delivery = int(type_counts.delivery or 0)
    takeaway = int(type_counts.takeaway or 0)
    cancelled = int(type_counts.cancelled or 0)

    # Successful orders count (excludes cancelled + complimentary)
    successful_count = (
        db.query(func.count(Order.id))
        .filter(*revenue_filter)
        .scalar()
    ) or 0

    # Average order value (successful only)
    avg_order_value = (
        total_revenue // successful_count
        if successful_count > 0
        else 0
    )

    # Payment mode breakdown (non-cancelled)
    payment_rows = (
        db.query(
            Order.payment_mode,
            func.count(Order.id).label("count"),
            func.sum(Order.total_amount).label("amount"),
        )
        .filter(*revenue_filter)
        .group_by(Order.payment_mode)
        .all()
    )
    payment_breakdown = {
        row.payment_mode: {
            "count": int(row.count),
            "amount": int(row.amount or 0),
        }
        for row in payment_rows
    }

    # Upsert DailySummary
    values = {
        "total_revenue": total_revenue,
        "net_revenue": net_revenue,
        "total_tax": total_tax,
        "total_discounts": total_discounts,
        "total_commissions": total_commissions,
        "total_orders": total_orders,
        "dine_in_orders": dine_in,
        "delivery_orders": delivery,
        "takeaway_orders": takeaway,
        "cancelled_orders": cancelled,
        "avg_order_value": avg_order_value,
        "payment_mode_breakdown": payment_breakdown,
    }

    existing = (
        db.query(DailySummary)
        .filter(
            DailySummary.restaurant_id == restaurant_id,
            DailySummary.summary_date == summary_date,
        )
        .first()
    )

    if existing:
        for k, v in values.items():
            setattr(existing, k, v)
        db.flush()
        logger.info(
            "Updated summary: date=%s orders=%d revenue=%d",
            summary_date, total_orders, total_revenue,
        )
        return existing

    summary = DailySummary(
        restaurant_id=restaurant_id,
        summary_date=summary_date,
        **values,
    )
    db.add(summary)
    db.flush()
    logger.info(
        "Created summary: date=%s orders=%d revenue=%d",
        summary_date, total_orders, total_revenue,
    )
    return summary


def backfill_summaries(
    db: Session,
    restaurant_id: int,
    start_date: date,
    end_date: date,
) -> List[Tuple[date, int, int]]:
    """Compute daily summaries for a date range.

    Returns list of (date, total_orders, total_revenue_paisa).
    """
    results: List[Tuple[date, int, int]] = []
    current = start_date

    while current <= end_date:
        try:
            summary = compute_daily_summary(
                db, restaurant_id, current
            )
            db.commit()
            results.append(
                (current, summary.total_orders, summary.total_revenue)
            )
        except Exception as exc:
            db.rollback()
            logger.error(
                "Summary FAILED: date=%s error=%s", current, exc
            )
            results.append((current, 0, 0))
        current += timedelta(days=1)

    return results
