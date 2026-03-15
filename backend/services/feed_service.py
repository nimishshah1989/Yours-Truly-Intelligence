"""Insight feed service — generates and ranks insight cards.

Cards are the primary visual unit in the YTIP web interface. Each card
answers one question: "What changed, why does it matter, what should I do?"

Card types:
  🔴 attention    — Something needs action NOW
  💰 opportunity  — Money being left on the table
  📈 growth       — Something good is happening
  ⚙️ optimization — Efficiency improvements available

Cards are generated nightly (after ETL) and on-demand.
They're ranked by importance: attention > opportunity > growth > optimization.
Within each category, higher impact = higher priority.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from database import SessionLocal, SessionReadOnly
from models import InsightCard
from services.whatsapp_service import format_currency, format_pct

logger = logging.getLogger("ytip.feed")


def generate_daily_cards(
    restaurant_id: int,
    target_date: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """Generate insight cards for a given day.

    This is the main entry point — called by the scheduler after nightly
    ETL, or on-demand via the API.

    Returns list of card dicts ready for storage.
    """
    if target_date is None:
        target_date = date.today() - timedelta(days=1)

    session = SessionReadOnly()
    cards: List[Dict[str, Any]] = []

    try:
        # --- Revenue insights ---
        cards.extend(_revenue_cards(session, restaurant_id, target_date))

        # --- Menu performance insights ---
        cards.extend(_menu_cards(session, restaurant_id, target_date))

        # --- Operational insights ---
        cards.extend(_operational_cards(session, restaurant_id, target_date))

        # --- Customer insights ---
        cards.extend(_customer_cards(session, restaurant_id, target_date))

        # Store cards in database
        _store_cards(restaurant_id, target_date, cards)

        logger.info(
            "Generated %d insight cards for restaurant %d on %s",
            len(cards), restaurant_id, target_date,
        )
        return cards

    finally:
        session.close()


def get_feed(
    restaurant_id: int,
    limit: int = 20,
    include_dismissed: bool = False,
) -> List[Dict[str, Any]]:
    """Get the current insight feed for the web app.

    Returns cards ranked by: priority (high→low), then recency.
    """
    session = SessionReadOnly()
    try:
        conditions = "restaurant_id = :rid"
        if not include_dismissed:
            conditions += " AND is_dismissed = false"

        rows = session.execute(
            text(f"""
                SELECT
                    id, card_type, priority, headline, body,
                    action_text, action_url, chart_data, comparison,
                    is_read, insight_date, created_at
                FROM insight_cards
                WHERE {conditions}
                ORDER BY
                    CASE priority
                        WHEN 'high' THEN 1
                        WHEN 'medium' THEN 2
                        WHEN 'low' THEN 3
                    END,
                    insight_date DESC,
                    created_at DESC
                LIMIT :lim
            """),
            {"rid": restaurant_id, "lim": limit},
        ).fetchall()

        return [
            {
                "id": r[0],
                "card_type": r[1],
                "priority": r[2],
                "headline": r[3],
                "body": r[4],
                "action_text": r[5],
                "action_url": r[6],
                "chart_data": r[7],
                "comparison": r[8],
                "is_read": r[9],
                "insight_date": r[10].isoformat() if r[10] else None,
                "created_at": r[11].isoformat() if r[11] else None,
            }
            for r in rows
        ]
    except Exception as exc:
        logger.error("Failed to get feed: %s", exc)
        return []
    finally:
        session.close()


# -------------------------------------------------------------------------
# Card generators
# -------------------------------------------------------------------------

def _revenue_cards(
    session: Session, restaurant_id: int, target_date: date,
) -> List[Dict[str, Any]]:
    """Generate revenue-related insight cards."""
    cards = []

    # Get yesterday + same day last week + 7-day trend
    yesterday = _day_revenue(session, restaurant_id, target_date)
    last_week = _day_revenue(session, restaurant_id, target_date - timedelta(days=7))
    two_weeks = _day_revenue(session, restaurant_id, target_date - timedelta(days=14))

    if yesterday["revenue"] == 0:
        return cards

    # Card: Daily revenue summary (always show)
    wow_pct = _pct(yesterday["revenue"], last_week["revenue"])
    trend = "up" if (wow_pct or 0) > 0 else "down"
    emoji_map = {"up": "📈", "down": "📉"}

    # Get last 7 days for sparkline
    sparkline = _revenue_sparkline(session, restaurant_id, target_date, days=7)

    cards.append({
        "card_type": "growth" if (wow_pct or 0) >= 0 else "attention",
        "priority": "high" if abs(wow_pct or 0) > 15 else "medium",
        "headline": f"Revenue {trend} {format_pct(abs(wow_pct))} vs last week" if wow_pct is not None else f"Revenue: {format_currency(yesterday['revenue'])}",
        "body": (
            f"Yesterday: {format_currency(yesterday['revenue'])} "
            f"from {yesterday['orders']} orders\n"
            f"Avg ticket: {format_currency(yesterday['aov'])}"
        ),
        "comparison": f"Last week: {format_currency(last_week['revenue'])}",
        "chart_data": {"type": "sparkline", "values": sparkline},
        "action_text": "View revenue breakdown",
        "action_url": "/revenue",
    })

    # Card: Weekend vs weekday performance (if weekend)
    dow = target_date.weekday()
    if dow in (4, 5, 6):  # Fri, Sat, Sun
        weekday_avg = _weekday_avg_revenue(session, restaurant_id, target_date, days=14)
        if weekday_avg > 0:
            weekend_lift = _pct(yesterday["revenue"], weekday_avg)
            if weekend_lift is not None and weekend_lift > 20:
                cards.append({
                    "card_type": "growth",
                    "priority": "low",
                    "headline": f"Weekend lift: {format_pct(weekend_lift)} above weekday avg",
                    "body": (
                        f"Yesterday's {format_currency(yesterday['revenue'])} is "
                        f"{format_pct(weekend_lift)} above your average weekday "
                        f"({format_currency(weekday_avg)})."
                    ),
                    "comparison": f"Weekday avg: {format_currency(weekday_avg)}",
                })

    return cards


def _menu_cards(
    session: Session, restaurant_id: int, target_date: date,
) -> List[Dict[str, Any]]:
    """Generate menu performance insight cards."""
    cards = []

    # Top item concentration
    top_items = _top_items_with_share(session, restaurant_id, target_date)
    if len(top_items) >= 5:
        top5_share = sum(it["share"] for it in top_items[:5])
        if top5_share > 60:
            items_text = "\n".join(
                f"• {it['name']}: {format_currency(it['revenue'])} ({it['share']:.0f}%)"
                for it in top_items[:5]
            )
            cards.append({
                "card_type": "attention",
                "priority": "medium",
                "headline": f"Top 5 items = {top5_share:.0f}% of revenue",
                "body": (
                    f"Heavy concentration risk. If any of these items "
                    f"has supply issues, impact is significant.\n\n{items_text}"
                ),
                "action_text": "View menu analysis",
                "action_url": "/menu",
            })

    # Items with declining sales (compare last 7d vs prev 7d)
    declining = _declining_items(session, restaurant_id, target_date)
    if declining:
        decline_text = "\n".join(
            f"• {it['name']}: {format_pct(it['change'])} "
            f"({it['this_week_qty']}× vs {it['last_week_qty']}×)"
            for it in declining[:3]
        )
        cards.append({
            "card_type": "attention",
            "priority": "medium",
            "headline": f"{len(declining)} items declining this week",
            "body": (
                f"These items saw significant drops in the last 7 days:\n\n"
                f"{decline_text}"
            ),
            "action_text": "View item performance",
            "action_url": "/menu",
        })

    return cards


def _operational_cards(
    session: Session, restaurant_id: int, target_date: date,
) -> List[Dict[str, Any]]:
    """Generate operational insight cards.

    Always generates at least the peak hours card if there's any order data.
    Area performance shows when there are 2+ areas with meaningful difference.
    """
    cards = []

    # Area performance — show if 2+ areas exist
    areas = _area_performance(session, restaurant_id, target_date)
    if len(areas) >= 2:
        best = areas[0]
        worst = areas[-1]
        ratio = best["revenue"] / max(worst["revenue"], 1)

        # Always show area breakdown (lowered threshold from 3× to 1.5×)
        if ratio > 1.5:
            cards.append({
                "card_type": "optimization",
                "priority": "low" if ratio < 3 else "medium",
                "headline": f"{best['area']} leads with {format_currency(best['revenue'])}",
                "body": (
                    f"Top: {best['area']} — {format_currency(best['revenue'])} "
                    f"({best['orders']} orders)\n"
                    f"Bottom: {worst['area']} — {format_currency(worst['revenue'])} "
                    f"({worst['orders']} orders)\n"
                    f"Spread: {ratio:.1f}× difference"
                ),
                "action_text": "View area heatmap",
                "action_url": "/operations",
            })

    # Peak hour analysis — always show if there's data
    peak = _peak_hours(session, restaurant_id, target_date)
    if peak:
        peak_str = ", ".join(f"{h['hour']}:00" for h in peak[:3])
        total_orders = sum(h["orders"] for h in peak)
        total_rev = sum(h["revenue"] for h in peak)
        cards.append({
            "card_type": "optimization",
            "priority": "low",
            "headline": f"Peak hours: {peak_str}",
            "body": (
                f"Busiest: {peak[0]['hour']}:00 — "
                f"{peak[0]['orders']} orders, "
                f"{format_currency(peak[0]['revenue'])}\n"
                f"Total yesterday: {total_orders} orders, "
                f"{format_currency(total_rev)}"
            ),
            "chart_data": {
                "type": "sparkline",
                "values": [h["orders"] for h in sorted(peak, key=lambda x: x["hour"])],
            },
            "action_text": "View hourly breakdown",
            "action_url": "/operations",
        })

    # Order type mix (dine-in vs delivery vs takeaway)
    order_mix = _order_type_mix(session, restaurant_id, target_date)
    if order_mix and len(order_mix) >= 2:
        top_type = order_mix[0]
        mix_str = " · ".join(
            f"{m['type']}: {m['pct']:.0f}%"
            for m in order_mix[:3]
        )
        cards.append({
            "card_type": "optimization",
            "priority": "low",
            "headline": f"{top_type['type']} dominates at {top_type['pct']:.0f}%",
            "body": f"Order mix: {mix_str}",
        })

    return cards


def _customer_cards(
    session: Session, restaurant_id: int, target_date: date,
) -> List[Dict[str, Any]]:
    """Generate customer insight cards."""
    cards = []

    # New vs returning customer ratio
    customer_mix = _customer_mix(session, restaurant_id, target_date)
    if customer_mix["total"] > 10:
        new_pct = (customer_mix["new"] / customer_mix["total"]) * 100
        if new_pct > 40:
            cards.append({
                "card_type": "growth",
                "priority": "medium",
                "headline": f"{new_pct:.0f}% new customers yesterday",
                "body": (
                    f"{customer_mix['new']} new customers out of "
                    f"{customer_mix['total']} total. "
                    f"Your discovery/marketing is working."
                ),
            })
        elif new_pct < 15:
            cards.append({
                "card_type": "opportunity",
                "priority": "medium",
                "headline": f"Only {new_pct:.0f}% new customers — mostly regulars",
                "body": (
                    f"Strong retention ({100-new_pct:.0f}% returning), "
                    f"but may need fresh traffic. Consider marketing push."
                ),
                "action_text": "View customer segments",
                "action_url": "/customers",
            })

    return cards


# -------------------------------------------------------------------------
# Data queries
# -------------------------------------------------------------------------

def _day_revenue(session: Session, rid: int, dt: date) -> Dict[str, Any]:
    row = session.execute(
        text("""
            SELECT COUNT(*), COALESCE(SUM(total_amount),0), COALESCE(AVG(total_amount),0)
            FROM orders
            WHERE restaurant_id = :rid AND DATE(ordered_at) = :dt
              AND is_cancelled = false AND status = 'completed'
        """),
        {"rid": rid, "dt": dt},
    ).fetchone()
    return {
        "orders": int(row[0]) if row else 0,
        "revenue": int(row[1]) if row else 0,
        "aov": int(row[2]) if row else 0,
    }


def _revenue_sparkline(session: Session, rid: int, end: date, days: int = 7) -> List[int]:
    start = end - timedelta(days=days - 1)
    rows = session.execute(
        text("""
            SELECT DATE(ordered_at), COALESCE(SUM(total_amount),0)
            FROM orders
            WHERE restaurant_id = :rid
              AND DATE(ordered_at) BETWEEN :start AND :end
              AND is_cancelled = false AND status = 'completed'
            GROUP BY DATE(ordered_at)
            ORDER BY DATE(ordered_at)
        """),
        {"rid": rid, "start": start, "end": end},
    ).fetchall()
    return [int(r[1]) for r in rows]


def _weekday_avg_revenue(session: Session, rid: int, before: date, days: int = 14) -> int:
    start = before - timedelta(days=days)
    row = session.execute(
        text("""
            SELECT AVG(day_rev) FROM (
                SELECT DATE(ordered_at), SUM(total_amount) AS day_rev
                FROM orders
                WHERE restaurant_id = :rid
                  AND DATE(ordered_at) BETWEEN :start AND :end
                  AND EXTRACT(DOW FROM ordered_at) BETWEEN 1 AND 5
                  AND is_cancelled = false AND status = 'completed'
                GROUP BY DATE(ordered_at)
            ) sub
        """),
        {"rid": rid, "start": start, "end": before - timedelta(days=1)},
    ).fetchone()
    return int(row[0]) if row and row[0] else 0


def _top_items_with_share(session: Session, rid: int, dt: date) -> List[Dict[str, Any]]:
    rows = session.execute(
        text("""
            WITH filtered_items AS (
                SELECT oi.item_name, oi.quantity, oi.total_price
                FROM order_items oi
                JOIN orders o ON o.id = oi.order_id
                WHERE oi.restaurant_id = :rid AND DATE(o.ordered_at) = :dt
                  AND o.is_cancelled = false AND o.status = 'completed'
                  AND oi.unit_price > 0
                  AND COALESCE(oi.category, '') NOT IN ('Add Ons', 'Addons', 'Modifiers', 'Packaging')
                  AND oi.item_name NOT ILIKE '%mineral water%'
                  AND oi.item_name NOT ILIKE '%bisleri%'
                  AND oi.item_name NOT ILIKE '%carry bag%'
                  AND oi.item_name NOT ILIKE '%packing%'
            ),
            totals AS (
                SELECT SUM(total_price) AS grand_total FROM filtered_items
            )
            SELECT item_name, SUM(quantity) AS qty, SUM(total_price) AS rev,
                   ROUND(SUM(total_price)*100.0 / NULLIF((SELECT grand_total FROM totals),0), 1) AS share
            FROM filtered_items
            GROUP BY item_name
            ORDER BY rev DESC
            LIMIT 10
        """),
        {"rid": rid, "dt": dt},
    ).fetchall()
    return [
        {"name": r[0], "qty": int(r[1]), "revenue": int(r[2]), "share": float(r[3] or 0)}
        for r in rows
    ]


def _declining_items(session: Session, rid: int, end: date) -> List[Dict[str, Any]]:
    this_start = end - timedelta(days=6)
    last_start = end - timedelta(days=13)
    last_end = end - timedelta(days=7)

    rows = session.execute(
        text("""
            WITH this_week AS (
                SELECT oi.item_name, SUM(oi.quantity) AS qty
                FROM order_items oi JOIN orders o ON o.id = oi.order_id
                WHERE oi.restaurant_id = :rid
                  AND DATE(o.ordered_at) BETWEEN :tw_start AND :tw_end
                  AND o.is_cancelled = false AND o.status = 'completed'
                GROUP BY oi.item_name
            ),
            last_week AS (
                SELECT oi.item_name, SUM(oi.quantity) AS qty
                FROM order_items oi JOIN orders o ON o.id = oi.order_id
                WHERE oi.restaurant_id = :rid
                  AND DATE(o.ordered_at) BETWEEN :lw_start AND :lw_end
                  AND o.is_cancelled = false AND o.status = 'completed'
                GROUP BY oi.item_name
            )
            SELECT lw.item_name, tw.qty, lw.qty,
                   ROUND((tw.qty - lw.qty)*100.0 / NULLIF(lw.qty, 0), 1) AS pct_change
            FROM last_week lw
            LEFT JOIN this_week tw ON tw.item_name = lw.item_name
            WHERE lw.qty >= 10  -- only items with meaningful volume
              AND (tw.qty IS NULL OR tw.qty < lw.qty * 0.7)  -- >30% decline
            ORDER BY lw.qty DESC
            LIMIT 5
        """),
        {
            "rid": rid,
            "tw_start": this_start, "tw_end": end,
            "lw_start": last_start, "lw_end": last_end,
        },
    ).fetchall()
    return [
        {
            "name": r[0],
            "this_week_qty": int(r[1] or 0),
            "last_week_qty": int(r[2]),
            "change": float(r[3] or -100),
        }
        for r in rows
    ]


def _area_performance(session: Session, rid: int, dt: date) -> List[Dict[str, Any]]:
    rows = session.execute(
        text("""
            SELECT COALESCE(sub_order_type, order_type), COUNT(*), SUM(total_amount)
            FROM orders
            WHERE restaurant_id = :rid AND DATE(ordered_at) = :dt
              AND is_cancelled = false AND status = 'completed'
            GROUP BY COALESCE(sub_order_type, order_type)
            ORDER BY SUM(total_amount) DESC
        """),
        {"rid": rid, "dt": dt},
    ).fetchall()
    return [
        {"area": r[0] or "Unknown", "orders": int(r[1]), "revenue": int(r[2])}
        for r in rows
    ]


def _peak_hours(session: Session, rid: int, dt: date) -> List[Dict[str, Any]]:
    rows = session.execute(
        text("""
            SELECT EXTRACT(HOUR FROM ordered_at)::int AS hr,
                   COUNT(*) AS orders, SUM(total_amount) AS revenue
            FROM orders
            WHERE restaurant_id = :rid AND DATE(ordered_at) = :dt
              AND is_cancelled = false AND status = 'completed'
            GROUP BY hr
            ORDER BY orders DESC
            LIMIT 8
        """),
        {"rid": rid, "dt": dt},
    ).fetchall()
    return [
        {"hour": int(r[0]), "orders": int(r[1]), "revenue": int(r[2])}
        for r in rows
    ]


def _order_type_mix(session: Session, rid: int, dt: date) -> List[Dict[str, Any]]:
    """Get order type distribution for a day."""
    rows = session.execute(
        text("""
            SELECT order_type, COUNT(*) AS cnt,
                   ROUND(COUNT(*) * 100.0 / NULLIF(SUM(COUNT(*)) OVER(), 0), 1) AS pct
            FROM orders
            WHERE restaurant_id = :rid AND DATE(ordered_at) = :dt
              AND is_cancelled = false AND status = 'completed'
            GROUP BY order_type
            ORDER BY cnt DESC
        """),
        {"rid": rid, "dt": dt},
    ).fetchall()
    return [{"type": r[0] or "Unknown", "count": int(r[1]), "pct": float(r[2] or 0)} for r in rows]


def _customer_mix(session: Session, rid: int, dt: date) -> Dict[str, int]:
    row = session.execute(
        text("""
            SELECT
                COUNT(DISTINCT customer_id) AS total_with_id,
                COUNT(DISTINCT CASE WHEN c.total_visits = 1 THEN customer_id END) AS new_customers
            FROM orders o
            LEFT JOIN customers c ON c.id = o.customer_id
            WHERE o.restaurant_id = :rid AND DATE(o.ordered_at) = :dt
              AND o.is_cancelled = false AND o.status = 'completed'
              AND o.customer_id IS NOT NULL
        """),
        {"rid": rid, "dt": dt},
    ).fetchone()
    total = int(row[0]) if row else 0
    new = int(row[1]) if row else 0
    return {"total": total, "new": new, "returning": total - new}


# -------------------------------------------------------------------------
# Storage
# -------------------------------------------------------------------------

def _store_cards(
    restaurant_id: int, target_date: date, cards: List[Dict[str, Any]],
) -> None:
    """Store generated cards in the database, replacing old ones for the same date."""
    session = SessionLocal()
    try:
        # Delete existing cards for this date (regeneration)
        session.execute(
            text("""
                DELETE FROM insight_cards
                WHERE restaurant_id = :rid AND insight_date = :dt
            """),
            {"rid": restaurant_id, "dt": target_date},
        )

        for card in cards:
            session.execute(
                text("""
                    INSERT INTO insight_cards
                    (restaurant_id, card_type, priority, headline, body,
                     action_text, action_url, chart_data, comparison,
                     is_read, is_dismissed, insight_date)
                    VALUES (:rid, :ct, :pr, :hl, :body,
                            :at, :au, CAST(:cd AS jsonb), :comp,
                            false, false, :dt)
                """),
                {
                    "rid": restaurant_id,
                    "ct": card.get("card_type", "optimization"),
                    "pr": card.get("priority", "medium"),
                    "hl": card["headline"],
                    "body": card["body"],
                    "at": card.get("action_text"),
                    "au": card.get("action_url"),
                    "cd": _json_dumps(card.get("chart_data")),
                    "comp": card.get("comparison"),
                    "dt": target_date,
                },
            )

        session.commit()
        logger.info("Stored %d cards for restaurant %d on %s", len(cards), restaurant_id, target_date)
    except Exception as exc:
        session.rollback()
        logger.error("Failed to store cards: %s", exc)
    finally:
        session.close()


# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------

def _pct(current: int, previous: int) -> Optional[float]:
    if previous == 0:
        return None
    return round(((current - previous) / previous) * 100, 1)


def _json_dumps(obj: Any) -> Optional[str]:
    if obj is None:
        return None
    import json
    return json.dumps(obj, default=str)
