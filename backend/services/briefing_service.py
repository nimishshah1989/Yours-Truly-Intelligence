"""Morning briefing engine — generates proactive daily intelligence.

Produces the content for:
  - Daily morning briefing (7:30 AM WhatsApp push)
  - Weekly pulse (Sunday evening)
  - Monthly deep dive (1st of month)

Each briefing queries the database directly and uses Claude to generate
a narrative. The narrative is conversational, not chart-heavy — designed
for WhatsApp consumption.

Architecture:
  1. Query database for KPIs and comparisons
  2. Detect anomalies (statistical + threshold-based)
  3. Feed data context to Claude for narrative generation
  4. Format for WhatsApp delivery
"""

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from config import settings
from database import SessionReadOnly
from services.whatsapp_service import format_currency, format_pct

logger = logging.getLogger("ytip.briefing")

# Day names for comparison context
DOW_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def generate_morning_briefing(
    restaurant_id: int,
    target_date: Optional[date] = None,
) -> Dict[str, Any]:
    """Generate the daily morning briefing content.

    Returns a dict with:
      - "whatsapp_message": formatted WhatsApp text
      - "sections": structured data for web feed cards
      - "anomalies": list of detected anomalies
      - "recommendations": list of actionable suggestions
    """
    if target_date is None:
        target_date = date.today() - timedelta(days=1)  # Yesterday

    session = SessionReadOnly()
    try:
        # Gather all data points
        yesterday = _get_day_metrics(session, restaurant_id, target_date)
        same_day_last_week = _get_day_metrics(
            session, restaurant_id, target_date - timedelta(days=7)
        )
        last_7_days = _get_period_metrics(
            session, restaurant_id,
            target_date - timedelta(days=6), target_date,
        )
        prev_7_days = _get_period_metrics(
            session, restaurant_id,
            target_date - timedelta(days=13), target_date - timedelta(days=7),
        )

        # Top items yesterday
        top_items = _get_top_items(session, restaurant_id, target_date, limit=5)

        # Area breakdown
        area_breakdown = _get_area_breakdown(session, restaurant_id, target_date)

        # Payment mode split
        payment_split = _get_payment_split(session, restaurant_id, target_date)

        # Anomaly detection
        anomalies = _detect_anomalies(
            yesterday, same_day_last_week, last_7_days, prev_7_days,
        )

        # Build the WhatsApp message
        dow_name = DOW_NAMES[target_date.weekday()]
        date_str = target_date.strftime("%d %b %Y")

        sections: List[Dict[str, str]] = []

        # Section 1: Yesterday's headline
        rev_str = format_currency(yesterday["revenue"])
        orders_str = str(yesterday["orders"])
        aov_str = format_currency(yesterday["avg_order_value"])

        wow_rev = _pct_change(yesterday["revenue"], same_day_last_week["revenue"])
        wow_label = f" ({format_pct(wow_rev)} vs last {dow_name})" if wow_rev is not None else ""

        sections.append({
            "emoji": "📊",
            "title": f"{dow_name}, {date_str}",
            "body": (
                f"Revenue: {rev_str}{wow_label}\n"
                f"Orders: {orders_str} • Avg ticket: {aov_str}"
            ),
        })

        # Section 2: Week-over-week
        if last_7_days["revenue"] > 0 and prev_7_days["revenue"] > 0:
            wow_week = _pct_change(last_7_days["revenue"], prev_7_days["revenue"])
            wow_week_str = format_pct(wow_week) if wow_week is not None else "—"
            sections.append({
                "emoji": "📈",
                "title": "7-Day Trend",
                "body": (
                    f"This week: {format_currency(last_7_days['revenue'])} "
                    f"({wow_week_str} WoW)\n"
                    f"Orders: {last_7_days['orders']} • "
                    f"Avg ticket: {format_currency(last_7_days['avg_order_value'])}"
                ),
            })

        # Section 3: Top sellers
        if top_items:
            items_lines = []
            for i, item in enumerate(top_items[:5], 1):
                items_lines.append(
                    f"{i}. {item['name']} — {item['qty']}× "
                    f"({format_currency(item['revenue'])})"
                )
            sections.append({
                "emoji": "🏆",
                "title": "Top 5 Items",
                "body": "\n".join(items_lines),
            })

        # Section 4: Anomalies / attention items
        if anomalies:
            anomaly_lines = []
            for a in anomalies[:3]:
                anomaly_lines.append(f"• {a['message']}")
            sections.append({
                "emoji": "⚠️",
                "title": f"{len(anomalies)} thing{'s' if len(anomalies) > 1 else ''} need attention",
                "body": "\n".join(anomaly_lines),
            })

        # Section 5: Area performance (if multiple areas)
        if len(area_breakdown) > 1:
            area_lines = []
            for area in area_breakdown[:5]:
                area_lines.append(
                    f"• {area['area']}: {format_currency(area['revenue'])} "
                    f"({area['orders']} orders)"
                )
            sections.append({
                "emoji": "🪑",
                "title": "By Area",
                "body": "\n".join(area_lines),
            })

        # Compose WhatsApp message
        greeting = _get_greeting()
        header = f"{greeting} Here's your {dow_name} briefing:\n"

        section_texts = []
        for s in sections:
            section_texts.append(f"{s['emoji']} *{s['title']}*\n{s['body']}")

        footer = "\n_Reply with any question — or send a voice note._"
        whatsapp_message = header + "\n\n" + "\n\n".join(section_texts) + footer

        return {
            "whatsapp_message": whatsapp_message,
            "sections": sections,
            "anomalies": anomalies,
            "metrics": {
                "yesterday": yesterday,
                "same_day_last_week": same_day_last_week,
                "last_7_days": last_7_days,
                "top_items": top_items,
                "area_breakdown": area_breakdown,
                "payment_split": payment_split,
            },
            "target_date": target_date.isoformat(),
        }
    finally:
        session.close()


