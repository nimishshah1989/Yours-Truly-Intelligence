"""Tests for Chef — Recipe & Innovation Catalyst agent.

Golden example and scoring function from PRODUCTION_PRD_v2.md PHASE-J2.
Golden example must score >= 0.75 on the 4-dimension scoring function.
"""

import re
import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from intelligence.agents.base_agent import Finding, Urgency, ImpactSize
from intelligence.agents.chef import ChefAgent, IDENTITY_CONFLICTS


# ── Scoring function (from PRD) ─────────────────────────────────────────────

def score_chef_finding(finding: Finding) -> float:
    score = 0.0

    # 1. Grounded in external data (cites trends, competitors, or research) — 0.25
    grounding_terms = ["competitor", "trend", "research", "survey", "65%", "72%",
                       "mumbai", "bangalore", "sienna", "third wave", "blue tokai"]
    if any(t in finding.finding_text.lower() for t in grounding_terms):
        score += 0.25

    # 2. Includes financial modelling (cost, margin, projected revenue) — 0.30
    financial_terms = ["cost", "margin", "₹", "incremental", "projected",
                       "revenue"]
    if sum(1 for t in financial_terms if t in finding.action_text.lower()) >= 3:
        score += 0.30

    # 3. Fits restaurant identity (specialty coffee, not random cuisine) — 0.20
    identity_terms = ["coffee", "latte", "cold brew", "pour over", "brunch",
                      "specialty"]
    if any(t in finding.action_text.lower() for t in identity_terms):
        score += 0.20

    # 4. Has a specific start action (not just "consider") — 0.25
    specific_actions = ["order", "add", "trial", "start", "announce",
                        "launch", "prep"]
    if any(t in finding.action_text.lower() for t in specific_actions):
        score += 0.25

    return score


# ── Golden Example: Oat Milk Recommendation ─────────────────────────────────

class TestGoldenExampleOatMilk:
    """PRD Golden Example: Oat milk trend-informed menu suggestion."""

    def _make_finding(self) -> Finding:
        return Finding(
            agent_name="chef",
            restaurant_id=1,
            category="innovation",
            urgency=Urgency.THIS_WEEK,
            optimization_impact="revenue_increase",
            finding_text=(
                "Oat milk is now standard at 65% of specialty cafés in Mumbai "
                "and Bangalore. Your direct competitors Sienna Café and Third "
                "Wave already offer it. 72% of under-30 coffee drinkers — "
                "your core demographic — say plant milk availability "
                "influences café choice. You're one of the few specialty "
                "cafés in Kolkata without it."
            ),
            action_text=(
                "Add oat milk as a ₹50 premium option for Latte, Iced Latte, "
                "and Cappuccino. Cost: ₹22/serving (₹15 incremental vs dairy). "
                "At ₹50 premium, margin is ₹35/serve — better than your dairy "
                "margin. Projected: if 15% of Latte/Cappuccino orders switch "
                "to oat milk, that's ~₹4,500/month incremental margin from a "
                "single ingredient addition. Start small: order 10L from Oatly "
                "or Minor Figures. 2-week trial. Announce on Instagram — this "
                "is content that your audience cares about."
            ),
            evidence_data={
                "opportunity_type": "trend_gap",
                "keyword": "oat milk",
                "kb_sources": 3,
                "competitor_offers": True,
                "competitor_name": "Sienna Café",
                "cost_per_serve_paisa": 2200,
                "margin_per_serve_paisa": 2800,
                "projected_monthly_impact_paisa": 450000,
                "relevance_check": True,
                "data_points_count": 5,
            },
            confidence_score=82,
            estimated_impact_size=ImpactSize.MEDIUM,
            estimated_impact_paisa=450000,
        )

    def test_scoring_meets_bar(self):
        finding = self._make_finding()
        score = score_chef_finding(finding)
        assert score >= 0.75, f"Golden example scored {score}, need >= 0.75"

    def test_grounded_in_data(self):
        finding = self._make_finding()
        text_lower = finding.finding_text.lower()
        assert "65%" in finding.finding_text
        assert "sienna" in text_lower or "third wave" in text_lower

    def test_has_financial_model(self):
        finding = self._make_finding()
        action = finding.action_text.lower()
        assert "cost" in action
        assert "margin" in action
        assert "₹" in finding.action_text

    def test_fits_coffee_identity(self):
        finding = self._make_finding()
        action = finding.action_text.lower()
        assert any(t in action for t in ["latte", "cappuccino", "coffee"])

    def test_has_specific_action(self):
        finding = self._make_finding()
        action = finding.action_text.lower()
        assert "start" in action or "add" in action or "trial" in action

    def test_has_impact_estimate(self):
        finding = self._make_finding()
        assert finding.estimated_impact_paisa == 450000


# ── Identity guardrail tests ────────────────────────────────────────────────

class TestIdentityGuardrails:
    def test_biryani_conflicts(self):
        assert "biryani" in IDENTITY_CONFLICTS

    def test_pizza_conflicts(self):
        assert "pizza" in IDENTITY_CONFLICTS

    def test_coffee_does_not_conflict(self):
        assert "coffee" not in IDENTITY_CONFLICTS

    def test_identity_check_rejects_biryani(self):
        agent = ChefAgent.__new__(ChefAgent)
        agent.profile = None
        assert not agent._fits_identity("Add biryani to weekend menu")

    def test_identity_check_accepts_latte(self):
        agent = ChefAgent.__new__(ChefAgent)
        agent.profile = None
        assert agent._fits_identity("Add oat milk latte option")


# ── Agent run tests (with mocked DB) ────────────────────────────────────────

class TestChefAgentRun:
    def _make_agent(self):
        db = MagicMock()
        rodb = MagicMock()

        profile = MagicMock()
        profile.cuisine_type = "Café"
        profile.cuisine_subtype = "Specialty coffee, all-day brunch"

        agent = ChefAgent.__new__(ChefAgent)
        agent.restaurant_id = 1
        agent.db = db
        agent.rodb = rodb
        agent.profile = profile
        agent.menu = None

        return agent

    def test_returns_list_of_findings(self):
        agent = self._make_agent()
        agent.rodb.execute = MagicMock(return_value=MagicMock(fetchall=lambda: []))

        with patch.object(agent, 'query_knowledge_base', return_value=[]):
            findings = agent.run()

        assert isinstance(findings, list)

    def test_max_one_finding(self):
        agent = self._make_agent()
        agent.rodb.execute = MagicMock(return_value=MagicMock(fetchall=lambda: []))

        with patch.object(agent, 'query_knowledge_base', return_value=[]):
            findings = agent.run()

        assert len(findings) <= 1

    def test_fails_silently(self):
        agent = self._make_agent()
        agent.rodb.execute = MagicMock(side_effect=Exception("DB down"))

        with patch.object(agent, 'query_knowledge_base', return_value=[]):
            findings = agent.run()

        assert findings == []

    def test_no_finding_without_data(self):
        agent = self._make_agent()
        agent.rodb.execute = MagicMock(return_value=MagicMock(fetchall=lambda: []))

        with patch.object(agent, 'query_knowledge_base', return_value=[]):
            findings = agent.run()

        assert findings == []
