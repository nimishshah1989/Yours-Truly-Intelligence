"""Claude-powered insight generator — transforms raw data into narratives.

Uses Claude Haiku for cost efficiency (~$0.01-0.03 per call). Generates:
  - Deep intelligence findings from cross-signal analysis
  - Briefing narrative from structured KPI data
  - Home page insight summary
"""

import json
import logging
import os
import uuid
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import anthropic
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from models import (
    DailySummary,
    IntelligenceFinding,
    Order,
    OrderItem,
)
from services.whatsapp_service import format_currency

logger = logging.getLogger("ytip.insight_generator")

_client: Optional[anthropic.Anthropic] = None


def _get_client() -> Optional[anthropic.Anthropic]:
    global _client
    if _client is None:
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            return None
        _client = anthropic.Anthropic(api_key=key)
    return _client


# ---------------------------------------------------------------------------
# Deep intelligence — Claude analyzes real data, produces rich findings
# ---------------------------------------------------------------------------

def generate_deep_insights(
    db: Session,
    restaurant_id: int,
    as_of: Optional[date] = None,
) -> List[IntelligenceFinding]:
    """Query the DB for key signals, send to Claude for cross-signal analysis.

    Returns a list of IntelligenceFinding objects ready to persist.
    Costs ~$0.03 per run (Haiku).
    """
    client = _get_client()
    if not client:
        logger.warning("No Anthropic API key — skipping deep insights")
        return []

    if as_of is None:
        as_of = date.today() - timedelta(days=1)

    # Gather data signals
    data_pack = _gather_data_signals(db, restaurant_id, as_of)
    if not data_pack:
        return []

    prompt = f"""You are the Chief of Staff for YoursTruly, a specialty coffee roaster in Kolkata (restaurant_id={restaurant_id}).

Analyze the following business data and generate 5-8 actionable intelligence findings. Each finding should be something the owner can ACT on to grow revenue, cut costs, or improve service.

DO NOT just restate numbers. Every finding must answer: "So what? What should I do?"

=== DATA ===
{json.dumps(data_pack, indent=2, default=str)}

=== RULES ===
- All monetary amounts are in PAISA (divide by 100 for rupees). Display as ₹X,XXX format.
- Focus on cross-signal insights (e.g., if an item is declining AND has low COGS, that's a pricing opportunity)
- Categories must be one of: revenue, cost, menu, operations
- Severity must be one of: critical, alert, watch, info
- Each finding needs a clear title (max 80 chars), a narrative explanation, and a specific recommended action
- Rupee impact should be a realistic MONTHLY estimate in paisa. If you can't estimate, use null.
- Don't generate findings about things that are going well unless there's an action to capitalize on it
- Keep narratives to 2 sentences max. Keep actions to 1 sentence max.

Return ONLY a JSON array (no markdown, no explanation). Each object:
{"category":"...","severity":"...","title":"max 60 chars","narrative":"2 sentences","action":"1 sentence","rupee_impact":null,"related_items":null}"""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()

        # Parse JSON — handle markdown code blocks
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

        insights = json.loads(raw)
        if not isinstance(insights, list):
            logger.error("Claude returned non-list: %s", type(insights))
            return []

        findings = []
        for ins in insights:
            findings.append(IntelligenceFinding(
                restaurant_id=restaurant_id,
                finding_date=as_of,
                category=ins.get("category", "operations"),
                severity=ins.get("severity", "info"),
                title=ins.get("title", "Untitled insight")[:200],
                detail={
                    "narrative": ins.get("narrative", ""),
                    "action": ins.get("action", ""),
                    "source": "claude_deep_analysis",
                },
                related_items=ins.get("related_items"),
                rupee_impact=ins.get("rupee_impact"),
            ))

        logger.info("Generated %d deep insights for %s", len(findings), as_of)
        return findings

    except json.JSONDecodeError as exc:
        logger.error("Failed to parse Claude insights JSON: %s", exc)
        return []
    except Exception as exc:
        logger.error("Deep insight generation failed: %s", exc)
        return []


