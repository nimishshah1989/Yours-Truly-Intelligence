"""Weekly brief generator — Monday 8am intelligence synthesis.

Generates the most comprehensive message of the week. Under 500 words.
8 sections as defined in the PRD:
  1. Last week's performance vs week before + same week last year
  2. Top 3 wins of the week
  3. Top 3 things to improve
  4. What's coming this week (Priya's 7-day forward calendar)
  5. One Chef suggestion (if available)
  6. Unacted-on findings from the past week
  7. Customer pulse (Sara's segment summary)
  8. One question / conversation hook

Uses data from: DailySummary, AgentFinding, RestaurantProfile.
"""

import logging
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from intelligence.synthesis.voice import (
    MAX_WHATSAPP_CHARS,
    bold,
    check_brief_voice,
    italic,
)

logger = logging.getLogger("ytip.synthesis.weekly_brief")


def _format_currency(paisa: int) -> str:
    """Format paisa to Indian rupee string."""
    try:
        from services.whatsapp_service import format_currency
        return format_currency(paisa)
    except ImportError:
        rupees = paisa / 100
        if rupees >= 100_000:
            return f"₹{rupees / 100_000:.2f}L"
        return f"₹{rupees:,.0f}"


def _format_pct(value: float) -> str:
    """Format percentage with sign."""
    try:
        from services.whatsapp_service import format_pct
        return format_pct(value)
    except ImportError:
        sign = "+" if value > 0 else ""
        return f"{sign}{value:.1f}%"


