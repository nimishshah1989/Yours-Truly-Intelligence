"""Tests for Kiran — Competition & Market Radar agent.

Golden examples and scoring function from PRODUCTION_PRD_v2.md PHASE-J1.
Every golden example must score >= 0.75 on the 4-dimension scoring function.
"""

import re
import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from intelligence.agents.base_agent import Finding, Urgency, ImpactSize
from intelligence.agents.kiran import KiranAgent, _is_relevant_competitor


# ── Scoring function (from PRD) ─────────────────────────────────────────────

def score_kiran_finding(finding: Finding) -> float:
    score = 0.0

    # 1. Names specific competitors — 0.25
    competitor_names = ["sienna", "third wave", "blue tokai", "bloom",
                        "kc roasters"]
    if any(name in finding.finding_text.lower() for name in competitor_names):
        score += 0.25

    # 2. Includes specific prices or ratings — 0.25
    if re.search(r'₹\d+|rating.*\d\.\d|\d+%|\d\.\d.*rating', finding.finding_text):
        score += 0.25

    # 3. Action is strategic, not panicked — 0.25
    panic_terms = ["immediately", "urgent", "crisis", "emergency"]
    strategic_terms = ["visit", "monitor", "consider", "watch",
                       "no change needed", "defensible", "no price change"]
    if (any(t in finding.action_text.lower() for t in strategic_terms) and
            not any(t in finding.action_text.lower() for t in panic_terms)):
        score += 0.25

    # 4. Relevance filter applied — 0.25
    if (finding.evidence_data.get("relevance_check") or
            finding.confidence_score > 0):
        score += 0.25

    return score


# ── Relevance filter tests ──────────────────────────────────────────────────

class TestRelevanceFilter:
    def test_cafe_is_relevant(self):
        assert _is_relevant_competitor(
            {"types": ["cafe"], "name": "Bloom Coffee Lab"},
            None,
        )

    def test_coffee_in_name_is_relevant(self):
        assert _is_relevant_competitor(
            {"name": "KC Roasters Coffee"},
            None,
        )

    def test_bakery_is_relevant(self):
        assert _is_relevant_competitor(
            {"types": ["bakery"], "name": "Artisan Bakehouse"},
            None,
        )

    def test_biryani_is_not_relevant(self):
        assert not _is_relevant_competitor(
            {"types": ["restaurant"], "name": "Arsalan Biryani",
             "distance_km": 3},
            None,
        )

    def test_very_close_competitor_always_relevant(self):
        assert _is_relevant_competitor(
            {"types": ["restaurant"], "name": "Random Place",
             "distance_km": 0.3},
            None,
        )


# ── Golden Example 1: New Competitor Opening ────────────────────────────────

class TestGoldenExample1NewCompetitor:
    """PRD Golden Example 1: Bloom Coffee Lab opens nearby."""

    def _make_finding(self) -> Finding:
        """Create finding matching the golden example input."""
        return Finding(
            agent_name="kiran",
            restaurant_id=1,
            category="competition",
            urgency=Urgency.THIS_WEEK,
            optimization_impact="risk_mitigation",
            finding_text=(
                "New specialty café spotted: Bloom Coffee Lab, 1.2km from you. "
                "Rating 4.3 with 47 reviews. "
                "That's fast traction — worth watching."
            ),
            action_text=(
                "Visit Bloom Coffee Lab this week. Check: their coffee quality, "
                "menu range, pricing vs yours, and what they're doing differently. "
                "They're close enough (1.2km) to share your dine-in catchment."
            ),
            evidence_data={
                "signal_type": "competitor_new",
                "competitor_name": "Bloom Coffee Lab",
                "distance_km": 1.2,
                "rating": 4.3,
                "review_count": 47,
                "relevance_check": True,
                "data_points_count": 1,
            },
            confidence_score=80,
        )

    def test_scoring_meets_bar(self):
        finding = self._make_finding()
        score = score_kiran_finding(finding)
        assert score >= 0.75, f"Golden example 1 scored {score}, need >= 0.75"

    def test_names_specific_competitor(self):
        finding = self._make_finding()
        assert "bloom" in finding.finding_text.lower()

    def test_includes_rating(self):
        finding = self._make_finding()
        assert "4.3" in finding.finding_text

    def test_strategic_not_panicked(self):
        finding = self._make_finding()
        assert "visit" in finding.action_text.lower()
        assert "crisis" not in finding.action_text.lower()

    def test_has_relevance_check(self):
        finding = self._make_finding()
        assert finding.evidence_data["relevance_check"] is True


# ── Golden Example 2: Competitor Promo ──────────────────────────────────────