def _gather_data_signals(
    db: Session, restaurant_id: int, as_of: date
) -> Optional[Dict[str, Any]]:
    """Query DB for the data pack Claude needs to analyze."""
    try:
        # 1. Last 7 days revenue + orders
        daily_rev = db.execute(text("""
            SELECT DATE(ordered_at) AS d, COUNT(*) AS orders,
                   SUM(net_amount) AS revenue, AVG(net_amount) AS avg_ticket
            FROM orders
            WHERE restaurant_id = :rid AND is_cancelled = false
              AND DATE(ordered_at) BETWEEN :start AND :end
            GROUP BY DATE(ordered_at) ORDER BY d
        """), {"rid": restaurant_id, "start": as_of - timedelta(days=6), "end": as_of}).fetchall()

        daily_data = [
            {"date": str(r[0]), "orders": int(r[1]),
             "revenue": int(r[2]), "avg_ticket": int(r[3])}
            for r in daily_rev
        ]

        # 2. Top 15 items by revenue (last 30 days)
        top_items = db.execute(text("""
            SELECT oi.item_name, SUM(oi.quantity) AS qty,
                   SUM(oi.total_price) AS revenue,
                   COALESCE(AVG(NULLIF(oi.cost_price, 0)), 0) AS avg_cost
            FROM order_items oi
            JOIN orders o ON o.id = oi.order_id
            WHERE o.restaurant_id = :rid AND o.is_cancelled = false
              AND DATE(o.ordered_at) BETWEEN :start AND :end
            GROUP BY oi.item_name ORDER BY revenue DESC LIMIT 15
        """), {"rid": restaurant_id, "start": as_of - timedelta(days=29), "end": as_of}).fetchall()

        items_data = [
            {"name": r[0], "qty_sold": int(r[1]),
             "revenue": int(r[2]), "avg_cost": int(r[3])}
            for r in top_items
        ]

        # 3. Items trending down (compare last 2 weeks vs prior 2 weeks)
        trending = db.execute(text("""
            WITH recent AS (
                SELECT oi.item_name, SUM(oi.quantity) AS qty
                FROM order_items oi JOIN orders o ON o.id = oi.order_id
                WHERE o.restaurant_id = :rid AND o.is_cancelled = false
                  AND DATE(o.ordered_at) BETWEEN :r_start AND :r_end
                GROUP BY oi.item_name
            ),
            prior AS (
                SELECT oi.item_name, SUM(oi.quantity) AS qty
                FROM order_items oi JOIN orders o ON o.id = oi.order_id
                WHERE o.restaurant_id = :rid AND o.is_cancelled = false
                  AND DATE(o.ordered_at) BETWEEN :p_start AND :p_end
                GROUP BY oi.item_name
            )
            SELECT r.item_name, r.qty AS recent_qty, p.qty AS prior_qty,
                   ROUND((r.qty::numeric - p.qty) / NULLIF(p.qty, 0) * 100, 1) AS change_pct
            FROM recent r JOIN prior p ON r.item_name = p.item_name
            WHERE p.qty > 10
            ORDER BY change_pct ASC LIMIT 10
        """), {
            "rid": restaurant_id,
            "r_start": as_of - timedelta(days=13), "r_end": as_of,
            "p_start": as_of - timedelta(days=27), "p_end": as_of - timedelta(days=14),
        }).fetchall()

        trending_data = [
            {"name": r[0], "recent_qty": int(r[1]),
             "prior_qty": int(r[2]), "change_pct": float(r[3]) if r[3] else 0}
            for r in trending
        ]

        # 4. Day-of-week performance (last 8 weeks)
        dow_perf = db.execute(text("""
            SELECT EXTRACT(DOW FROM ordered_at)::int AS dow,
                   COUNT(*) AS orders, SUM(net_amount) AS revenue
            FROM orders
            WHERE restaurant_id = :rid AND is_cancelled = false
              AND DATE(ordered_at) BETWEEN :start AND :end
            GROUP BY dow ORDER BY dow
        """), {"rid": restaurant_id, "start": as_of - timedelta(days=55), "end": as_of}).fetchall()

        dow_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        dow_data = [
            {"day": dow_names[int(r[0])], "orders": int(r[1]), "revenue": int(r[2])}
            for r in dow_perf
        ]

        # 5. COGS data (last 7 days)
        cogs_data = db.execute(text("""
            SELECT DATE(o.ordered_at) AS d,
                   SUM(oi.cost_price * oi.quantity) AS cogs,
                   SUM(oi.total_price) AS item_rev
            FROM order_items oi
            JOIN orders o ON o.id = oi.order_id
            WHERE o.restaurant_id = :rid AND o.is_cancelled = false
              AND oi.cost_price > 0
              AND DATE(o.ordered_at) BETWEEN :start AND :end
            GROUP BY DATE(o.ordered_at) ORDER BY d
        """), {"rid": restaurant_id, "start": as_of - timedelta(days=6), "end": as_of}).fetchall()

        cogs = [
            {"date": str(r[0]), "cogs": int(r[1]), "item_revenue": int(r[2]),
             "cogs_pct": round(int(r[1]) / max(int(r[2]), 1) * 100, 1)}
            for r in cogs_data
        ]

        # 6. Order type / channel mix
        channel_mix = db.execute(text("""
            SELECT COALESCE(order_type, 'unknown') AS channel,
                   COUNT(*) AS orders, SUM(net_amount) AS revenue
            FROM orders
            WHERE restaurant_id = :rid AND is_cancelled = false
              AND DATE(ordered_at) BETWEEN :start AND :end
            GROUP BY order_type ORDER BY revenue DESC
        """), {"rid": restaurant_id, "start": as_of - timedelta(days=6), "end": as_of}).fetchall()

        channels = [
            {"channel": r[0], "orders": int(r[1]), "revenue": int(r[2])}
            for r in channel_mix
        ]

        # 7. Hourly distribution (yesterday only)
        hourly = db.execute(text("""
            SELECT EXTRACT(HOUR FROM ordered_at)::int AS hr,
                   COUNT(*) AS orders, SUM(net_amount) AS revenue
            FROM orders
            WHERE restaurant_id = :rid AND is_cancelled = false
              AND DATE(ordered_at) = :dt
            GROUP BY hr ORDER BY hr
        """), {"rid": restaurant_id, "dt": as_of}).fetchall()

        hourly_data = [
            {"hour": int(r[0]), "orders": int(r[1]), "revenue": int(r[2])}
            for r in hourly
        ]

        return {
            "analysis_date": str(as_of),
            "daily_performance_last_7_days": daily_data,
            "top_15_items_last_30_days": items_data,
            "items_trending_down": trending_data,
            "day_of_week_performance_8_weeks": dow_data,
            "cogs_last_7_days": cogs,
            "channel_mix_last_7_days": channels,
            "hourly_distribution_yesterday": hourly_data,
        }

    except Exception as exc:
        logger.error("Failed to gather data signals: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Briefing narrative
# ---------------------------------------------------------------------------

def generate_briefing_narrative(
    metrics: Dict[str, Any],
    sections: List[Dict[str, str]],
    anomalies: List[Dict[str, Any]],
    restaurant_name: str = "YoursTruly",
) -> Optional[str]:
    """Generate a Claude narrative from briefing data."""
    client = _get_client()
    if not client:
        return None

    yesterday = metrics.get("yesterday", {})
    same_day_lw = metrics.get("same_day_last_week", {})
    last_7 = metrics.get("last_7_days", {})
    top_items = metrics.get("top_items", [])

    prompt = f"""You are the Chief of Staff for {restaurant_name}, a specialty coffee roaster in Kolkata.
Analyze yesterday's performance and give the owner 3-5 sentences of actionable insight. Be specific, mention items by name, and suggest one concrete action.

Yesterday's data:
- Revenue: {format_currency(yesterday.get('revenue', 0))} ({yesterday.get('orders', 0)} orders, avg ticket {format_currency(yesterday.get('avg_order_value', 0))})
- Same day last week: {format_currency(same_day_lw.get('revenue', 0))} ({same_day_lw.get('orders', 0)} orders)
- 7-day total: {format_currency(last_7.get('revenue', 0))} ({last_7.get('orders', 0)} orders)
- Top items: {', '.join(f"{it['name']} ({it['qty']}x, {format_currency(it['revenue'])})" for it in top_items[:5])}

Anomalies detected: {len(anomalies)}
{chr(10).join(f"- {a['message']}" for a in anomalies[:3]) if anomalies else "None"}

Rules:
- All amounts are in paisa (divide by 100 for rupees). Display as rupee format.
- Be conversational, not robotic. No bullet points.
- Focus on "so what" and "what to do", not restating numbers.
- If revenue is down, suggest specific actions (promo, combo, timing).
- If an item is trending, suggest featuring it or creating a combo."""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as exc:
        logger.error("Insight generation failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Home page insight
# ---------------------------------------------------------------------------

def generate_home_insight(
    stats: Dict[str, Any],
    findings_summary: Dict[str, Any],
    restaurant_name: str = "YoursTruly",
) -> Optional[str]:
    """Generate a 2-3 sentence home page insight from stats + findings."""
    client = _get_client()
    if not client:
        return None

    prompt = f"""You are the Chief of Staff for {restaurant_name} coffee roaster in Kolkata.
Based on these numbers, give the owner 2-3 sentences of morning insight.

Yesterday: Revenue {format_currency(stats.get('revenue_yesterday', 0))}, {stats.get('orders_yesterday', 0)} orders, avg ticket {format_currency(stats.get('avg_ticket', 0))}, COGS {stats.get('cogs_pct', 'N/A')}%
Active findings: {findings_summary.get('total_findings', 0)} patterns detected
Top category: {findings_summary.get('top_category', 'none')} ({findings_summary.get('top_category_count', 0)} findings)

Rules:
- Amounts in paisa (divide by 100 = rupees). Display as rupee format.
- Be warm, specific, actionable. No bullet points.
- Start with the most important thing.
- If COGS > 35%, flag it. If orders are strong, celebrate briefly then push for more."""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as exc:
        logger.error("Home insight generation failed: %s", exc)
        return None
