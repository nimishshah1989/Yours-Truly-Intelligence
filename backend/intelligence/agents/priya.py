"""Priya — Cultural & Calendar Intelligence Agent.

14-day forward calendar scan. Filters every cultural event through this
restaurant's actual catchment demographics and city. Salary week detection
using week-of-month + historical spending patterns.

Rules:
- Reads cultural_events table + restaurant_profiles.catchment_demographics
- calculate_catchment_relevance() returns 0-100. Only events > 20 become findings
- Max 2 findings per daily run, 3 for weekly deep scan
- Never applies pan-Indian assumptions to a specific catchment
- Fails silently — returns [] on error
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional

from intelligence.agents.base_agent import (
    BaseAgent,
    Finding,
    ImpactSize,
    OptimizationImpact,
    Urgency,
)

logger = logging.getLogger("ytip.agents.priya")

# Thresholds
RELEVANCE_MIN = 20  # Below this, event is not worth a finding
RELEVANCE_HIGH = 50
FORWARD_SCAN_DAYS = 14
MAX_FINDINGS_DAILY = 2
MAX_FINDINGS_WEEKLY = 3

# Salary cycle week boundaries
SALARY_WEEKS = {
    1: (1, 7),
    2: (8, 15),
    3: (16, 23),
    4: (24, 31),
}

# Salary week behavior scores (from CULTURAL_MODEL.md)
SALARY_WEEK_SCORES = {
    1: {"label": "post-salary spending", "avg_spend_modifier": +2.5},
    2: {"label": "slight above normal", "avg_spend_modifier": +0.5},
    3: {"label": "slight below normal", "avg_spend_modifier": -0.3},
    4: {"label": "pre-salary tightening", "avg_spend_modifier": -1.5},
}


def _get_week_of_month(d: date = None) -> int:
    """Return 1-4 based on day of month."""
    if d is None:
        d = date.today()
    day = d.day
    for week_num, (start, end) in SALARY_WEEKS.items():
        if start <= day <= end:
            return week_num
    return 4


def calculate_catchment_relevance(event, profile) -> int:
    """0-100 score. Only events > 20 become findings.

    relevance = sum(community_share * city_weight * max_impact_normalized * 100)
    Capped at 100.
    """
    catchment = getattr(profile, "catchment_demographics", None) or {}
    city = (getattr(profile, "city", None) or "").lower()
    city_weights = getattr(event, "city_weights", None) or {}
    city_weight = city_weights.get(city, 0.0)
    if isinstance(city_weight, str):
        city_weight = float(city_weight)

    primary_communities = getattr(event, "primary_communities", None) or []
    behavior_impacts = getattr(event, "behavior_impacts", None) or {}

    if not behavior_impacts:
        return 0

    max_impact = max(abs(float(v)) for v in behavior_impacts.values()) / 3.0

    relevance = 0.0
    for community in primary_communities:
        community_share = catchment.get(community, 0.0)
        if isinstance(community_share, str):
            community_share = float(community_share)
        relevance += community_share * city_weight * max_impact * 100

    return min(100, int(relevance))


def _format_rupees(paisa: int) -> str:
    """Format paisa as Indian rupee string."""
    rupees = paisa / 100
    if rupees >= 100000:
        return f"₹{rupees / 100000:,.2f}L"
    elif rupees >= 1000:
        return f"₹{rupees:,.0f}"
    return f"₹{rupees:.0f}"


class PriyaAgent(BaseAgent):
    """Cultural & Calendar Intelligence agent."""

    agent_name = "priya"
    category = "cultural"

    def run(self, weekly: bool = False) -> list[Finding]:
        """Run cultural calendar scan. Return findings for upcoming events."""
        findings: list[Finding] = []
        max_findings = MAX_FINDINGS_WEEKLY if weekly else MAX_FINDINGS_DAILY

        try:
            # 1. Cultural event scan (14-day forward)
            event_findings = self._scan_cultural_events()
            findings.extend(event_findings)

            # 2. Salary week detection
            salary_finding = self._analyze_salary_week()
            if salary_finding:
                findings.append(salary_finding)

        except Exception as e:
            logger.error("Priya run failed entirely: %s", e)
            return []

        # Sort by relevance/confidence, cap at max
        findings.sort(key=lambda f: f.confidence_score, reverse=True)
        return findings[:max_findings]

    # ------------------------------------------------------------------
    # Cultural event scan
    # ------------------------------------------------------------------

    def _scan_cultural_events(self) -> list[Finding]:
        """Scan cultural_events table for events in the next 14 days."""
        findings = []
        try:
            from intelligence.models import CulturalEvent

            events = (
                self.rodb.query(CulturalEvent)
                .filter(CulturalEvent.is_active.is_(True))
                .all()
            )

            if not events or not self.profile:
                return []

            today = date.today()

            for event in events:
                days_until = self._days_until_event(event, today)
                outside_window = (
                    days_until is None
                    or days_until < 0
                    or days_until > FORWARD_SCAN_DAYS
                )
                if outside_window:
                    continue

                relevance = calculate_catchment_relevance(event, self.profile)

                # Only events > 20 relevance become findings
                if relevance <= RELEVANCE_MIN:
                    continue

                finding = self._build_event_finding(event, relevance, days_until)
                if finding:
                    findings.append(finding)

        except Exception as e:
            logger.warning("Cultural event scan failed: %s", e)

        return findings

    def _days_until_event(self, event, today: date) -> Optional[int]:
        """Calculate days until event. Handles month/day stored in event."""
        try:
            month = event.month
            day_of_month = event.day_of_month

            if month is None:
                return None

            # Build target date for this year
            year = today.year
            if day_of_month is None:
                day_of_month = 1

            try:
                event_date = date(year, month, day_of_month)
            except ValueError:
                # Handle Feb 29 etc
                event_date = date(year, month, min(day_of_month, 28))

            # If event already passed this year, check next year
            if event_date < today:
                try:
                    event_date = date(year + 1, month, day_of_month)
                except ValueError:
                    event_date = date(year + 1, month, min(day_of_month, 28))

            return (event_date - today).days
        except Exception:
            return None

    def _build_event_finding(self, event, relevance: int,
                             days_until: int) -> Optional[Finding]:
        """Build a Finding for a cultural event."""
        try:
            city = (getattr(self.profile, "city", None) or "unknown").capitalize()
            catchment = getattr(self.profile, "catchment_demographics", None) or {}
            behavior_impacts = getattr(event, "behavior_impacts", None) or {}

            # Determine urgency based on relevance and timing
            urgency = self._determine_event_urgency(relevance, days_until)

            # Build behavior prediction text
            behavior_text = self._format_behavior_predictions(
                behavior_impacts, relevance
            )

            # Build catchment context
            catchment_text = self._format_catchment_context(
                event, catchment, city, relevance
            )

            # Finding text
            event_name = event.event_name or event.event_key
            finding_text = (
                f"{event_name} starts in {days_until} days. "
            )

            if relevance >= RELEVANCE_HIGH:
                finding_text += (
                    f"This is a major event for your café "
                    f"(relevance: {relevance}/100). "
                )
            elif relevance > RELEVANCE_MIN:
                finding_text += (
                    f"Minimal impact for your café "
                    f"(relevance: {relevance}/100). "
                )

            finding_text += catchment_text

            if behavior_text:
                finding_text += f" {behavior_text}"

            # Action text
            action_text = self._build_action_text(
                event, relevance, days_until
            )

            # Impact estimate for high-relevance events
            impact_paisa = None
            if relevance >= RELEVANCE_HIGH:
                impact_paisa = self._estimate_event_impact(
                    event, relevance
                )

            # Confidence: higher relevance = higher confidence
            confidence = 60 + min(30, relevance // 3)

            return Finding(
                agent_name=self.agent_name,
                restaurant_id=self.restaurant_id,
                category=self.category,
                urgency=urgency,
                optimization_impact=OptimizationImpact.OPPORTUNITY,
                finding_text=finding_text,
                action_text=action_text,
                evidence_data={
                    "event_key": event.event_key,
                    "event_name": event.event_name,
                    "days_until": days_until,
                    "relevance_score": relevance,
                    "city": city,
                    "catchment_demographics": catchment,
                    "behavior_impacts": behavior_impacts,
                    "data_points_count": max(3, len(behavior_impacts)),
                },
                confidence_score=confidence,
                action_deadline=date.today() + timedelta(days=max(1, days_until - 2)),
                estimated_impact_size=(
                    ImpactSize.HIGH if relevance >= RELEVANCE_HIGH
                    else ImpactSize.MEDIUM if relevance > 40
                    else ImpactSize.LOW
                ),
                estimated_impact_paisa=impact_paisa,
            )
        except Exception as e:
            logger.warning("Failed to build finding for event %s: %s",
                           getattr(event, "event_key", "?"), e)
            return None

    def _determine_event_urgency(self, relevance: int,
                                 days_until: int) -> Urgency:
        """Determine urgency from relevance and timing.

        High relevance (>60) + soon (<7 days) = this_week or immediate
        Low relevance (<40) = always strategic
        """
        if relevance < 40:
            return Urgency.STRATEGIC

        if days_until <= 3 and relevance >= RELEVANCE_HIGH:
            return Urgency.IMMEDIATE
        elif days_until <= 7 and relevance >= RELEVANCE_HIGH:
            return Urgency.THIS_WEEK
        elif days_until <= 7 and relevance >= 40:
            return Urgency.THIS_WEEK
        elif days_until <= 14 and relevance >= RELEVANCE_HIGH:
            return Urgency.THIS_WEEK
        else:
            return Urgency.STRATEGIC

    def _format_behavior_predictions(self, behavior_impacts: dict,
                                     relevance: int) -> str:
        """Format behavior impacts as prediction text with percentages."""
        if not behavior_impacts:
            return ""

        parts = []
        scale = relevance / 100.0

        for dimension, score in sorted(
            behavior_impacts.items(),
            key=lambda x: abs(float(x[1])),
            reverse=True,
        )[:3]:
            score_f = float(score)
            pct = int(abs(score_f) * scale * 15)
            if pct < 5:
                continue
            sign = "+" if score_f > 0 else "-"
            label = dimension.replace("_", " ")
            parts.append(f"{sign}{pct}% {label}")

        if not parts:
            return ""

        return "Expect: " + ", ".join(parts) + "."

    def _format_catchment_context(self, event, catchment: dict,
                                  city: str, relevance: int) -> str:
        """Explain WHY this relevance score, referencing actual catchment."""
        primary = getattr(event, "primary_communities", None) or []

        # Find the most relevant community in catchment
        relevant_parts = []
        for comm in primary:
            share = catchment.get(comm, 0.0)
            if isinstance(share, str):
                share = float(share)
            if share > 0.01:
                label = comm.replace("_", " ").title()
                relevant_parts.append(f"{int(share * 100)}% {label}")

        # Find communities NOT in this catchment
        irrelevant = [
            c.replace("_", " ").title() for c in primary
            if catchment.get(c, 0.0) <= 0.01
        ]

        text = f"Your {city} catchment is "
        if relevant_parts:
            text += ", ".join(relevant_parts) + "."
        elif irrelevant:
            text += (
                f"not significantly "
                f"{', '.join(irrelevant).lower()} — "
                f"this event has limited relevance."
            )
        else:
            text += "mixed."

        return text

    def _build_action_text(self, event, relevance: int,
                           days_until: int) -> str:
        """Build action text based on event template and relevance."""
        template = getattr(event, "owner_action_template", None)
        surge_dishes = getattr(event, "surge_dishes", None) or []

        if relevance < 40:
            # Low relevance — minimal or no action
            action = (
                "No action needed. "
            )
            if surge_dishes:
                action += (
                    "If anything, add one related option to the "
                    "specials board as a gesture for the small "
                    "segment who observes."
                )
            else:
                action += (
                    "Monitor for any subtle shifts in ordering patterns."
                )
            return action

        # High relevance — specific actions
        action_parts = []

        if template:
            action_parts.append(template)

        if days_until <= 3:
            action_parts.append(
                f"Only {days_until} days left — act today."
            )
        elif days_until <= 7:
            action_parts.append(
                f"{days_until} days lead time remaining."
            )
        else:
            action_parts.append(
                f"You have {days_until} days to prepare."
            )

        if surge_dishes:
            top_surge = surge_dishes[:5]
            action_parts.append(
                f"Expected surge items: {', '.join(top_surge)}."
            )

        return " ".join(action_parts)

    def _estimate_event_impact(self, event, relevance: int) -> Optional[int]:
        """Rough ₹ impact estimate based on relevance and baseline revenue."""
        try:
            baseline = self._get_baseline("revenue", lookback_weeks=8)
            if baseline["data_points"] < 7:
                return None

            daily_avg = baseline["mean"]
            if daily_avg <= 0:
                return None

            duration = getattr(event, "duration_days", 1) or 1
            behavior_impacts = getattr(event, "behavior_impacts", None) or {}

            if not behavior_impacts:
                return None

            max_impact = max(float(v) for v in behavior_impacts.values())
            scale = relevance / 100.0
            uplift_fraction = max_impact / 3.0 * scale * 0.3

            impact = int(daily_avg * duration * uplift_fraction)
            return impact if impact > 0 else None
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Salary week analysis
    # ------------------------------------------------------------------

    def _analyze_salary_week(self) -> Optional[Finding]:
        """Detect salary week and compare historical spending patterns."""
        try:
            if not self.profile:
                return None

            today = date.today()
            week = _get_week_of_month(today)
            week_info = SALARY_WEEK_SCORES.get(week)
            if not week_info:
                return None

            # Only generate findings for week 1 (push premium) or
            # week 4 (push value)
            if week not in (1, 4):
                return None

            # Get historical week1 vs week4 spending patterns
            historical = self._get_salary_week_historical()
            if not historical:
                return None

            w1_avg = historical.get("week_1_avg_ticket", 0)
            w4_avg = historical.get("week_4_avg_ticket", 0)

            if w1_avg <= 0 or w4_avg <= 0:
                return None

            spend_diff_pct = int((w1_avg - w4_avg) / w4_avg * 100) if w4_avg > 0 else 0

            if abs(spend_diff_pct) < 10:
                return None  # Not enough salary cycle signal

            # Get premium item patterns
            premium_items = historical.get("premium_item_shifts", {})
            premium_text = self._format_premium_shifts(premium_items, week)

            if week == 1:
                finding_text = (
                    f"Salary week (April {SALARY_WEEKS[1][0]}-{SALARY_WEEKS[1][1]}). "
                    f"Your customers spend {spend_diff_pct}% more per order in "
                    f"week 1 vs week 4 "
                    f"({_format_rupees(w1_avg)} vs {_format_rupees(w4_avg)}). "
                )
                if premium_text:
                    finding_text += premium_text
                finding_text += (
                    "Your corporate crowd treats themselves when the salary hits."
                )

                action_text = (
                    "This week, push your premium items hard. "
                    "Your customers are more likely to trade up right now. "
                    "Put a 'Barista's Pick' table card featuring your "
                    "highest-margin items this week."
                )
                urgency = Urgency.IMMEDIATE

            else:  # week 4
                finding_text = (
                    f"Pre-salary week ({today.strftime('%B')} "
                    f"{SALARY_WEEKS[4][0]}-{SALARY_WEEKS[4][1]}). "
                    f"Customers tighten spending — average ticket drops "
                    f"{abs(spend_diff_pct)}% vs week 1 "
                    f"({_format_rupees(w4_avg)} vs {_format_rupees(w1_avg)}). "
                )
                finding_text += (
                    "Value-seeking behavior peaks this week."
                )

                action_text = (
                    "Feature value combos and lunch specials this week. "
                    "Bundle a coffee + pastry at a slight discount to "
                    "maintain visit frequency even as per-order spend drops."
                )
                urgency = Urgency.THIS_WEEK

            return Finding(
                agent_name=self.agent_name,
                restaurant_id=self.restaurant_id,
                category=self.category,
                urgency=urgency,
                optimization_impact=OptimizationImpact.REVENUE_INCREASE,
                finding_text=finding_text,
                action_text=action_text,
                evidence_data={
                    "week_of_month": week,
                    "week_1_avg_ticket_paisa": w1_avg,
                    "week_4_avg_ticket_paisa": w4_avg,
                    "spend_diff_pct": spend_diff_pct,
                    "premium_item_shifts": premium_items,
                    "data_points_count": historical.get("data_points", 4),
                },
                confidence_score=75,
                action_deadline=today + timedelta(days=3),
                estimated_impact_size=ImpactSize.MEDIUM,
            )
        except Exception as e:
            logger.warning("Salary week analysis failed: %s", e)
            return None

    def _get_salary_week_historical(self) -> Optional[dict]:
        """Compare week 1 vs week 4 average ticket from daily_summaries."""
        try:
            from core.models import DailySummary

            cutoff = date.today() - timedelta(weeks=12)

            summaries = (
                self.rodb.query(DailySummary)
                .filter(
                    DailySummary.restaurant_id == self.restaurant_id,
                    DailySummary.summary_date >= cutoff,
                    DailySummary.summary_date < date.today(),
                )
                .all()
            )

            if not summaries or len(summaries) < 14:
                return None

            week1_tickets = []
            week4_tickets = []

            for s in summaries:
                d = s.summary_date
                if isinstance(d, datetime):
                    d = d.date()
                w = _get_week_of_month(d)
                aov = getattr(s, "avg_order_value", None) or 0
                if aov <= 0:
                    continue
                if w == 1:
                    week1_tickets.append(aov)
                elif w == 4:
                    week4_tickets.append(aov)

            if not week1_tickets or not week4_tickets:
                return None

            w1_avg = int(sum(week1_tickets) / len(week1_tickets))
            w4_avg = int(sum(week4_tickets) / len(week4_tickets))

            return {
                "week_1_avg_ticket": w1_avg,
                "week_4_avg_ticket": w4_avg,
                "data_points": len(week1_tickets) + len(week4_tickets),
                "premium_item_shifts": {},
            }
        except Exception as e:
            logger.debug("Salary week historical query failed: %s", e)
            return None

    def _format_premium_shifts(self, shifts: dict, week: int) -> str:
        """Format premium item share shifts for the finding text."""
        if not shifts:
            return ""

        parts = []
        for item, data in sorted(
            shifts.items(),
            key=lambda x: abs(x[1].get("w1_share", 0) - x[1].get("w4_share", 0)),
            reverse=True,
        )[:3]:
            w1 = data.get("w1_share", 0)
            w4 = data.get("w4_share", 0)
            if w1 > 0 and w4 > 0:
                parts.append(
                    f"{item} orders "
                    f"{'double' if w1 / w4 >= 1.8 else 'rise'} "
                    f"({int(w1 * 100)}% vs {int(w4 * 100)}% share)"
                )

        if not parts:
            return ""
        return ". ".join(parts) + ". "
