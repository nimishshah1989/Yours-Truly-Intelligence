"""Revenue Intelligence service — analytics helpers for the revenue router.

All monetary values are in paisa (INR x 100). Frontend handles formatting.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import case, cast, func, extract, Date
from sqlalchemy.orm import Session

from models import DailySummary, Order, OrderItem
from services.analytics_service import IST, resolve_period, today_ist
from dependencies import DOW_NAMES, safe_pct_change, date_to_ist_range

logger = logging.getLogger("ytip.revenue")


def _base_order_query(db: Session, restaurant_id: int):
    """Start a query on Order filtered to non-cancelled orders for a restaurant."""
    return db.query(Order).filter(
        Order.restaurant_id == restaurant_id,
        Order.is_cancelled.is_(False),
    )


# ---------------------------------------------------------------------------
# 1. Overview: stat cards + sparkline
# ---------------------------------------------------------------------------
def get_overview(
    db: Session,
    restaurant_id: int,
    period: str,
    custom_start: Optional[date] = None,
    custom_end: Optional[date] = None,
) -> Dict[str, Any]:
    """Revenue overview: yesterday stats (T-1), WoW change, MoM change, 7-day sparkline."""
    today = today_ist()
    yesterday = today - timedelta(days=1)

    # Yesterday's stats (T-1 data from PetPooja)
    start_dt, end_dt = date_to_ist_range(yesterday, yesterday)
    today_q = _base_order_query(db, restaurant_id).filter(
        Order.ordered_at >= start_dt, Order.ordered_at <= end_dt
    )
    today_agg = today_q.with_entities(
        func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
        func.coalesce(func.sum(Order.net_amount), 0).label("net_revenue"),
        func.count(Order.id).label("orders"),
    ).first()

    today_revenue = int(today_agg.revenue)
    today_orders = int(today_agg.orders)
    avg_ticket = today_revenue // today_orders if today_orders > 0 else 0

    # WoW: same day last week from DailySummary
    last_week_day = yesterday - timedelta(days=7)
    lw_summary = (
        db.query(DailySummary)
        .filter(
            DailySummary.restaurant_id == restaurant_id,
            DailySummary.summary_date == last_week_day,
        )
        .first()
    )
    lw_revenue = lw_summary.total_revenue if lw_summary else 0
    wow_change = safe_pct_change(today_revenue, lw_revenue)

    # MoM: last 7 days vs prior 7 days from DailySummary
    recent_start = today - timedelta(days=6)
    prior_start = today - timedelta(days=13)
    prior_end = today - timedelta(days=7)

    recent_rev = (
        db.query(func.coalesce(func.sum(DailySummary.total_revenue), 0))
        .filter(
            DailySummary.restaurant_id == restaurant_id,
            DailySummary.summary_date >= recent_start,
            DailySummary.summary_date <= today,
        )
        .scalar()
    )
    prior_rev = (
        db.query(func.coalesce(func.sum(DailySummary.total_revenue), 0))
        .filter(
            DailySummary.restaurant_id == restaurant_id,
            DailySummary.summary_date >= prior_start,
            DailySummary.summary_date <= prior_end,
        )
        .scalar()
    )
    mom_change = safe_pct_change(int(recent_rev), int(prior_rev))

    # 7-day sparkline from DailySummary
    sparkline_rows = (
        db.query(
            DailySummary.summary_date,
            DailySummary.total_revenue,
        )
        .filter(
            DailySummary.restaurant_id == restaurant_id,
            DailySummary.summary_date >= recent_start,
            DailySummary.summary_date <= today,
        )
        .order_by(DailySummary.summary_date)
        .all()
    )
    # Build a full 7-day array (fill gaps with 0)
    sparkline_map = {row.summary_date: int(row.total_revenue) for row in sparkline_rows}
    sparkline = [
        sparkline_map.get(recent_start + timedelta(days=i), 0) for i in range(7)
    ]

    return {
        "today_revenue": today_revenue,
        "today_orders": today_orders,
        "avg_ticket": avg_ticket,
        "net_revenue": int(today_agg.net_revenue),
        "wow_change": wow_change,
        "mom_change": mom_change,
        "sparkline": sparkline,
    }


# ---------------------------------------------------------------------------
# 2. Trend: daily revenue line
# ---------------------------------------------------------------------------
def get_trend(
    db: Session, restaurant_id: int, start_date: date, end_date: date
) -> List[Dict[str, Any]]:
    """Daily revenue, net_revenue, and order count from daily_summaries."""
    rows = (
        db.query(
            DailySummary.summary_date,
            DailySummary.total_revenue,
            DailySummary.net_revenue,
            DailySummary.total_orders,
        )
        .filter(
            DailySummary.restaurant_id == restaurant_id,
            DailySummary.summary_date >= start_date,
            DailySummary.summary_date <= end_date,
        )
        .order_by(DailySummary.summary_date)
        .all()
    )
    return [
        {
            "date": row.summary_date.isoformat(),
            "revenue": int(row.total_revenue),
            "net_revenue": int(row.net_revenue),
            "orders": int(row.total_orders),
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# 3. Heatmap: day-of-week x hour revenue matrix
# ---------------------------------------------------------------------------
def get_heatmap(
    db: Session, restaurant_id: int, start_date: date, end_date: date
) -> Dict[str, Any]:
    """Revenue heatmap — day_of_week (rows) x hour (columns)."""
    start_dt, end_dt = date_to_ist_range(start_date, end_date)

    rows = (
        db.query(
            extract("dow", Order.ordered_at).label("dow"),
            extract("hour", Order.ordered_at).label("hour"),
            func.sum(Order.total_amount).label("revenue"),
            func.count(Order.id).label("orders"),
        )
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.is_cancelled.is_(False),
            Order.ordered_at >= start_dt,
            Order.ordered_at <= end_dt,
        )
        .group_by("dow", "hour")
        .all()
    )

    cells = []
    max_value = 0
    for row in rows:
        revenue = int(row.revenue)
        max_value = max(max_value, revenue)
        cells.append({
            "x": int(row.hour),
            "y": DOW_NAMES.get(int(row.dow), "?"),
            "value": revenue,
            "orders": int(row.orders),
        })

    return {"cells": cells, "max_value": max_value}


# ---------------------------------------------------------------------------
# 4. Concentration (Pareto): items ranked by revenue + cumulative %
# ---------------------------------------------------------------------------
def get_concentration(
    db: Session, restaurant_id: int, start_date: date, end_date: date
) -> List[Dict[str, Any]]:
    """Revenue Pareto — items ranked by revenue with cumulative percentage."""
    start_dt, end_dt = date_to_ist_range(start_date, end_date)

    rows = (
        db.query(
            OrderItem.item_name,
            func.sum(OrderItem.total_price).label("revenue"),
            func.sum(OrderItem.quantity).label("quantity"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .filter(
            OrderItem.restaurant_id == restaurant_id,
            OrderItem.is_void.is_(False),
            Order.is_cancelled.is_(False),
            Order.ordered_at >= start_dt,
            Order.ordered_at <= end_dt,
        )
        .group_by(OrderItem.item_name)
        .order_by(func.sum(OrderItem.total_price).desc())
        .all()
    )

    total_revenue = sum(int(r.revenue) for r in rows)
    if total_revenue == 0:
        return []

    cumulative = 0
    result = []
    for row in rows:
        revenue = int(row.revenue)
        cumulative += revenue
        result.append({
            "name": row.item_name,
            "revenue": revenue,
            "quantity": int(row.quantity),
            "cumulative_pct": round((cumulative / total_revenue) * 100, 1),
        })
    return result


# ---------------------------------------------------------------------------
# 5. Payment modes: breakdown + daily trend
# ---------------------------------------------------------------------------
def get_payment_modes(
    db: Session, restaurant_id: int, start_date: date, end_date: date
) -> Dict[str, Any]:
    """Payment mode breakdown and daily trend."""
    start_dt, end_dt = date_to_ist_range(start_date, end_date)

    base = (
        db.query(Order)
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.is_cancelled.is_(False),
            Order.ordered_at >= start_dt,
            Order.ordered_at <= end_dt,
        )
    )

    # Aggregate breakdown
    breakdown_rows = (
        base.with_entities(
            Order.payment_mode,
            func.sum(Order.total_amount).label("revenue"),
            func.count(Order.id).label("count"),
        )
        .group_by(Order.payment_mode)
        .order_by(func.sum(Order.total_amount).desc())
        .all()
    )
    breakdown = [
        {"mode": row.payment_mode, "revenue": int(row.revenue), "count": int(row.count)}
        for row in breakdown_rows
    ]

    # Daily trend pivoted by payment mode
    trend_rows = (
        base.with_entities(
            cast(Order.ordered_at, Date).label("order_date"),
            Order.payment_mode,
            func.sum(Order.total_amount).label("revenue"),
        )
        .group_by("order_date", Order.payment_mode)
        .order_by("order_date")
        .all()
    )

    # Pivot into {date: {mode: revenue}}
    trend_map: Dict[str, Dict[str, int]] = {}
    for row in trend_rows:
        d = row.order_date.isoformat() if hasattr(row.order_date, "isoformat") else str(row.order_date)
        if d not in trend_map:
            trend_map[d] = {}
        trend_map[d][row.payment_mode] = int(row.revenue)

    trend = [{"date": d, **modes} for d, modes in sorted(trend_map.items())]

    return {"breakdown": breakdown, "trend": trend}


# ---------------------------------------------------------------------------
# 6. Platform profitability: gross vs net by platform
# ---------------------------------------------------------------------------
def get_platform_profitability(
    db: Session, restaurant_id: int, start_date: date, end_date: date
) -> List[Dict[str, Any]]:
    """Gross vs net revenue and commissions by platform."""
    start_dt, end_dt = date_to_ist_range(start_date, end_date)

    rows = (
        db.query(
            Order.platform,
            func.sum(Order.total_amount).label("gross"),
            func.sum(Order.net_amount).label("net"),
            func.sum(Order.platform_commission).label("commission"),
            func.sum(Order.discount_amount).label("discounts"),
            func.count(Order.id).label("orders"),
        )
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.is_cancelled.is_(False),
            Order.ordered_at >= start_dt,
            Order.ordered_at <= end_dt,
        )
        .group_by(Order.platform)
        .order_by(func.sum(Order.total_amount).desc())
        .all()
    )

    return [
        {
            "platform": row.platform,
            "gross": int(row.gross),
            "net": int(row.net),
            "commission": int(row.commission),
            "discounts": int(row.discounts),
            "orders": int(row.orders),
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# 7. Discount analysis: totals + daily trend
# ---------------------------------------------------------------------------
def get_discount_analysis(
    db: Session, restaurant_id: int, start_date: date, end_date: date
) -> Dict[str, Any]:
    """Discount stats and daily trend."""
    start_dt, end_dt = date_to_ist_range(start_date, end_date)

    # Aggregate stats
    agg = (
        db.query(
            func.coalesce(func.sum(Order.total_amount), 0).label("total_revenue"),
            func.coalesce(func.sum(Order.discount_amount), 0).label("total_discounts"),
            func.count(Order.id).label("total_orders"),
            func.sum(
                case((Order.discount_amount > 0, 1), else_=0)
            ).label("discounted_orders"),
        )
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.is_cancelled.is_(False),
            Order.ordered_at >= start_dt,
            Order.ordered_at <= end_dt,
        )
        .first()
    )

    total_revenue = int(agg.total_revenue)
    total_discounts = int(agg.total_discounts)
    discounted_orders = int(agg.discounted_orders)
    discount_rate = round((total_discounts / total_revenue) * 100, 2) if total_revenue > 0 else 0
    avg_per_order = total_discounts // discounted_orders if discounted_orders > 0 else 0

    # Daily trend
    trend_rows = (
        db.query(
            cast(Order.ordered_at, Date).label("order_date"),
            func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
            func.coalesce(func.sum(Order.discount_amount), 0).label("discounts"),
        )
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.is_cancelled.is_(False),
            Order.ordered_at >= start_dt,
            Order.ordered_at <= end_dt,
        )
        .group_by("order_date")
        .order_by("order_date")
        .all()
    )

    trend = []
    for row in trend_rows:
        rev = int(row.revenue)
        disc = int(row.discounts)
        rate = round((disc / rev) * 100, 2) if rev > 0 else 0
        trend.append({
            "date": row.order_date.isoformat() if hasattr(row.order_date, "isoformat") else str(row.order_date),
            "discounts": disc,
            "revenue": rev,
            "rate": rate,
        })

    return {
        "total_discounts": total_discounts,
        "discount_rate": discount_rate,
        "avg_per_order": avg_per_order,
        "discounted_orders": discounted_orders,
        "total_orders": int(agg.total_orders),
        "trend": trend,
    }
