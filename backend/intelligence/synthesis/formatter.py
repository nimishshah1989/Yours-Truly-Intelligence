"""WhatsApp message formatter — converts QC-passed Findings to owner messages.

Architecture:
  Finding (from agent, post-QC) → format() → WhatsApp-ready text string

Every message follows: Opening → Evidence → Action → Impact → Hook (optional)
No agent names. No system internals. One specific action per message.
Under 225 words. Under 4096 chars.

Message batching: if multiple findings pass QC simultaneously:
  1. Rank by urgency + estimated ₹ impact
  2. Send highest-ranked first
  3. Queue rest for 4 hours or weekly brief
"""

import logging
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from intelligence.agents.base_agent import (
    Finding,
    OptimizationImpact,
    Urgency,
)
from intelligence.synthesis.voice import (
    MAX_FINDING_WORDS,
    MAX_WHATSAPP_CHARS,
    bold,
    check_voice,
    italic,
    sanitize_message,
)

logger = logging.getLogger("ytip.synthesis.formatter")


def _format_currency(paisa: int) -> str:
    """Format paisa to Indian rupee string."""
    try:
        from services.whatsapp_service import format_currency
        return format_currency(paisa)
    except ImportError:
        rupees = paisa / 100
        if rupees >= 10_000_000:
            return f"₹{rupees / 10_000_000:.2f} Cr"
        elif rupees >= 100_000:
            return f"₹{rupees / 100_000:.2f}L"
        else:
            return f"₹{rupees:,.0f}"


def _format_pct(value: float) -> str:
    """Format percentage with sign."""
    try:
        from services.whatsapp_service import format_pct
        return format_pct(value)
    except ImportError:
        sign = "+" if value > 0 else ""
        return f"{sign}{value:.1f}%"


