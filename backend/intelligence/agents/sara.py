"""Sara — Customer Intelligence Agent.

RFM segmentation using resolved_customers (falls back to raw customers table).
Tracks: new customer return rate, lapsed regulars, revenue concentration,
cohort retention month-on-month.

Rules:
- Uses resolved_customers when populated, raw customers otherwise
- Scores R/F/M on 1-5 scale relative to THIS restaurant's distribution
- Max 2 findings per run
- Fails silently — returns [] on error
"""

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, and_, case
from sqlalchemy.orm import Session

from intelligence.agents.base_agent import (
    BaseAgent,
    Finding,
    ImpactSize,
    OptimizationImpact,
    Urgency,
)

logger = logging.getLogger("ytip.agents.sara")

# Thresholds
LAPSED_DAYS = 45  # Haven't visited in 45+ days
LAPSED_MIN_VISITS = 4  # Must have visited 4+ times to count as lapsed regular
RFM_LOOKBACK_DAYS = 90
NEW_CUSTOMER_LOOKBACK_DAYS = 30
RETURN_WINDOW_DAYS = 30
MAX_FINDINGS = 2

# RFM segment definitions: (min_R, min_F, min_M)
RFM_SEGMENTS = {
    "champion": {"r_min": 4, "f_min": 4, "m_min": 4},
    "loyal": {"r_min": 3, "f_min": 4, "m_min": 0},
    "at_risk": {"r_max": 2, "f_min": 3, "m_min": 0},
    "cannot_lose": {"r_max": 2, "f_min": 4, "m_min": 4},
    "new": {"is_new": True},
    "hibernating": {"r_max": 1, "f_min": 2, "m_min": 0},
}


def _format_rupees(paisa: int) -> str:
    """Format paisa as Indian rupee string."""
    rupees = paisa / 100
    if rupees >= 100000:
        return f"Rs {rupees / 100000:,.2f}L"
    elif rupees >= 1000:
        return f"Rs {rupees:,.0f}"
    return f"Rs {rupees:.0f}"


def _score_quintile(value: float, all_values: list[float]) -> int:
    """Score a value 1-5 based on quintile position in distribution."""
    if not all_values:
        return 3
    sorted_vals = sorted(all_values)
    n = len(sorted_vals)
    if n < 5:
        # Too few data points — use simple rank
        rank = sum(1 for v in sorted_vals if v <= value)
        return max(1, min(5, round(rank / n * 5)))

    quintiles = [sorted_vals[int(n * q / 5)] for q in range(1, 5)]

    if value <= quintiles[0]:
        return 1
    elif value <= quintiles[1]:
        return 2
    elif value <= quintiles[2]:
        return 3
    elif value <= quintiles[3]:
        return 4
    else:
        return 5