def generate_weekly_pulse(
    restaurant_id: int,
    week_end: Optional[date] = None,
) -> Dict[str, Any]:
    """Generate weekly pulse for Sunday evening delivery."""
    if week_end is None:
        week_end = date.today() - timedelta(days=1)

    week_start = week_end - timedelta(days=6)
    prev_week_end = week_start - timedelta(days=1)
    prev_week_start = prev_week_end - timedelta(days=6)

    session = SessionReadOnly()
    try:
        this_week = _get_period_metrics(session, restaurant_id, week_start, week_end)
        last_week = _get_period_metrics(
            session, restaurant_id, prev_week_start, prev_week_end
        )

        # Top items this week
        top_items = _get_top_items_period(
            session, restaurant_id, week_start, week_end, limit=10
        )

        # Day-by-day breakdown
        daily_breakdown = _get_daily_breakdown(
            session, restaurant_id, week_start, week_end
        )

        # Build message
        wow_rev = _pct_change(this_week["revenue"], last_week["revenue"])
        wow_orders = _pct_change(this_week["orders"], last_week["orders"])

        sections = []

        sections.append({
            "emoji": "📊",
            "title": f"Week of {week_start.strftime('%d %b')} — {week_end.strftime('%d %b')}",
            "body": (
                f"Revenue: {format_currency(this_week['revenue'])} "
                f"({format_pct(wow_rev) if wow_rev is not None else '—'} WoW)\n"
                f"Orders: {this_week['orders']} "
                f"({format_pct(wow_orders) if wow_orders is not None else '—'} WoW)\n"
                f"Avg ticket: {format_currency(this_week['avg_order_value'])}"
            ),
        })

        # Best and worst days
        if daily_breakdown:
            best_day = max(daily_breakdown, key=lambda d: d["revenue"])
            worst_day = min(daily_breakdown, key=lambda d: d["revenue"])
            sections.append({
                "emoji": "📅",
                "title": "Best & Worst Days",
                "body": (
                    f"Best: {best_day['day_name']} — {format_currency(best_day['revenue'])} "
                    f"({best_day['orders']} orders)\n"
                    f"Slowest: {worst_day['day_name']} — {format_currency(worst_day['revenue'])} "
                    f"({worst_day['orders']} orders)"
                ),
            })

        # Top 5 items
        if top_items:
            items_lines = [
                f"{i}. {it['name']} — {it['qty']}× ({format_currency(it['revenue'])})"
                for i, it in enumerate(top_items[:5], 1)
            ]
            sections.append({
                "emoji": "🏆",
                "title": "Top 5 Items This Week",
                "body": "\n".join(items_lines),
            })

        greeting = "Good evening!"
        header = f"{greeting} Here's your weekly pulse:\n"

        section_texts = [
            f"{s['emoji']} *{s['title']}*\n{s['body']}" for s in sections
        ]
        footer = "\n_Ask me anything about this week — text or voice note._"

        return {
            "whatsapp_message": header + "\n\n" + "\n\n".join(section_texts) + footer,
            "sections": sections,
            "metrics": {
                "this_week": this_week,
                "last_week": last_week,
                "top_items": top_items,
                "daily_breakdown": daily_breakdown,
            },
        }
    finally:
        session.close()


# -------------------------------------------------------------------------
# Data queries (read-only session)
# -------------------------------------------------------------------------

