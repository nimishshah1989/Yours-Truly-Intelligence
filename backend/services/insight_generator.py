"""Claude-powered insight generator — transforms raw data into narratives.

Uses Claude Haiku for cost efficiency (~$0.01 per call). Generates:
  - Briefing narrative from structured KPI data
  - Chart commentary for dashboard visuals
  - Finding explanations with actionable advice
"""

import logging
import os
from typing import Any, Dict, List, Optional

import anthropic

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


def generate_briefing_narrative(
    metrics: Dict[str, Any],
    sections: List[Dict[str, str]],
    anomalies: List[Dict[str, Any]],
    restaurant_name: str = "YoursTruly",
) -> Optional[str]:
    """Generate a Claude narrative from briefing data.

    Returns a 3-5 sentence insight paragraph, or None on failure.
    """
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
- Top items: {', '.join(f"{it['name']} ({it['qty']}×, {format_currency(it['revenue'])})" for it in top_items[:5])}

Anomalies detected: {len(anomalies)}
{chr(10).join(f"- {a['message']}" for a in anomalies[:3]) if anomalies else "None"}

Rules:
- All amounts are in paisa (divide by 100 for rupees). Display as ₹X,XXX format.
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


def generate_finding_insight(
    finding_title: str,
    finding_detail: Optional[Dict[str, Any]],
    category: str,
    restaurant_name: str = "YoursTruly",
) -> Optional[str]:
    """Generate a 2-sentence explanation + action for a single finding."""
    client = _get_client()
    if not client:
        return None

    detail_str = ""
    if finding_detail:
        detail_str = "\n".join(f"- {k}: {v}" for k, v in finding_detail.items())

    prompt = f"""You are the Chief of Staff for {restaurant_name} coffee roaster.
A pattern detector flagged this finding:

Title: {finding_title}
Category: {category}
Details:
{detail_str}

In 2 sentences: (1) explain why this matters to a restaurant owner, (2) suggest one specific action.
Be direct and conversational. All amounts in paisa (÷100 for rupees)."""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as exc:
        logger.error("Finding insight generation failed: %s", exc)
        return None


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
- Amounts in paisa (÷100 = rupees). Display as ₹X,XXX.
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