class WeeklyBriefGenerator:
    """Generates the Monday 8am weekly intelligence brief."""

    def __init__(self, restaurant_id: int, db_session: Session,
                 readonly_db: Session = None):
        self.restaurant_id = restaurant_id
        self.db = db_session
        self.rodb = readonly_db or db_session
        self.profile = self._load_profile()

    def _load_profile(self):
        """Load restaurant profile."""
        try:
            from intelligence.models import RestaurantProfile
            return (
                self.rodb.query(RestaurantProfile)
                .filter_by(restaurant_id=self.restaurant_id)
                .first()
            )
        except Exception as e:
            logger.debug("Profile load failed: %s", e)
            return None

    def generate(self, week_end: Optional[date] = None) -> dict:
        """Generate the weekly brief.

        Args:
            week_end: Last day of the reporting week (default: yesterday).

        Returns:
            {
                "whatsapp_message": str,
                "sections": list[dict],
                "word_count": int,
                "char_count": int,
            }
        """
        if week_end is None:
            week_end = date.today() - timedelta(days=1)

        week_start = week_end - timedelta(days=6)
        prev_week_start = week_start - timedelta(days=7)
        prev_week_end = week_start - timedelta(days=1)

        # Gather data
        this_week = self._get_week_metrics(week_start, week_end)
        last_week = self._get_week_metrics(prev_week_start, prev_week_end)
        findings = self._get_week_findings(week_start, week_end)
        unacted = self._get_unacted_findings(week_start, week_end)
        upcoming = self._get_upcoming_events()

        # Build sections
        sections = []

        # Header
        date_range = f"{week_start.strftime('%d %b')} — {week_end.strftime('%d %b')}"
        header = f"Your week at a glance: {date_range}"

        # 1. Performance summary
        perf = self._section_performance(this_week, last_week, date_range)
        sections.append(perf)

        # 2. Top 3 wins
        wins = self._section_wins(findings, this_week)
        if wins:
            sections.append(wins)

        # 3. Top 3 improvements
        improvements = self._section_improvements(findings)
        if improvements:
            sections.append(improvements)

        # 4. What's coming this week
        calendar = self._section_calendar(upcoming)
        if calendar:
            sections.append(calendar)

        # 5. Chef suggestion (if available)
        chef_note = self._section_chef(findings)
        if chef_note:
            sections.append(chef_note)

        # 6. Unacted findings
        if unacted:
            sections.append(self._section_unacted(unacted))

        # 7. Customer pulse
        customer_pulse = self._section_customers(findings)
        if customer_pulse:
            sections.append(customer_pulse)

        # 8. Conversation hook
        sections.append(self._section_hook())

        # Compose message
        section_texts = []
        for s in sections:
            emoji = s.get("emoji", "")
            title = s.get("title", "")
            body = s.get("body", "")
            if title:
                section_texts.append(f"{emoji} {bold(title)}\n{body}")
            else:
                section_texts.append(body)

        message = bold(header) + "\n\n" + "\n\n".join(section_texts)

        # Voice check
        violations = check_brief_voice(message)
        if violations:
            logger.warning("Brief voice violations: %s", violations)

        # Enforce limits
        if len(message) > MAX_WHATSAPP_CHARS:
            message = message[:MAX_WHATSAPP_CHARS - 5] + "\n..."

        return {
            "whatsapp_message": message,
            "sections": sections,
            "word_count": len(message.split()),
            "char_count": len(message),
        }

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def _section_performance(self, this_week: dict, last_week: dict,
                              date_range: str) -> dict:
        """Section 1: Performance vs previous week."""
        rev = this_week.get("revenue", 0)
        prev_rev = last_week.get("revenue", 0)
        orders = this_week.get("orders", 0)
        prev_orders = last_week.get("orders", 0)
        aov = this_week.get("avg_order_value", 0)

        lines = [f"Revenue: {_format_currency(rev)}"]

        if prev_rev > 0:
            pct = ((rev - prev_rev) / prev_rev) * 100
            lines[0] += f" ({_format_pct(pct)} vs prior week)"

        lines.append(f"Orders: {orders}")
        if prev_orders > 0:
            ord_pct = ((orders - prev_orders) / prev_orders) * 100
            lines[-1] += f" ({_format_pct(ord_pct)})"

        lines.append(f"Avg ticket: {_format_currency(aov)}")

        # Best day
        best_day = this_week.get("best_day")
        if best_day:
            lines.append(
                f"Best day: {best_day['day_name']} "
                f"({_format_currency(best_day['revenue'])})"
            )

        return {
            "emoji": "📊",
            "title": "Last Week",
            "body": "\n".join(lines),
        }

    def _section_wins(self, findings: list, this_week: dict) -> Optional[dict]:
        """Section 2: Top 3 wins (positive findings or achievements)."""
        wins = []

        # Look for positive findings
        for f in findings:
            if isinstance(f, dict):
                impact = f.get("optimization_impact", "")
                text = f.get("finding_text", "")
            else:
                impact = getattr(f, "optimization_impact", "")
                text = getattr(f, "finding_text", "")

            if impact in ("revenue_increase", "opportunity"):
                wins.append(text)

        # Add top items as wins if we don't have enough
        top_items = this_week.get("top_items", [])
        if len(wins) < 3 and top_items:
            for item in top_items[:3 - len(wins)]:
                wins.append(
                    f"{item['name']} was your top performer "
                    f"({item.get('qty', '?')} orders)"
                )

        if not wins:
            return None

        lines = [f"• {w}" for w in wins[:3]]
        return {
            "emoji": "🏆",
            "title": "Wins",
            "body": "\n".join(lines),
        }

    def _section_improvements(self, findings: list) -> Optional[dict]:
        """Section 3: Top 3 things to improve."""
        improvements = []

        for f in findings:
            if isinstance(f, dict):
                impact = f.get("optimization_impact", "")
                action = f.get("action_text", "")
            else:
                impact = getattr(f, "optimization_impact", "")
                action = getattr(f, "action_text", "")

            if isinstance(impact, str):
                is_risk = impact in ("risk_mitigation", "margin_improvement")
            else:
                is_risk = impact in ("risk_mitigation", "margin_improvement")

            if is_risk and action:
                improvements.append(action)

        if not improvements:
            return None

        lines = [f"• {a}" for a in improvements[:3]]
        return {
            "emoji": "📋",
            "title": "To Improve",
            "body": "\n".join(lines),
        }

    def _section_calendar(self, upcoming: list) -> Optional[dict]:
        """Section 4: What's coming this week (from Priya/cultural events)."""
        if not upcoming:
            return None

        lines = []
        for event in upcoming[:3]:
            name = event.get("event_name", "Event")
            event_date = event.get("event_date", "")
            action = event.get("action", "")

            if isinstance(event_date, date):
                day_str = event_date.strftime("%A, %d %b")
            else:
                day_str = str(event_date)

            line = f"• {name} ({day_str})"
            if action:
                line += f" — {action}"
            lines.append(line)

        return {
            "emoji": "📅",
            "title": "Coming This Week",
            "body": "\n".join(lines),
        }

    def _section_chef(self, findings: list) -> Optional[dict]:
        """Section 5: One Chef suggestion (if available)."""
        for f in findings:
            if isinstance(f, dict):
                agent = f.get("agent_name", "")
                text = f.get("finding_text", "")
                action = f.get("action_text", "")
            else:
                agent = getattr(f, "agent_name", "")
                text = getattr(f, "finding_text", "")
                action = getattr(f, "action_text", "")

            if agent == "chef":
                return {
                    "emoji": "👨‍🍳",
                    "title": "Menu Idea",
                    "body": f"{text}\n{action}" if action else text,
                }

        return None

    def _section_unacted(self, unacted: list) -> dict:
        """Section 6: Unacted findings from the past week."""
        lines = []
        for f in unacted[:3]:
            if isinstance(f, dict):
                text = f.get("action_text", f.get("finding_text", ""))
            else:
                text = getattr(f, "action_text", getattr(f, "finding_text", ""))
            lines.append(f"• {text}")

        return {
            "emoji": "⏳",
            "title": "Still Pending",
            "body": "\n".join(lines),
        }

    def _section_customers(self, findings: list) -> Optional[dict]:
        """Section 7: Customer pulse from Sara's findings."""
        for f in findings:
            if isinstance(f, dict):
                agent = f.get("agent_name", "")
                text = f.get("finding_text", "")
            else:
                agent = getattr(f, "agent_name", "")
                text = getattr(f, "finding_text", "")

            if agent == "sara":
                return {
                    "emoji": "👥",
                    "title": "Customer Pulse",
                    "body": text,
                }

        return None

    def _section_hook(self) -> dict:
        """Section 8: Conversation hook."""
        return {
            "emoji": "",
            "title": "",
            "body": italic(
                "Reply with any question about last week — "
                "or send a voice note."
            ),
        }

    # ------------------------------------------------------------------
    # Data queries
    # ------------------------------------------------------------------

    def _get_week_metrics(self, start: date, end: date) -> dict:
        """Get aggregated metrics for a week."""
        try:
            result = self.rodb.execute(
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
                {"rid": self.restaurant_id, "start": start, "end": end},
            ).fetchone()

            metrics = {
                "orders": int(result[0]) if result else 0,
                "revenue": int(result[1]) if result else 0,
                "avg_order_value": int(result[2]) if result else 0,
            }

            # Top items
            items = self.rodb.execute(
                text("""
                    SELECT oi.item_name, SUM(oi.quantity) AS qty,
                           SUM(oi.total_price) AS revenue
                    FROM order_items oi
                    JOIN orders o ON o.id = oi.order_id
                    WHERE oi.restaurant_id = :rid
                      AND DATE(o.ordered_at) BETWEEN :start AND :end
                      AND o.is_cancelled = false
                      AND o.status = 'completed'
                    GROUP BY oi.item_name
                    ORDER BY revenue DESC
                    LIMIT 5
                """),
                {"rid": self.restaurant_id, "start": start, "end": end},
            ).fetchall()

            metrics["top_items"] = [
                {"name": r[0], "qty": int(r[1]), "revenue": int(r[2])}
                for r in items
            ]

            # Best day
            days = self.rodb.execute(
                text("""
                    SELECT DATE(ordered_at) AS day,
                           COUNT(*) AS orders,
                           SUM(total_amount) AS revenue
                    FROM orders
                    WHERE restaurant_id = :rid
                      AND DATE(ordered_at) BETWEEN :start AND :end
                      AND is_cancelled = false
                      AND status = 'completed'
                    GROUP BY DATE(ordered_at)
                    ORDER BY revenue DESC
                    LIMIT 1
                """),
                {"rid": self.restaurant_id, "start": start, "end": end},
            ).fetchone()

            if days:
                dow_names = ["Monday", "Tuesday", "Wednesday", "Thursday",
                             "Friday", "Saturday", "Sunday"]
                metrics["best_day"] = {
                    "date": days[0],
                    "day_name": dow_names[days[0].weekday()],
                    "orders": int(days[1]),
                    "revenue": int(days[2]),
                }

            return metrics
        except Exception as e:
            logger.warning("Week metrics query failed: %s", e)
            return {"orders": 0, "revenue": 0, "avg_order_value": 0}

    def _get_week_findings(self, start: date, end: date) -> list:
        """Get all approved findings for the week."""
        try:
            from intelligence.models import AgentFinding

            return (
                self.rodb.query(AgentFinding)
                .filter(
                    AgentFinding.restaurant_id == self.restaurant_id,
                    AgentFinding.status == "approved",
                    AgentFinding.created_at >= start,
                    AgentFinding.created_at <= end + timedelta(days=1),
                )
                .order_by(AgentFinding.created_at.desc())
                .all()
            )
        except Exception as e:
            logger.debug("Week findings query failed: %s", e)
            return []

    def _get_unacted_findings(self, start: date, end: date) -> list:
        """Get findings that were sent but not acted on."""
        try:
            from intelligence.models import AgentFinding

            return (
                self.rodb.query(AgentFinding)
                .filter(
                    AgentFinding.restaurant_id == self.restaurant_id,
                    AgentFinding.status == "approved",
                    AgentFinding.sent_at.isnot(None),
                    AgentFinding.owner_acted.is_(None),
                    AgentFinding.created_at >= start,
                    AgentFinding.created_at <= end + timedelta(days=1),
                )
                .order_by(AgentFinding.created_at.desc())
                .limit(3)
                .all()
            )
        except Exception as e:
            logger.debug("Unacted findings query failed: %s", e)
            return []

    def _get_upcoming_events(self) -> list:
        """Get upcoming cultural events for the next 7 days."""
        try:
            from intelligence.models import CulturalEvent

            today = date.today()
            next_week = today + timedelta(days=7)

            events = (
                self.rodb.query(CulturalEvent)
                .filter(
                    CulturalEvent.is_active.is_(True),
                    CulturalEvent.month == today.month,
                )
                .all()
            )

            upcoming = []
            for e in events:
                if e.day_of_month and today.day <= e.day_of_month <= next_week.day:
                    event_date = date(today.year, today.month, e.day_of_month)
                    upcoming.append({
                        "event_name": e.event_name,
                        "event_date": event_date,
                        "action": e.owner_action_template or "",
                    })

            return upcoming
        except Exception as e:
            logger.debug("Upcoming events query failed: %s", e)
            return []