def _get_day_metrics(
    session: Session, restaurant_id: int, target_date: date
) -> Dict[str, Any]:
    """Get core KPIs for a single day."""
    result = session.execute(
        text("""
            SELECT
                COALESCE(COUNT(*), 0) AS orders,
                COALESCE(SUM(total_amount), 0) AS revenue,
                COALESCE(SUM(discount_amount), 0) AS discounts,
                COALESCE(SUM(tax_amount), 0) AS tax,
                COALESCE(AVG(total_amount), 0) AS avg_order_value,
                COALESCE(SUM(CASE WHEN is_cancelled THEN 1 ELSE 0 END), 0) AS cancelled
            FROM orders
            WHERE restaurant_id = :rid
              AND DATE(ordered_at) = :dt
              AND is_cancelled = false
              AND status = 'completed'
        """),
        {"rid": restaurant_id, "dt": target_date},
    ).fetchone()

    if not result:
        return {
            "orders": 0, "revenue": 0, "discounts": 0, "tax": 0,
            "avg_order_value": 0, "cancelled": 0,
        }

    return {
        "orders": int(result[0]),
        "revenue": int(result[1]),
        "discounts": int(result[2]),
        "tax": int(result[3]),
        "avg_order_value": int(result[4]),
        "cancelled": int(result[5]),
    }


def _get_period_metrics(
    session: Session, restaurant_id: int, start: date, end: date
) -> Dict[str, Any]:
    """Get aggregated KPIs for a date range."""
    result = session.execute(
        text("""
            SELECT
                COALESCE(COUNT(*), 0) AS orders,
                COALESCE(SUM(total_amount), 0) AS revenue,
                COALESCE(AVG(total_amount), 0) AS avg_order_value
            FROM orders
            WHERE restaurant_id = :rid
              AND DATE(ordered_at) BETWEEN :start AND :end
              AND is_cancelled = false
              AND status = 'completed'
        """),
        {"rid": restaurant_id, "start": start, "end": end},
    ).fetchone()

    if not result:
        return {"orders": 0, "revenue": 0, "avg_order_value": 0}

    return {
        "orders": int(result[0]),
        "revenue": int(result[1]),
        "avg_order_value": int(result[2]),
    }


def _get_top_items(
    session: Session, restaurant_id: int, target_date: date, limit: int = 5
) -> List[Dict[str, Any]]:
    """Get top-selling items for a single day."""
    rows = session.execute(
        text("""
            SELECT
                oi.item_name AS name,
                SUM(oi.quantity) AS qty,
                SUM(oi.total_price) AS revenue
            FROM order_items oi
            JOIN orders o ON o.id = oi.order_id
            WHERE oi.restaurant_id = :rid
              AND DATE(o.ordered_at) = :dt
              AND o.is_cancelled = false
              AND o.status = 'completed'
            GROUP BY oi.item_name
            ORDER BY revenue DESC
            LIMIT :lim
        """),
        {"rid": restaurant_id, "dt": target_date, "lim": limit},
    ).fetchall()

    return [
        {"name": r[0], "qty": int(r[1]), "revenue": int(r[2])}
        for r in rows
    ]


def _get_top_items_period(
    session: Session, restaurant_id: int,
    start: date, end: date, limit: int = 10,
) -> List[Dict[str, Any]]:
    """Get top-selling items for a date range."""
    rows = session.execute(
        text("""
            SELECT
                oi.item_name AS name,
                SUM(oi.quantity) AS qty,
                SUM(oi.total_price) AS revenue
            FROM order_items oi
            JOIN orders o ON o.id = oi.order_id
            WHERE oi.restaurant_id = :rid
              AND DATE(o.ordered_at) BETWEEN :start AND :end
              AND o.is_cancelled = false
              AND o.status = 'completed'
            GROUP BY oi.item_name
            ORDER BY revenue DESC
            LIMIT :lim
        """),
        {"rid": restaurant_id, "start": start, "end": end, "lim": limit},
    ).fetchall()

    return [
        {"name": r[0], "qty": int(r[1]), "revenue": int(r[2])}
        for r in rows
    ]


def _get_area_breakdown(
    session: Session, restaurant_id: int, target_date: date,
) -> List[Dict[str, Any]]:
    """Get revenue breakdown by seating area (sub_order_type)."""
    rows = session.execute(
        text("""
            SELECT
                COALESCE(sub_order_type, order_type) AS area,
                COUNT(*) AS orders,
                SUM(total_amount) AS revenue
            FROM orders
            WHERE restaurant_id = :rid
              AND DATE(ordered_at) = :dt
              AND is_cancelled = false
              AND status = 'completed'
            GROUP BY COALESCE(sub_order_type, order_type)
            ORDER BY revenue DESC
        """),
        {"rid": restaurant_id, "dt": target_date},
    ).fetchall()

    return [
        {"area": r[0] or "Unknown", "orders": int(r[1]), "revenue": int(r[2])}
        for r in rows
    ]


