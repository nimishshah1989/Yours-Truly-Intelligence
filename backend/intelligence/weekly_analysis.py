"""Weekly Claude batch analysis — runs Sunday 3 AM IST.

Assembles the week's intelligence findings + daily summaries,
sends to Claude for creative cross-signal analysis,
writes observations to insights_journal.

Cost: ~₹10/week (single Claude call per restaurant).

Usage:
    python -m intelligence.weekly_analysis              # this week
    python -m intelligence.weekly_analysis --backfill   # last 12 weeks
"""

import logging
from datetime import date, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from config import settings
from models import (
    DailySummary,
    IntelligenceFinding,
    InsightsJournal,
    Restaurant,
)

logger = logging.getLogger("ytip.intelligence.weekly")


def _build_analysis_prompt(
    findings: List[IntelligenceFinding],
    summaries: List[DailySummary],
    week_start: date,
) -> str:
    """Build the prompt for Claude's weekly analysis."""
    week_end = week_start + timedelta(days=6)

    findings_text = "No automated findings this week."
    if findings:
        lines = []
        for f in findings:
            impact = f" (est. impact: ₹{f.rupee_impact // 100:,}/yr)" if f.rupee_impact else ""
            lines.append(f"- [{f.severity.upper()}] {f.category}: {f.title}{impact}")
        findings_text = "\n".join(lines)

    summary_text = "No daily summaries available."
    if summaries:
        lines = []
        for s in summaries:
            rev = s.total_revenue // 100 if s.total_revenue else 0
            orders = s.total_orders or 0
            lines.append(f"- {s.summary_date}: ₹{rev:,} revenue, {orders} orders")
        summary_text = "\n".join(lines)

    return f"""You are the Chief of Staff intelligence engine for YoursTruly Coffee Roaster, a premium cafe in Kolkata.

Analyze this week's data ({week_start} to {week_end}) and provide ONE concise observation that connects patterns across multiple signals. Focus on what the owner should DO, not just what happened.

AUTOMATED FINDINGS THIS WEEK:
{findings_text}

DAILY PERFORMANCE:
{summary_text}

Rules:
1. Be specific — use actual numbers and item names
2. Connect dots across findings (e.g., rising food cost + declining item = recipe issue)
3. End with ONE clear action the owner should take this week
4. Keep it under 200 words
5. Write as if briefing a busy restaurant owner — direct, no fluff
6. All amounts in ₹ (Indian rupees), use lakh format for large numbers

Respond with:
OBSERVATION: [your analysis]
ACTION: [one specific action]
CONFIDENCE: [high/medium/low]"""


def _extract_action(response_text: str) -> Optional[str]:
    """Extract the ACTION line from Claude's response."""
    for line in response_text.split("\n"):
        line = line.strip()
        if line.upper().startswith("ACTION:"):
            return line[7:].strip()
    return None


def _extract_confidence(response_text: str) -> str:
    """Extract confidence level from response."""
    for line in response_text.split("\n"):
        line = line.strip()
        if line.upper().startswith("CONFIDENCE:"):
            val = line[11:].strip().lower()
            if val in ("high", "medium", "low"):
                return val
    return "medium"


def run_weekly_analysis(
    db: Session, restaurant_id: int, week_start: date
) -> Optional[InsightsJournal]:
    """Assemble week's findings, call Claude, write to insights_journal."""
    week_end = week_start + timedelta(days=6)

    # Check if already analyzed
    existing = (
        db.query(InsightsJournal)
        .filter(
            InsightsJournal.restaurant_id == restaurant_id,
            InsightsJournal.week_start == week_start,
        )
        .first()
    )
    if existing:
        logger.info("Weekly analysis already exists for %s — skipping", week_start)
        return existing

    # Fetch this week's findings
    findings = (
        db.query(IntelligenceFinding)
        .filter(
            IntelligenceFinding.restaurant_id == restaurant_id,
            IntelligenceFinding.finding_date >= week_start,
            IntelligenceFinding.finding_date <= week_end,
        )
        .order_by(IntelligenceFinding.finding_date)
        .all()
    )

    # Fetch daily summaries
    summaries = (
        db.query(DailySummary)
        .filter(
            DailySummary.restaurant_id == restaurant_id,
            DailySummary.summary_date >= week_start,
            DailySummary.summary_date <= week_end,
        )
        .order_by(DailySummary.summary_date)
        .all()
    )

    if not findings and not summaries:
        logger.info("No data for week %s — skipping analysis", week_start)
        return None

    # Build prompt and call Claude
    prompt = _build_analysis_prompt(findings, summaries, week_start)

    if not settings.anthropic_api_key:
        logger.warning("No ANTHROPIC_API_KEY set — skipping weekly analysis")
        return None

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = response.content[0].text
    except Exception as exc:
        logger.error("Claude API call failed: %s", exc)
        return None

    # Write to insights_journal
    journal = InsightsJournal(
        restaurant_id=restaurant_id,
        week_start=week_start,
        observation_text=response_text,
        connected_finding_ids=[f.id for f in findings],
        suggested_action=_extract_action(response_text),
        confidence=_extract_confidence(response_text),
        owner_relevance_score=7 if findings else 5,
    )
    db.add(journal)
    db.commit()

    logger.info(
        "Weekly analysis written: week=%s findings=%d",
        week_start, len(findings),
    )
    return journal


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")

    from database import SessionLocal

    db = SessionLocal()
    rest = db.query(Restaurant).filter(Restaurant.is_active == True).first()
    if not rest:
        print("No active restaurant found")
        sys.exit(1)

    if "--backfill" in sys.argv:
        for week in range(12, 0, -1):
            ws = date.today() - timedelta(weeks=week)
            # Align to Monday
            ws = ws - timedelta(days=ws.weekday())
            result = run_weekly_analysis(db, rest.id, ws)
            status = "written" if result else "skipped"
            print(f"  Week of {ws}: {status}")
    else:
        # This week (Monday)
        today = date.today()
        ws = today - timedelta(days=today.weekday())
        result = run_weekly_analysis(db, rest.id, ws)
        if result:
            print(f"Analysis written for week of {ws}")
            print(result.observation_text[:500])
        else:
            print("No analysis generated (no data or already exists)")

    db.close()
