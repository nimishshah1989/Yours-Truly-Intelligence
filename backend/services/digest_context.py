"""Digest context builders — assemble metric strings for Claude prompts.

Extracted from digest_service.py to keep both files under 300 lines.
All monetary formatting via _paisa_to_rupees (local to this module).
"""

import logging
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import DailySummary, Order, OrderItem

logger = logging.getLogger("ytip.digest_context")


def _paisa_to_rupees(paisa: int) -> str:
    """Format paisa value as a compact Indian Rupee string."""
    rupees = paisa / 100
    if rupees >= 10_00_000:
        return f"₹{rupees / 10_00_000:.2f}L"
    if rupees >= 1_000:
        return f"₹{rupees:,.0f}"
    return f"₹{rupees:.0f}"


def build_daily_context(
    restaurant_id: int, target_date: date, db: Session
) -> str:
    """Build a compact context string with key daily metrics for Claude."""
    summary: Optional[DailySummary] = (
        db.query(DailySummary)
        .filter(
            DailySummary.restaurant_id == restaurant_id,
            DailySummary.summary_date == target_date,
        )
        .first()
    )

    if not summary:
        live = (
            db.query(
                func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
                func.coalesce(func.sum(Order.discount_amount), 0).label("discounts"),
                func.count(Order.id).label("orders"),
            )
            .filter(
                Order.restaurant_id == restaurant_id,
                func.date(Order.ordered_at) == target_date,
                Order.is_cancelled.is_(False),
            )
            .first()
        )
        revenue = int(live.revenue)
        discounts = int(live.discounts)
        total_orders = int(live.orders)
        avg_ticket = revenue // total_orders if total_orders > 0 else 0
        net_revenue = revenue - discounts
        dine_in = delivery = cancelled = 0
        has_summary = False
    else:
        revenue = int(summary.total_revenue)
        discounts = int(summary.total_discounts)
        total_orders = int(summary.total_orders)
        avg_ticket = int(summary.avg_order_value)
        net_revenue = int(summary.net_revenue)
        dine_in = int(summary.dine_in_orders)
        delivery = int(summary.delivery_orders)
        cancelled = int(summary.cancelled_orders)
        has_summary = True

    top_items = (
        db.query(
            OrderItem.item_name,
            func.sum(OrderItem.total_price).label("item_revenue"),
            func.sum(OrderItem.quantity).label("qty"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .filter(
            OrderItem.restaurant_id == restaurant_id,
            func.date(Order.ordered_at) == target_date,
            Order.is_cancelled.is_(False),
            OrderItem.is_void.is_(False),
        )
        .group_by(OrderItem.item_name)
        .order_by(func.sum(OrderItem.total_price).desc())
        .limit(5)
        .all()
    )

    top_items_text = "\n".join(
        f"  - {row.item_name}: {_paisa_to_rupees(int(row.item_revenue))} ({int(row.qty)} units)"
        for row in top_items
    ) or "  No data"

    week_ago = target_date - timedelta(days=7)
    prior: Optional[DailySummary] = (
        db.query(DailySummary)
        .filter(
            DailySummary.restaurant_id == restaurant_id,
            DailySummary.summary_date == week_ago,
        )
        .first()
    )
    wow_change = ""
    if prior and int(prior.total_revenue) > 0:
        change_pct = ((revenue - int(prior.total_revenue)) / int(prior.total_revenue)) * 100
        direction = "+" if change_pct >= 0 else ""
        wow_change = f" ({direction}{change_pct:.1f}% WoW)"

    lines = [
        f"Date: {target_date}",
        f"Total Revenue: {_paisa_to_rupees(revenue)}{wow_change}",
        f"Net Revenue (after discounts): {_paisa_to_rupees(net_revenue)}",
        f"Total Orders: {total_orders}",
        f"Avg Ticket Size: {_paisa_to_rupees(avg_ticket)}",
        f"Total Discounts: {_paisa_to_rupees(discounts)}",
    ]
    if has_summary:
        lines.append(f"Dine-in: {dine_in} | Delivery: {delivery} | Cancelled: {cancelled}")
    lines += ["", "Top 5 Items by Revenue:", top_items_text]
    return "\n".join(lines)


def build_weekly_context(
    restaurant_id: int, week_start: date, week_end: date, db: Session
) -> str:
    """Build weekly aggregates context string."""
    summaries = (
        db.query(DailySummary)
        .filter(
            DailySummary.restaurant_id == restaurant_id,
            DailySummary.summary_date >= week_start,
            DailySummary.summary_date <= week_end,
        )
        .all()
    )

    total_revenue = sum(int(s.total_revenue) for s in summaries)
    total_orders = sum(int(s.total_orders) for s in summaries)
    total_discounts = sum(int(s.total_discounts) for s in summaries)
    cancelled_orders = sum(int(s.cancelled_orders) for s in summaries)
    days_with_data = len(summaries)
    avg_daily = total_revenue // days_with_data if days_with_data > 0 else 0

    return (
        f"Week: {week_start} to {week_end}\n"
        f"Days with data: {days_with_data}/7\n"
        f"Total Revenue: {_paisa_to_rupees(total_revenue)}\n"
        f"Avg Daily Revenue: {_paisa_to_rupees(avg_daily)}\n"
        f"Total Orders: {total_orders}\n"
        f"Total Discounts: {_paisa_to_rupees(total_discounts)}\n"
        f"Cancelled Orders: {cancelled_orders}"
    )


def build_monthly_context(
    restaurant_id: int, month_start: date, month_end: date, db: Session
) -> str:
    """Build monthly aggregates context string."""
    summaries = (
        db.query(DailySummary)
        .filter(
            DailySummary.restaurant_id == restaurant_id,
            DailySummary.summary_date >= month_start,
            DailySummary.summary_date <= month_end,
        )
        .all()
    )

    total_revenue = sum(int(s.total_revenue) for s in summaries)
    total_orders = sum(int(s.total_orders) for s in summaries)
    total_discounts = sum(int(s.total_discounts) for s in summaries)
    total_commissions = sum(int(s.total_commissions) for s in summaries)
    cancelled_orders = sum(int(s.cancelled_orders) for s in summaries)

    return (
        f"Month: {month_start.strftime('%B %Y')}\n"
        f"Days with data: {len(summaries)}\n"
        f"Total Revenue: {_paisa_to_rupees(total_revenue)}\n"
        f"Total Orders: {total_orders}\n"
        f"Total Discounts: {_paisa_to_rupees(total_discounts)}\n"
        f"Platform Commissions: {_paisa_to_rupees(total_commissions)}\n"
        f"Cancelled Orders: {cancelled_orders}"
    )