class WhatsAppFormatter:
    """Formats QC-passed findings into WhatsApp messages."""

    def __init__(self, restaurant_id: int, db_session: Session = None):
        self.restaurant_id = restaurant_id
        self.db = db_session
        self.profile = self._load_profile()

    def _load_profile(self):
        """Load restaurant profile for identity-aware formatting."""
        if not self.db:
            return None
        try:
            from intelligence.models import RestaurantProfile
            return (
                self.db.query(RestaurantProfile)
                .filter_by(restaurant_id=self.restaurant_id)
                .first()
            )
        except Exception as e:
            logger.debug("Profile load failed: %s", e)
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def format(self, finding: Finding) -> str:
        """Convert a single Finding to a WhatsApp message string.

        Structure: Opening → Evidence → Action → Impact → Hook
        """
        parts = []

        # 1. Opening — one sentence, most important thing, no preamble
        opening = self._build_opening(finding)
        parts.append(opening)

        # 2. Evidence — 2-3 sentences with specific numbers
        evidence = self._build_evidence(finding)
        if evidence:
            parts.append(evidence)

        # 3. Action — one specific thing to do
        action = self._build_action(finding)
        parts.append(action)

        # 4. Impact — the rupee reason
        impact = self._build_impact(finding)
        if impact:
            parts.append(impact)

        # 5. Hook — optional conversation starter
        hook = self._build_hook(finding)
        if hook:
            parts.append(hook)

        message = "\n\n".join(parts)

        # Voice check and sanitize
        violations = check_voice(message)
        if violations:
            logger.warning("Voice violations in %s finding: %s",
                           finding.category, violations)
            message = sanitize_message(message)

        # Enforce limits
        message = self._enforce_limits(message)

        return message

    def format_batch(self, findings: list[Finding]) -> dict:
        """Format multiple findings with batching logic.

        Returns:
            {
                "immediate": str or None — send now (highest priority),
                "queued": list[dict] — send after 4h or in weekly brief,
                "queue_messages": list[str] — pre-formatted queued messages,
            }
        """
        if not findings:
            return {"immediate": None, "queued": [], "queue_messages": []}

        ranked = self._rank_findings(findings)

        immediate_finding = ranked[0]
        immediate_msg = self.format(immediate_finding)

        queued = []
        queue_messages = []
        for f in ranked[1:]:
            queued.append({
                "finding": f,
                "category": f.category,
                "urgency": (
                    f.urgency.value
                    if hasattr(f.urgency, "value")
                    else str(f.urgency)
                ),
                "impact_paisa": f.estimated_impact_paisa,
            })
            queue_messages.append(self.format(f))

        return {
            "immediate": immediate_msg,
            "queued": queued,
            "queue_messages": queue_messages,
        }

    # ------------------------------------------------------------------
    # Message building — each section
    # ------------------------------------------------------------------

    def _build_opening(self, finding: Finding) -> str:
        """One sentence stating the most important thing. No preamble."""
        # Use finding_text as base — it's already the core insight
        text = finding.finding_text

        # Make it punchy: strip weak openings
        for prefix in ["Analysis shows that ", "Data indicates that ",
                        "We found that ", "It appears that "]:
            if text.startswith(prefix):
                text = text[len(prefix):]
                text = text[0].upper() + text[1:]

        return text

    def _build_evidence(self, finding: Finding) -> Optional[str]:
        """2-3 sentences with specific numbers from evidence_data."""
        evidence = finding.evidence_data or {}
        parts = []

        # Extract key metrics based on category
        if finding.category == "revenue":
            parts.extend(self._evidence_revenue(evidence))
        elif finding.category == "menu":
            parts.extend(self._evidence_menu(evidence))
        elif finding.category == "stock":
            parts.extend(self._evidence_stock(evidence))
        elif finding.category == "customer":
            parts.extend(self._evidence_customer(evidence))
        elif finding.category == "cultural":
            parts.extend(self._evidence_cultural(evidence))
        else:
            parts.extend(self._evidence_generic(evidence))

        if not parts:
            return None

        return " ".join(parts[:3])  # Max 3 evidence sentences

    def _build_action(self, finding: Finding) -> str:
        """One specific action with deadline."""
        action = finding.action_text

        # Add deadline if present
        if finding.action_deadline:
            deadline_str = finding.action_deadline.strftime("%A, %d %b")
            day_str = finding.action_deadline.strftime("%d")
            if f"by {deadline_str}" not in action.lower() and day_str not in action:
                action = f"{action} — by {deadline_str}."

        return bold("Action:") + f" {action}"

    def _build_impact(self, finding: Finding) -> Optional[str]:
        """The rupee impact reason."""
        if not finding.estimated_impact_paisa:
            return None

        impact_str = _format_currency(finding.estimated_impact_paisa)

        impact_label = {
            OptimizationImpact.REVENUE_INCREASE: "potential additional revenue",
            OptimizationImpact.MARGIN_IMPROVEMENT: "margin improvement potential",
            OptimizationImpact.RISK_MITIGATION: "at risk",
            OptimizationImpact.OPPORTUNITY: "opportunity value",
        }
        label = impact_label.get(finding.optimization_impact, "estimated impact")

        return f"{impact_str} {label}."

    def _build_hook(self, finding: Finding) -> Optional[str]:
        """Optional conversation hook — only for non-immediate findings."""
        urgency = finding.urgency
        if hasattr(urgency, "value"):
            urgency = urgency.value

        if urgency == "immediate":
            return None  # Immediate findings don't need hooks

        hooks = {
            "revenue": "Reply if you want the full day-part breakdown.",
            "menu": "Reply if you want the full menu ranking.",
            "stock": "Reply if you want this week's full prep plan.",
            "customer": "Reply if you want the full customer segment view.",
            "cultural": "Reply if you want the full 14-day calendar.",
        }
        hook = hooks.get(finding.category)
        if hook:
            return italic(hook)
        return None

    # ------------------------------------------------------------------
    # Evidence builders per category
    # ------------------------------------------------------------------

    def _evidence_revenue(self, evidence: dict) -> list[str]:
        """Build revenue evidence sentences."""
        parts = []
        baseline_mean = evidence.get("baseline_mean")
        current_value = evidence.get("current_value")
        deviation_pct = evidence.get("deviation_pct")
        discount_rate = evidence.get("discount_rate")

        if baseline_mean and current_value:
            parts.append(
                f"Your 8-week average for this day is "
                f"{_format_currency(int(baseline_mean))}, "
                f"but yesterday came in at {_format_currency(int(current_value))}."
            )

        if deviation_pct:
            pct = deviation_pct * 100 if abs(deviation_pct) < 1 else deviation_pct
            parts.append(f"That's a {_format_pct(pct)} deviation from your baseline.")

        if discount_rate and evidence.get("discount_rate_baseline"):
            parts.append(
                f"Discount rate has crept to {discount_rate*100:.1f}% "
                f"from a baseline of {evidence['discount_rate_baseline']*100:.1f}%."
            )

        return parts

    def _evidence_menu(self, evidence: dict) -> list[str]:
        """Build menu evidence sentences."""
        parts = []

        item_name = evidence.get("item_name") or evidence.get("dish_name")
        margin_pct = (
            evidence.get("margin_pct")
            or evidence.get("contribution_margin_pct")
        )
        order_count = evidence.get("order_count") or evidence.get("orders_30d")
        revenue = evidence.get("revenue") or evidence.get("contribution_30d")
        order_rank = evidence.get("order_rank")

        if item_name and margin_pct:
            parts.append(
                f"{item_name} runs at {margin_pct:.0f}% contribution margin"
                f"{f' — your #{order_rank} by orders' if order_rank else ''}."
            )

        if revenue:
            parts.append(
                f"In the last 30 days it generated "
                f"{_format_currency(int(revenue))} in contribution."
            )

        if order_count and not order_rank:
            parts.append(f"It moved {order_count} units in the last 30 days.")

        # Dead SKU evidence
        if evidence.get("dead_sku_count"):
            parts.append(
                f"{evidence['dead_sku_count']} items on your menu had fewer "
                f"than 3 orders in 30 days."
            )

        return parts

    def _evidence_stock(self, evidence: dict) -> list[str]:
        """Build stock/waste evidence sentences."""
        parts = []

        waste_item = evidence.get("item_name") or evidence.get("waste_item")
        waste_pct = evidence.get("waste_pct")
        waste_cost = evidence.get("waste_cost_paisa")
        prep_qty = evidence.get("recommended_prep")
        historical_avg = evidence.get("historical_avg_sales")

        if waste_item and waste_pct:
            parts.append(
                f"You're prepping more {waste_item} than you sell — "
                f"{waste_pct:.0f}% is going to waste."
            )

        if waste_cost:
            parts.append(
                f"That's {_format_currency(int(waste_cost))} in wasted "
                f"food cost per week."
            )

        if prep_qty and historical_avg:
            parts.append(
                f"Based on your last 4 weeks, {historical_avg:.0f} portions "
                f"is the right prep target for today."
            )

        # Supplier price spike
        if evidence.get("price_increase_pct"):
            ingredient = evidence.get("ingredient_name", "ingredient")
            parts.append(
                f"{ingredient} prices are up "
                f"{evidence['price_increase_pct']:.0f}% this week."
            )

        return parts

    def _evidence_customer(self, evidence: dict) -> list[str]:
        """Build customer evidence sentences."""
        parts = []

        lapsed_count = evidence.get("lapsed_count")
        lapsed_revenue = evidence.get("lapsed_revenue_paisa")
        cohort_conversion = evidence.get("cohort_conversion_pct")
        high_ltv_trait = evidence.get("high_ltv_common_trait")
        coverage_pct = evidence.get("coverage_pct")

        if lapsed_count:
            parts.append(
                f"{lapsed_count} regulars who used to visit often "
                f"haven't been back in 45+ days."
            )

        if lapsed_revenue:
            parts.append(
                f"Together they represented "
                f"{_format_currency(int(lapsed_revenue))} in monthly revenue."
            )

        if cohort_conversion is not None:
            parts.append(
                f"Your first-visit to second-visit conversion is "
                f"{cohort_conversion:.0f}%."
            )

        if high_ltv_trait:
            parts.append(f"Your best customers tend to {high_ltv_trait}.")

        if coverage_pct and coverage_pct < 60:
            parts.append(
                italic(f"Note: customer data covers ~{coverage_pct:.0f}% "
                       f"of transactions — cash/anonymous orders excluded.")
            )

        return parts

    def _evidence_cultural(self, evidence: dict) -> list[str]:
        """Build cultural/calendar evidence sentences."""
        parts = []

        event_name = evidence.get("event_name")
        event_date = evidence.get("event_date")
        behavior_change = evidence.get("expected_behavior")
        surge_dishes = evidence.get("surge_dishes", [])

        if event_name and event_date:
            days_away = None
            if isinstance(event_date, str):
                try:
                    evt = date.fromisoformat(event_date)
                    days_away = (evt - date.today()).days
                except ValueError:
                    pass
            elif isinstance(event_date, date):
                days_away = (event_date - date.today()).days

            if days_away is not None and days_away > 0:
                parts.append(
                    f"{event_name} is {days_away} days away."
                )

        if behavior_change:
            parts.append(behavior_change)

        if surge_dishes:
            dish_list = ", ".join(surge_dishes[:3])
            parts.append(f"Expect demand for: {dish_list}.")

        return parts

    def _evidence_generic(self, evidence: dict) -> list[str]:
        """Fallback evidence builder for unknown categories."""
        parts = []
        for key in ["deviation_pct", "data_points_count", "current_value"]:
            if key in evidence:
                val = evidence[key]
                if key == "deviation_pct":
                    pct = val * 100 if abs(val) < 1 else val
                    parts.append(f"Deviation: {_format_pct(pct)} from baseline.")
                elif key == "current_value" and isinstance(val, (int, float)):
                    parts.append(f"Current: {_format_currency(int(val))}.")
        return parts

    # ------------------------------------------------------------------
    # Ranking and limits
    # ------------------------------------------------------------------

    def _rank_findings(self, findings: list[Finding]) -> list[Finding]:
        """Rank findings by urgency + estimated impact for batching."""
        urgency_score = {
            Urgency.IMMEDIATE: 3,
            Urgency.THIS_WEEK: 2,
            Urgency.STRATEGIC: 1,
            "immediate": 3,
            "this_week": 2,
            "strategic": 1,
        }

        def sort_key(f: Finding) -> tuple:
            u = urgency_score.get(f.urgency, 0)
            impact = f.estimated_impact_paisa or 0
            return (-u, -impact)

        return sorted(findings, key=sort_key)

    def _enforce_limits(self, message: str) -> str:
        """Enforce word and character limits."""
        # Character limit
        if len(message) > MAX_WHATSAPP_CHARS:
            message = message[:MAX_WHATSAPP_CHARS - 5] + "\n..."

        # Word limit — trim from the end but preserve action section
        words = message.split()
        if len(words) > MAX_FINDING_WORDS:
            # Find the action section and preserve it
            action_idx = None
            for i, w in enumerate(words):
                if w == "*Action:*":
                    action_idx = i
                    break

            if action_idx and action_idx < MAX_FINDING_WORDS:
                # Keep everything up to the word limit
                message = " ".join(words[:MAX_FINDING_WORDS])
            else:
                message = " ".join(words[:MAX_FINDING_WORDS])

        return message
