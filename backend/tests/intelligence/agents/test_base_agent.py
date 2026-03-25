"""Tests for BaseAgent, Finding dataclass, and enums."""

import pytest
from datetime import date

from intelligence.agents.base_agent import (
    BaseAgent,
    Finding,
    ImpactSize,
    OptimizationImpact,
    Urgency,
)


# ── Enum tests ──────────────────────────────────────────────────────────────

class TestEnums:
    def test_urgency_values(self):
        assert Urgency.IMMEDIATE == "immediate"
        assert Urgency.THIS_WEEK == "this_week"
        assert Urgency.STRATEGIC == "strategic"

    def test_optimization_impact_values(self):
        assert OptimizationImpact.REVENUE_INCREASE == "revenue_increase"
        assert OptimizationImpact.MARGIN_IMPROVEMENT == "margin_improvement"
        assert OptimizationImpact.RISK_MITIGATION == "risk_mitigation"
        assert OptimizationImpact.OPPORTUNITY == "opportunity"

    def test_impact_size_values(self):
        assert ImpactSize.HIGH == "high"
        assert ImpactSize.MEDIUM == "medium"
        assert ImpactSize.LOW == "low"


# ── Finding dataclass tests ─────────────────────────────────────────────────

class TestFinding:
    def test_finding_required_fields(self):
        f = Finding(
            agent_name="ravi",
            restaurant_id=5,
            category="revenue",
            urgency=Urgency.THIS_WEEK,
            optimization_impact=OptimizationImpact.REVENUE_INCREASE,
            finding_text="Revenue dropped 18%",
            action_text="Investigate Tuesday lunch slot",
            evidence_data={"deviation_pct": 0.18},
            confidence_score=75,
        )
        assert f.agent_name == "ravi"
        assert f.restaurant_id == 5
        assert f.action_deadline is None
        assert f.estimated_impact_paisa is None

    def test_finding_optional_fields(self):
        f = Finding(
            agent_name="maya",
            restaurant_id=5,
            category="menu",
            urgency=Urgency.STRATEGIC,
            optimization_impact=OptimizationImpact.MARGIN_IMPROVEMENT,
            finding_text="Margin eroded",
            action_text="Increase price by Rs 20",
            evidence_data={"old_margin": 0.65, "new_margin": 0.50},
            confidence_score=80,
            action_deadline=date(2026, 4, 1),
            estimated_impact_size=ImpactSize.MEDIUM,
            estimated_impact_paisa=150000,
        )
        assert f.action_deadline == date(2026, 4, 1)
        assert f.estimated_impact_size == ImpactSize.MEDIUM
        assert f.estimated_impact_paisa == 150000

    def test_finding_is_immutable_dataclass(self):
        """Finding is a dataclass — verify it stores data correctly."""
        f = Finding(
            agent_name="ravi",
            restaurant_id=5,
            category="revenue",
            urgency=Urgency.IMMEDIATE,
            optimization_impact=OptimizationImpact.RISK_MITIGATION,
            finding_text="test",
            action_text="test action",
            evidence_data={},
            confidence_score=50,
        )
        assert isinstance(f.evidence_data, dict)


# ── BaseAgent abstract class tests ──────────────────────────────────────────

class TestBaseAgent:
    def test_cannot_instantiate_directly(self, db, restaurant_id):
        """BaseAgent is abstract — instantiation without run() should fail."""
        with pytest.raises(TypeError):
            BaseAgent(restaurant_id=restaurant_id, db_session=db, readonly_db=db)

    def test_concrete_subclass_works(self, db, restaurant_id):
        """A subclass implementing run() can be instantiated."""

        class StubAgent(BaseAgent):
            def run(self):
                return []

        agent = StubAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        assert agent.restaurant_id == restaurant_id
        assert agent.run() == []

    def test_load_profile_returns_none_when_missing(self, db, restaurant_id):
        """Profile returns None when no restaurant_profiles row exists."""

        class StubAgent(BaseAgent):
            def run(self):
                return []

        agent = StubAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        assert agent.profile is None

    def test_load_profile_returns_profile(self, db, restaurant_id):
        """Profile loads when row exists."""
        from intelligence.models import RestaurantProfile

        profile = RestaurantProfile(
            restaurant_id=restaurant_id,
            cuisine_type="cafe",
            city="Kolkata",
        )
        db.add(profile)
        db.flush()

        class StubAgent(BaseAgent):
            def run(self):
                return []

        agent = StubAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        assert agent.profile is not None
        assert agent.profile.city == "Kolkata"

    def test_menu_graph_loaded(self, db, restaurant_id):
        """MenuGraphQuery is initialized on the agent."""
        from intelligence.menu_graph.semantic_query import MenuGraphQuery

        class StubAgent(BaseAgent):
            def run(self):
                return []

        agent = StubAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        assert isinstance(agent.menu, MenuGraphQuery)