def _get_payment_split(
    session: Session, restaurant_id: int, target_date: date,
) -> List[Dict[str, Any]]:
    """Get payment mode breakdown."""
    rows = session.execute(
        text("""
            SELECT
                payment_mode,
                COUNT(*) AS orders,
                SUM(total_amount) AS revenue
            FROM orders
            WHERE restaurant_id = :rid
              AND DATE(ordered_at) = :dt
              AND is_cancelled = false
              AND status = 'completed'
            GROUP BY payment_mode
            ORDER BY revenue DESC
        """),
        {"rid": restaurant_id, "dt": target_date},
    ).fetchall()

    return [
        {"mode": r[0], "orders": int(r[1]), "revenue": int(r[2])}
        for r in rows
    ]


def _get_daily_breakdown(
    session: Session, restaurant_id: int, start: date, end: date,
) -> List[Dict[str, Any]]:
    """Get day-by-day KPIs for a date range."""
    rows = session.execute(
        text("""
            SELECT
                DATE(ordered_at) AS day,
                COUNT(*) AS orders,
                SUM(total_amount) AS revenue,
                AVG(total_amount) AS avg_ov
            FROM orders
            WHERE restaurant_id = :rid
              AND DATE(ordered_at) BETWEEN :start AND :end
              AND is_cancelled = false
              AND status = 'completed'
            GROUP BY DATE(ordered_at)
            ORDER BY day
        """),
        {"rid": restaurant_id, "start": start, "end": end},
    ).fetchall()

    return [
        {
            "date": r[0].isoformat(),
            "day_name": DOW_NAMES[r[0].weekday()],
            "orders": int(r[1]),
            "revenue": int(r[2]),
            "avg_order_value": int(r[3]),
        }
        for r in rows
    ]


# -------------------------------------------------------------------------
# Anomaly detection (threshold + statistical)
# -------------------------------------------------------------------------

def _detect_anomalies(
    yesterday: Dict[str, Any],
    same_day_last_week: Dict[str, Any],
    last_7_days: Dict[str, Any],
    prev_7_days: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Detect notable anomalies worth alerting the owner about."""
    anomalies = []

    # 1. Revenue drop > 15% vs same day last week
    wow_rev = _pct_change(yesterday["revenue"], same_day_last_week["revenue"])
    if wow_rev is not None and wow_rev < -15:
        anomalies.append({
            "type": "revenue_drop",
            "severity": "high" if wow_rev < -25 else "medium",
            "message": (
                f"Revenue down {format_pct(wow_rev)} vs last week "
                f"({format_currency(yesterday['revenue'])} vs "
                f"{format_currency(same_day_last_week['revenue'])})"
            ),
            "value": wow_rev,
        })

    # 2. Order count drop > 20%
    wow_orders = _pct_change(yesterday["orders"], same_day_last_week["orders"])
    if wow_orders is not None and wow_orders < -20:
        anomalies.append({
            "type": "order_drop",
            "severity": "medium",
            "message": (
                f"Order count down {format_pct(wow_orders)} "
                f"({yesterday['orders']} vs {same_day_last_week['orders']} last week)"
            ),
            "value": wow_orders,
        })

    # 3. AOV change > 15% (up or down — both worth noting)
    wow_aov = _pct_change(yesterday["avg_order_value"], same_day_last_week["avg_order_value"])
    if wow_aov is not None and abs(wow_aov) > 15:
        direction = "up" if wow_aov > 0 else "down"
        anomalies.append({
            "type": "aov_change",
            "severity": "low",
            "message": (
                f"Avg ticket {direction} {format_pct(abs(wow_aov))} to "
                f"{format_currency(yesterday['avg_order_value'])}"
            ),
            "value": wow_aov,
        })

    # 4. Cancellation rate > 5%
    if yesterday["orders"] > 0:
        cancel_rate = (yesterday["cancelled"] / (yesterday["orders"] + yesterday["cancelled"])) * 100
        if cancel_rate > 5:
            anomalies.append({
                "type": "high_cancellations",
                "severity": "high",
                "message": (
                    f"Cancellation rate at {cancel_rate:.1f}% "
                    f"({yesterday['cancelled']} cancelled)"
                ),
                "value": cancel_rate,
            })

    # 5. Weekly trend declining
    wow_week = _pct_change(last_7_days["revenue"], prev_7_days["revenue"])
    if wow_week is not None and wow_week < -10:
        anomalies.append({
            "type": "weekly_decline",
            "severity": "medium",
            "message": (
                f"Weekly revenue declining: {format_pct(wow_week)} over 7 days"
            ),
            "value": wow_week,
        })

    return anomalies


# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------

def _pct_change(current: int, previous: int) -> Optional[float]:
    """Calculate percentage change. Returns None if previous is zero."""
    if previous == 0:
        return None
    return round(((current - previous) / previous) * 100, 1)


def _get_greeting() -> str:
    """Time-appropriate greeting."""
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning! ☀️"
    elif hour < 17:
        return "Good afternoon!"
    else:
        return "Good evening!"