class SaraAgent(BaseAgent):
    """Customer Intelligence agent."""

    agent_name = "sara"
    category = "customer"

    def run(self) -> list[Finding]:
        """Run all customer analyses. Return max 2 findings."""
        findings: list[Finding] = []

        try:
            analyses = [
                self._analyze_rfm_segments,
                self._analyze_lapsed_regulars,
                self._analyze_new_customer_return_rate,
            ]

            for analysis in analyses:
                try:
                    result = analysis()
                    if result:
                        findings.append(result)
                except Exception as e:
                    logger.warning("Sara analysis %s failed: %s",
                                   analysis.__name__, e)
                    continue

        except Exception as e:
            logger.error("Sara run failed entirely: %s", e)
            return []

        findings.sort(key=lambda f: f.confidence_score, reverse=True)
        return findings[:MAX_FINDINGS]

    def _get_customer_data(self) -> list[dict]:
        """Get customer data — prefer resolved_customers, fall back to raw.

        Returns list of dicts with: id, name, last_order_date,
        order_count_90d, total_spend_90d, first_order_date.
        """
        # Try resolved_customers first
        try:
            from intelligence.models import ResolvedCustomer

            resolved = (
                self.rodb.query(ResolvedCustomer)
                .filter(
                    ResolvedCustomer.restaurant_id == self.restaurant_id,
                )
                .all()
            )

            if resolved and len(resolved) >= 5:
                return [
                    {
                        "id": rc.id,
                        "name": rc.display_name,
                        "last_order_date": rc.last_seen,
                        "order_count": rc.total_orders,
                        "total_spend": rc.total_spend_paisa,
                        "first_order_date": rc.first_seen,
                        "source": "resolved",
                    }
                    for rc in resolved
                    if rc.total_orders and rc.total_orders > 0
                ]
        except Exception as e:
            logger.debug("Resolved customers unavailable: %s", e)

        # Fall back to raw customers table
        try:
            from core.models import Customer

            customers = (
                self.rodb.query(Customer)
                .filter(
                    Customer.restaurant_id == self.restaurant_id,
                    Customer.total_visits > 0,
                )
                .all()
            )

            if not customers:
                return []

            return [
                {
                    "id": c.id,
                    "name": c.name,
                    "last_order_date": c.last_visit,
                    "order_count": c.total_visits,
                    "total_spend": c.total_spend,
                    "first_order_date": c.first_visit,
                    "source": "raw",
                }
                for c in customers
            ]
        except Exception as e:
            logger.warning("Failed to load customer data: %s", e)
            return []

    def _compute_rfm(self, customers: list[dict]) -> list[dict]:
        """Compute RFM scores and segment labels for customers."""
        today = date.today()

        # Compute raw values
        for c in customers:
            last_date = c.get("last_order_date")
            if isinstance(last_date, datetime):
                last_date = last_date.date()
            c["recency_days"] = (today - last_date).days if last_date else 999

            first_date = c.get("first_order_date")
            if isinstance(first_date, datetime):
                first_date = first_date.date()
            c["is_new"] = (
                first_date is not None
                and (today - first_date).days <= NEW_CUSTOMER_LOOKBACK_DAYS
            )

        # Build value distributions for quintile scoring
        # For recency: lower is better, so invert
        recency_values = [c["recency_days"] for c in customers]
        frequency_values = [c["order_count"] for c in customers]
        monetary_values = [c["total_spend"] for c in customers]

        for c in customers:
            # Recency: invert so lower days = higher score
            r_score = 6 - _score_quintile(c["recency_days"], recency_values)
            r_score = max(1, min(5, r_score))
            c["r_score"] = r_score
            c["f_score"] = _score_quintile(c["order_count"], frequency_values)
            c["m_score"] = _score_quintile(c["total_spend"], monetary_values)

            # Assign segment
            c["segment"] = self._classify_segment(c)

        return customers

    def _classify_segment(self, customer: dict) -> str:
        """Classify a customer into an RFM segment."""
        r, f, m = customer["r_score"], customer["f_score"], customer["m_score"]

        if customer.get("is_new"):
            return "new"
        if r >= 4 and f >= 4 and m >= 4:
            return "champion"
        if r <= 2 and f >= 4 and m >= 4:
            return "cannot_lose"
        if r <= 2 and f >= 3:
            return "at_risk"
        if r >= 3 and f >= 4:
            return "loyal"
        if r <= 1 and f >= 2:
            return "hibernating"
        if r >= 3 and f >= 2:
            return "loyal"
        return "other"

    def _analyze_rfm_segments(self) -> Optional[Finding]:
        """Compute RFM segments and flag concerning distributions."""
        try:
            customers = self._get_customer_data()
            if len(customers) < 5:
                return None

            segmented = self._compute_rfm(customers)

            # Count segments
            segment_counts = defaultdict(int)
            segment_spend = defaultdict(int)
            for c in segmented:
                segment_counts[c["segment"]] += 1
                segment_spend[c["segment"]] += c["total_spend"]

            total_customers = len(segmented)
            total_spend = sum(c["total_spend"] for c in segmented)

            at_risk = segment_counts.get("at_risk", 0)
            cannot_lose = segment_counts.get("cannot_lose", 0)
            champions = segment_counts.get("champion", 0)

            # Calculate top 20% revenue concentration
            sorted_by_spend = sorted(segmented, key=lambda c: c["total_spend"], reverse=True)
            top_20_count = max(1, total_customers // 5)
            top_20_spend = sum(c["total_spend"] for c in sorted_by_spend[:top_20_count])
            top_20_concentration = top_20_spend / total_spend if total_spend > 0 else 0

            # Determine the most actionable finding
            risk_count = at_risk + cannot_lose
            if risk_count == 0:
                return None

            risk_pct = risk_count / total_customers
            risk_spend = segment_spend.get("at_risk", 0) + segment_spend.get("cannot_lose", 0)

            return Finding(
                agent_name=self.agent_name,
                restaurant_id=self.restaurant_id,
                category=self.category,
                urgency=Urgency.THIS_WEEK if cannot_lose > 0 else Urgency.STRATEGIC,
                optimization_impact=OptimizationImpact.REVENUE_INCREASE,
                finding_text=(
                    f"{risk_count} customers ({risk_pct * 100:.0f}% of base) are in "
                    f"at-risk or cannot-lose segments. Combined historical spend: "
                    f"{_format_rupees(risk_spend)}. Champions: {champions}, "
                    f"At Risk: {at_risk}, Cannot Lose: {cannot_lose}."
                ),
                action_text=(
                    f"Priority: reach out to the {cannot_lose} cannot-lose customers "
                    f"first — they were your highest-value regulars. "
                    f"For delivery: use platform 'we miss you' offers. "
                    f"For dine-in: consider a WhatsApp message with a personal offer."
                ),
                evidence_data={
                    "segment_counts": dict(segment_counts),
                    "segment_spend": {k: v for k, v in segment_spend.items()},
                    "total_customers": total_customers,
                    "top_20pct_revenue_concentration": round(top_20_concentration, 4),
                    "risk_count": risk_count,
                    "risk_spend_paisa": risk_spend,
                    "deviation_pct": risk_pct,
                    "data_points_count": total_customers,
                },
                confidence_score=75,
                action_deadline=date.today() + timedelta(days=7),
                estimated_impact_size=ImpactSize.HIGH if risk_spend > 1000000 else ImpactSize.MEDIUM,
                estimated_impact_paisa=int(risk_spend * 0.10),  # 10% recovery estimate
            )
        except Exception as e:
            logger.warning("RFM segment analysis failed: %s", e)
            return None

    def _analyze_lapsed_regulars(self) -> Optional[Finding]:
        """Flag customers with 4+ visits who haven't been seen in 45+ days."""
        try:
            customers = self._get_customer_data()
            if not customers:
                return None

            today = date.today()
            lapsed = []

            for c in customers:
                last_date = c.get("last_order_date")
                if isinstance(last_date, datetime):
                    last_date = last_date.date()
                if last_date is None:
                    continue

                days_since = (today - last_date).days
                visits = c.get("order_count", 0)

                if visits >= LAPSED_MIN_VISITS and days_since >= LAPSED_DAYS:
                    lapsed.append({
                        "name": c.get("name", "Unknown"),
                        "visits": visits,
                        "days_since_last": days_since,
                        "total_spend": c.get("total_spend", 0),
                    })

            if not lapsed:
                return None

            lapsed.sort(key=lambda x: x["total_spend"], reverse=True)
            total_lapsed_spend = sum(l["total_spend"] for l in lapsed)

            return Finding(
                agent_name=self.agent_name,
                restaurant_id=self.restaurant_id,
                category=self.category,
                urgency=Urgency.THIS_WEEK,
                optimization_impact=OptimizationImpact.REVENUE_INCREASE,
                finding_text=(
                    f"{len(lapsed)} customers who visited {LAPSED_MIN_VISITS}+ times "
                    f"haven't ordered in {LAPSED_DAYS}+ days. Combined historical "
                    f"spend: {_format_rupees(total_lapsed_spend)}."
                ),
                action_text=(
                    f"For delivery: use platform 'we miss you' offers to lapsed "
                    f"customers. For dine-in: consider a WhatsApp message via "
                    f"PetPooja customer export. A 10% return offer on "
                    f"{_format_rupees(total_lapsed_spend)} annual spend could recover "
                    f"significant revenue."
                ),
                evidence_data={
                    "lapsed_customers": lapsed[:10],
                    "total_lapsed": len(lapsed),
                    "total_lapsed_spend_paisa": total_lapsed_spend,
                    "min_visits_threshold": LAPSED_MIN_VISITS,
                    "days_threshold": LAPSED_DAYS,
                    "deviation_pct": len(lapsed) / max(len(customers), 1),
                    "data_points_count": len(customers),
                },
                confidence_score=80,
                action_deadline=date.today() + timedelta(days=7),
                estimated_impact_size=ImpactSize.HIGH if total_lapsed_spend > 2000000 else ImpactSize.MEDIUM,
                estimated_impact_paisa=int(total_lapsed_spend * 0.10),
            )
        except Exception as e:
            logger.warning("Lapsed regulars analysis failed: %s", e)
            return None

    def _analyze_new_customer_return_rate(self) -> Optional[Finding]:
        """Track 30-day return rate for new customers.

        Flag if the rate has dropped vs the previous period.
        """
        try:
            from core.models import Customer, Order

            today = date.today()
            recent_start = today - timedelta(days=60)
            previous_start = today - timedelta(days=120)

            # Get customers who first visited in the recent 60-day window
            recent_new = (
                self.rodb.query(Customer)
                .filter(
                    Customer.restaurant_id == self.restaurant_id,
                    Customer.first_visit >= recent_start,
                    Customer.first_visit < today - timedelta(days=RETURN_WINDOW_DAYS),
                )
                .all()
            )

            previous_new = (
                self.rodb.query(Customer)
                .filter(
                    Customer.restaurant_id == self.restaurant_id,
                    Customer.first_visit >= previous_start,
                    Customer.first_visit < recent_start,
                )
                .all()
            )

            if len(recent_new) < 3 or len(previous_new) < 3:
                return None

            # Count returnees
            recent_returned = sum(
                1 for c in recent_new
                if c.total_visits and c.total_visits >= 2
            )
            previous_returned = sum(
                1 for c in previous_new
                if c.total_visits and c.total_visits >= 2
            )

            recent_rate = recent_returned / len(recent_new) if recent_new else 0
            previous_rate = previous_returned / len(previous_new) if previous_new else 0

            if previous_rate == 0:
                return None

            drop = previous_rate - recent_rate
            if drop <= 0.05:
                return None  # No significant drop

            return Finding(
                agent_name=self.agent_name,
                restaurant_id=self.restaurant_id,
                category=self.category,
                urgency=Urgency.THIS_WEEK,
                optimization_impact=OptimizationImpact.RISK_MITIGATION,
                finding_text=(
                    f"New customer 30-day return rate has dropped from "
                    f"{previous_rate * 100:.0f}% to {recent_rate * 100:.0f}% — "
                    f"this is the most important early warning metric suggesting "
                    f"the first visit experience is declining."
                ),
                action_text=(
                    f"Investigate what changed — menu, staff, quality, service "
                    f"timing. Review your recent 1-3 star reviews for clues. "
                    f"The data alone can't tell you why, but it's telling you "
                    f"something changed."
                ),
                evidence_data={
                    "recent_return_rate": round(recent_rate, 4),
                    "previous_return_rate": round(previous_rate, 4),
                    "recent_new_count": len(recent_new),
                    "recent_returned_count": recent_returned,
                    "previous_new_count": len(previous_new),
                    "previous_returned_count": previous_returned,
                    "deviation_pct": round(drop, 4),
                    "data_points_count": len(recent_new) + len(previous_new),
                    "baseline_mean": previous_rate,
                    "current_value": recent_rate,
                    "baseline_std": 0,
                },
                confidence_score=70,
                action_deadline=date.today() + timedelta(days=7),
                estimated_impact_size=ImpactSize.HIGH,
            )
        except Exception as e:
            logger.warning("New customer return rate analysis failed: %s", e)
            return None