class TestGoldenExample2CompetitorPromo:
    """PRD Golden Example 2: Third Wave Coffee promo on Swiggy."""

    def _make_finding(self) -> Finding:
        return Finding(
            agent_name="kiran",
            restaurant_id=1,
            category="competition",
            urgency=Urgency.THIS_WEEK,
            optimization_impact="revenue_increase",
            finding_text=(
                "Third Wave Coffee is running 40% off on Swiggy this week "
                "(up to ₹100 on orders above ₹299). "
                "You have no active Swiggy promotion running."
            ),
            action_text=(
                "You don't need to match their discount — that's a margin game "
                "you don't want to play. But if your Swiggy orders dip this "
                "week, this is likely why. Consider: a smaller promotion "
                "(15-20% off) on your highest-margin items to maintain "
                "visibility without killing margin."
            ),
            evidence_data={
                "signal_type": "competitor_promo",
                "competitor_name": "Third Wave Coffee",
                "platform": "swiggy",
                "relevance_check": True,
                "data_points_count": 1,
            },
            confidence_score=72,
        )

    def test_scoring_meets_bar(self):
        finding = self._make_finding()
        score = score_kiran_finding(finding)
        assert score >= 0.75, f"Golden example 2 scored {score}, need >= 0.75"

    def test_names_competitor(self):
        finding = self._make_finding()
        assert "third wave" in finding.finding_text.lower()

    def test_includes_price(self):
        finding = self._make_finding()
        assert "₹" in finding.finding_text


# ── Golden Example 3: Pricing Intelligence ──────────────────────────────────

class TestGoldenExample3PricingIntelligence:
    """PRD Golden Example 3: Cold Brew pricing position."""

    def _make_finding(self) -> Finding:
        return Finding(
            agent_name="kiran",
            restaurant_id=1,
            category="competition",
            urgency=Urgency.STRATEGIC,
            optimization_impact="margin_improvement",
            finding_text=(
                "Your Cold Brew at ₹300 is positioned 2nd highest in "
                "Kolkata's specialty café market (avg ₹295). "
                "Blue Tokai is above you at ₹310. "
                "Sienna and Third Wave are below at ₹280 and ₹290."
            ),
            action_text=(
                "Your pricing is defensible — you're ₹5 above market average "
                "but below the category leader (Blue Tokai). "
                "No price change needed — monitor weekly."
            ),
            confidence_score=70,
            evidence_data={
                "signal_type": "competitor_pricing",
                "item_category": "Cold Brew",
                "our_price": 300,
                "market_avg": 295,
                "relevance_check": True,
                "data_points_count": 4,
            },
        )

    def test_scoring_meets_bar(self):
        finding = self._make_finding()
        score = score_kiran_finding(finding)
        assert score >= 0.75, f"Golden example 3 scored {score}, need >= 0.75"

    def test_names_multiple_competitors(self):
        finding = self._make_finding()
        text_lower = finding.finding_text.lower()
        assert "blue tokai" in text_lower
        assert "sienna" in text_lower

    def test_includes_prices(self):
        finding = self._make_finding()
        assert "₹300" in finding.finding_text
        assert "₹295" in finding.finding_text

    def test_strategic_action(self):
        finding = self._make_finding()
        assert "no price change needed" in finding.action_text.lower()


# ── Agent run tests (with mocked DB) ────────────────────────────────────────

class TestKiranAgentRun:
    def _make_agent(self, signals=None):
        """Create KiranAgent with mocked DB."""
        db = MagicMock()
        rodb = MagicMock()

        # Mock profile
        profile = MagicMock()
        profile.cuisine_type = "Café"
        profile.cuisine_subtype = "Specialty coffee, all-day brunch"

        agent = KiranAgent.__new__(KiranAgent)
        agent.restaurant_id = 1
        agent.db = db
        agent.rodb = rodb
        agent.profile = profile
        agent.menu = None

        return agent

    def test_returns_list_of_findings(self):
        agent = self._make_agent()
        # Mock all DB calls to return empty
        agent.rodb.execute = MagicMock(return_value=MagicMock(fetchall=lambda: []))

        with patch.object(agent, 'query_knowledge_base', return_value=[]):
            findings = agent.run()

        assert isinstance(findings, list)

    def test_max_two_findings(self):
        agent = self._make_agent()
        agent.rodb.execute = MagicMock(return_value=MagicMock(fetchall=lambda: []))

        with patch.object(agent, 'query_knowledge_base', return_value=[]):
            findings = agent.run()

        assert len(findings) <= 2

    def test_fails_silently(self):
        agent = self._make_agent()
        agent.rodb.execute = MagicMock(side_effect=Exception("DB down"))

        with patch.object(agent, 'query_knowledge_base', return_value=[]):
            findings = agent.run()

        assert findings == []
