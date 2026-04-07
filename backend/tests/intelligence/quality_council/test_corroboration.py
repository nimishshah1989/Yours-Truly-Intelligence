"""Tests for Quality Council Stage 2: Corroboration Check."""

import pytest
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from intelligence.agents.base_agent import Finding, Urgency, OptimizationImpact
from intelligence.quality_council.corroboration import (
    corroboration_check,
    signals_align,
)
from intelligence.models import AgentFinding


def _make_finding(**overrides) -> Finding:
    defaults = {
        "agent_name": "ravi",
        "restaurant_id": 1,
        "category": "revenue",
        "urgency": Urgency.THIS_WEEK,
        "optimization_impact": OptimizationImpact.REVENUE_INCREASE,
        "finding_text": "Revenue declined 20% vs baseline",
        "action_text": "Investigate the drop and run a promo this week",
        "evidence_data": {"data_points_count": 10, "deviation_pct": 0.20},
        "confidence_score": 70,
        "action_deadline": date.today() + timedelta(days=7),
    }
    defaults.update(overrides)
    return Finding(**defaults)


def _insert_finding(db: Session, restaurant_id: int, agent_name: str,
                    category: str, days_ago: int = 1,
                    status: str = "pending") -> AgentFinding:
    """Insert a finding into agent_findings for corroboration lookup."""
    af = AgentFinding(
        restaurant_id=restaurant_id,
        agent_name=agent_name,
        category=category,
        urgency="this_week",
        optimization_impact="revenue_increase",
        finding_text=f"Test finding from {agent_name}",
        action_text="Test action text that is long enough",
        confidence_score=70,
        status=status,
        created_at=datetime.now() - timedelta(days=days_ago),
    )
    db.add(af)
    db.flush()
    return af


class TestSignalsAlign:
    """Unit tests for signals_align() function."""

    def test_revenue_aligns_with_stock(self):
        f1 = _make_finding(agent_name="ravi", category="revenue")
        f2 = _make_finding(agent_name="arjun", category="stock")
        assert signals_align(f1, f2) is True

    def test_revenue_aligns_with_customer(self):
        f1 = _make_finding(agent_name="ravi", category="revenue")
        f2 = _make_finding(agent_name="sara", category="customer")
        assert signals_align(f1, f2) is True

    def test_menu_aligns_with_stock(self):
        f1 = _make_finding(agent_name="maya", category="menu")
        f2 = _make_finding(agent_name="arjun", category="stock")
        assert signals_align(f1, f2) is True

    def test_cultural_aligns_with_revenue(self):
        f1 = _make_finding(agent_name="priya", category="cultural")
        f2 = _make_finding(agent_name="ravi", category="revenue")
        assert signals_align(f1, f2) is True

    def test_unrelated_agents_do_not_align(self):
        f1 = _make_finding(agent_name="ravi", category="revenue")
        f2 = _make_finding(agent_name="maya", category="menu")
        assert signals_align(f1, f2) is False

    def test_same_agent_does_not_align_with_self(self):
        f1 = _make_finding(agent_name="ravi", category="revenue")
        f2 = _make_finding(agent_name="ravi", category="revenue")
        assert signals_align(f1, f2) is False


class TestCorroborationCheck:
    """Integration tests for corroboration_check()."""

    def test_passes_with_corroborating_finding(self, db, restaurant_id):
        """Ravi finding + recent Arjun stock finding = corroborated."""
        _insert_finding(db, restaurant_id, "arjun", "stock", days_ago=2)

        finding = _make_finding(
            restaurant_id=restaurant_id,
            agent_name="ravi",
            category="revenue",
        )
        passed, agents, reason = corroboration_check(finding, restaurant_id, db)
        assert passed is True
        assert "arjun" in agents
        assert reason == "corroborated"

    def test_fails_without_corroboration(self, db, restaurant_id):
        """No recent findings from other agents -> fail."""
        finding = _make_finding(
            restaurant_id=restaurant_id,
            agent_name="ravi",
            category="revenue",
        )
        passed, agents, reason = corroboration_check(finding, restaurant_id, db)
        assert passed is False
        assert reason == "no_corroboration"

    def test_ignores_findings_older_than_7_days(self, db, restaurant_id):
        """Finding from 10 days ago should not count."""
        _insert_finding(db, restaurant_id, "arjun", "stock", days_ago=10)

        finding = _make_finding(
            restaurant_id=restaurant_id,
            agent_name="ravi",
            category="revenue",
        )
        passed, agents, reason = corroboration_check(finding, restaurant_id, db)
        assert passed is False

    def test_solo_exception_immediate_high_confidence(self, db, restaurant_id):
        """Solo exception: urgency=immediate AND confidence >= 85."""
        finding = _make_finding(
            restaurant_id=restaurant_id,
            agent_name="kiran",
            category="competition",
            urgency=Urgency.IMMEDIATE,
            confidence_score=90,
        )
        passed, agents, reason = corroboration_check(finding, restaurant_id, db)
        assert passed is True
        assert reason == "solo_high_confidence_exception"

    def test_solo_exception_fails_below_85_confidence(self, db, restaurant_id):
        """Solo exception requires confidence >= 85."""
        finding = _make_finding(
            restaurant_id=restaurant_id,
            agent_name="kiran",
            category="competition",
            urgency=Urgency.IMMEDIATE,
            confidence_score=80,
        )
        passed, agents, reason = corroboration_check(finding, restaurant_id, db)
        assert passed is False

    def test_solo_exception_fails_non_immediate(self, db, restaurant_id):
        """Solo exception requires urgency=immediate."""
        finding = _make_finding(
            restaurant_id=restaurant_id,
            agent_name="kiran",
            category="competition",
            urgency=Urgency.THIS_WEEK,
            confidence_score=90,
        )
        passed, agents, reason = corroboration_check(finding, restaurant_id, db)
        assert passed is False

    def test_ignores_same_agent_findings(self, db, restaurant_id):
        """Finding from the same agent should not count as corroboration."""
        _insert_finding(db, restaurant_id, "ravi", "revenue", days_ago=1)

        finding = _make_finding(
            restaurant_id=restaurant_id,
            agent_name="ravi",
            category="revenue",
        )
        passed, agents, reason = corroboration_check(finding, restaurant_id, db)
        assert passed is False
