"""Digest service — generate AI-powered daily/weekly/monthly digests via Claude.

Uses Claude claude-sonnet-4-6 to produce structured, data-driven management digests.
Context assembly is in digest_context.py (split to stay under file size limit).
Each digest is persisted to the digests table.
"""

import logging
from datetime import date, timedelta

import anthropic
from sqlalchemy.orm import Session

from config import settings
from models import Digest
from services.alert_service import evaluate_daily_alerts, get_alert_summary_text
from services.digest_context import (
    build_daily_context,
    build_monthly_context,
    build_weekly_context,
)

logger = logging.getLogger("ytip.digest")

CLAUDE_MODEL = "claude-sonnet-4-6"
DAILY_MAX_TOKENS = 1000
WEEKLY_MAX_TOKENS = 1000
MONTHLY_MAX_TOKENS = 1500

SYSTEM_PROMPT = (
    "You are an expert restaurant intelligence analyst for YoursTruly Café in India. "
    "Analyze operational data and generate concise, actionable digests for the owner. "
    "Be specific with numbers, compare to baselines, and highlight what needs immediate attention."
)


def _claude_client() -> anthropic.Anthropic:
    """Return an Anthropic client using the configured API key."""
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _persist_digest(
    db: Session,
    restaurant_id: int,
    digest_type: str,
    period_start: date,
    period_end: date,
    content: str,
) -> Digest:
    """Create and commit a Digest row, then return the refreshed object."""
    digest = Digest(
        restaurant_id=restaurant_id,
        digest_type=digest_type,
        period_start=period_start,
        period_end=period_end,
        content=content,
        widgets=None,
    )
    db.add(digest)
    db.commit()
    db.refresh(digest)
    return digest


def generate_daily_digest(
    restaurant_id: int, target_date: date, db: Session
) -> Digest:
    """Generate a daily digest using Claude claude-sonnet-4-6.

    Produces 3 key observations, 1 concern, and 2 recommended actions.
    Alert results are embedded in the prompt context.
    """
    context = build_daily_context(restaurant_id, target_date, db)
    alert_results = evaluate_daily_alerts(restaurant_id, target_date, db)
    alert_text = get_alert_summary_text(alert_results)

    user_prompt = f"""Restaurant daily operational data for {target_date}:

{context}

Active Alerts:
{alert_text}

Generate a daily digest with exactly these sections:
1. TOP 3 INSIGHTS (numbered, include specific numbers, compare to recent baseline where available)
2. CONCERN (one key anomaly or risk — if none, state "No significant concerns today")
3. RECOMMENDED ACTIONS (exactly 2 specific, actionable items for the owner to act on today)

Keep each section concise. Use Indian Rupee amounts (₹). Be direct and data-driven."""

    client = _claude_client()
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=DAILY_MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    content = message.content[0].text

    digest = _persist_digest(db, restaurant_id, "daily", target_date, target_date, content)
    logger.info(
        "Daily digest generated: restaurant_id=%d date=%s digest_id=%d",
        restaurant_id,
        target_date,
        digest.id,
    )
    return digest


def generate_weekly_digest(
    restaurant_id: int, week_start: date, db: Session
) -> Digest:
    """Generate a weekly digest covering Mon–Sun, for Monday 9 AM runs."""
    week_end = week_start + timedelta(days=6)
    context = build_weekly_context(restaurant_id, week_start, week_end, db)

    user_prompt = f"""Weekly operational data for YoursTruly Café:

{context}

Generate a weekly digest with:
1. WEEK SUMMARY (3 key metrics and how they compare to expectations)
2. TOP TREND (most significant pattern this week)
3. CONCERN (if any — otherwise "No significant concerns")
4. NEXT WEEK PRIORITIES (2 specific actions for the coming week)

Use Indian Rupee amounts (₹). Be concise and actionable."""

    client = _claude_client()
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=WEEKLY_MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    content = message.content[0].text

    digest = _persist_digest(db, restaurant_id, "weekly", week_start, week_end, content)
    logger.info(
        "Weekly digest generated: restaurant_id=%d week=%s digest_id=%d",
        restaurant_id,
        week_start,
        digest.id,
    )
    return digest


def generate_monthly_digest(
    restaurant_id: int, month_start: date, db: Session
) -> Digest:
    """Generate a monthly P&L + strategic recommendations digest."""
    if month_start.month == 12:
        month_end = month_start.replace(year=month_start.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        month_end = month_start.replace(month=month_start.month + 1, day=1) - timedelta(days=1)

    context = build_monthly_context(restaurant_id, month_start, month_end, db)

    user_prompt = f"""Monthly operational data for YoursTruly Café:

{context}

Generate a monthly management digest with:
1. MONTHLY P&L SUMMARY (revenue, discounts, commissions, net — with % breakdown)
2. TOP 3 INSIGHTS (most significant patterns this month)
3. CONCERNS (up to 2 issues that need attention)
4. STRATEGIC RECOMMENDATIONS (3 specific recommendations for next month)

Use Indian Rupee amounts (₹). Be thorough but concise."""

    client = _claude_client()
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=MONTHLY_MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    content = message.content[0].text

    digest = _persist_digest(db, restaurant_id, "monthly", month_start, month_end, content)
    logger.info(
        "Monthly digest generated: restaurant_id=%d month=%s digest_id=%d",
        restaurant_id,
        month_start,
        digest.id,
    )
    return digest
