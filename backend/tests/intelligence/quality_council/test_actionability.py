"""Tests for Quality Council Stage 3: Actionability + Identity Filter."""

import pytest
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from intelligence.agents.base_agent import Finding, Urgency, OptimizationImpact
from intelligence.quality_council.actionability import actionability_check
from intelligence.models import AgentFinding, RestaurantProfile


def _make_finding(**overrides) -> Finding:
    defaults = {
        "agent_name": "ravi",
        "restaurant_id": 1,
        "category": "revenue",
        "urgency": Urgency.THIS_WEEK,
        "optimization_impact": OptimizationImpact.REVENUE_INCREASE,
        "finding_text": "Revenue declined 20% vs baseline",
        "action_text": "Investigate the revenue drop and launch a Tuesday lunch promo",
        "evidence_data": {"data_points_count": 10, "deviation_pct": 0.20},
        "confidence_score": 70,
        "action_deadline": date.today() + timedelta(days=7),
        "estimated_impact_paisa": 500000,
    }
    defaults.update(overrides)
    return Finding(**defaults)


def _insert_sent_finding(db: Session, restaurant_id: int, agent_name: str,
                         category: str, action_text: str,
                         days_ago: int = 3) -> AgentFinding:
    """Insert a previously sent finding for dedup checks."""
    af = AgentFinding(
        restaurant_id=restaurant_id,
        agent_name=agent_name,
        category=category,
        urgency="this_week",
        optimization_impact="revenue_increase",
        finding_text="Previous finding",
        action_text=action_text,
        confidence_score=70,
        status="sent",
        sent_at=datetime.now() - timedelta(days=days_ago),
        created_at=datetime.now() - timedelta(days=days_ago),
    )
    db.add(af)
    db.flush()
    return af


class TestActionabilityCheck:

    def test_passes_with_all_criteria(self, db, restaurant_id):
        finding = _make_finding(restaurant_id=restaurant_id)
        passed, reason = actionability_check(finding, restaurant_id, db)
        assert passed is True
        assert reason == "passed"

    def test_fails_vague_action_text(self, db, restaurant_id):
        """Action text < 20 chars -> fail."""
        finding = _make_finding(
            restaurant_id=restaurant_id,
            action_text="Do something",
        )
        passed, reason = actionability_check(finding, restaurant_id, db)
        assert passed is False
        assert reason == "action_text_too_vague"

    def test_fails_no_deadline(self, db, restaurant_id):
        finding = _make_finding(
            restaurant_id=restaurant_id,
            action_deadline=None,
        )
        passed, reason = actionability_check(finding, restaurant_id, db)
        assert passed is False
        assert reason == "no_deadline"

    def test_fails_no_estimated_impact(self, db, restaurant_id):
        finding = _make_finding(
            restaurant_id=restaurant_id,
            estimated_impact_paisa=None,
        )
        passed, reason = actionability_check(finding, restaurant_id, db)
        assert passed is False
        assert reason == "no_estimated_impact"

    def test_fails_past_deadline(self, db, restaurant_id):
        finding = _make_finding(
            restaurant_id=restaurant_id,
            action_deadline=date.today() - timedelta(days=1),
        )
        passed, reason = actionability_check(finding, restaurant_id, db)
        assert passed is False
        assert reason == "action_deadline_already_passed"

    def test_fails_duplicate_of_recent_sent(self, db, restaurant_id):
        """Jaccard similarity > 0.6 with recently sent finding -> duplicate."""
        action = "Investigate the revenue drop and launch a Tuesday lunch promo"
        _insert_sent_finding(
            db, restaurant_id, "ravi", "revenue",
            action_text=action, days_ago=2,
        )

        finding = _make_finding(
            restaurant_id=restaurant_id,
            action_text=action,  # identical
        )
        passed, reason = actionability_check(finding, restaurant_id, db)
        assert passed is False
        assert reason == "duplicate_of_recent_finding"

    def test_passes_different_action_text(self, db, restaurant_id):
        """Different action text should not be flagged as duplicate."""
        _insert_sent_finding(
            db, restaurant_id, "ravi", "revenue",
            action_text="Check platform listing quality and ratings",
            days_ago=2,
        )

        finding = _make_finding(restaurant_id=restaurant_id)
        passed, reason = actionability_check(finding, restaurant_id, db)
        assert passed is True

    def test_identity_conflict_flagged(self, db, restaurant_id):
        """If action conflicts with non-negotiable, flag it."""
        from sqlalchemy import text
        # Insert profile directly via SQL to avoid ARRAY binding issue in SQLite
        db.execute(
            text(
                "INSERT INTO restaurant_profiles "
                "(restaurant_id, has_delivery, has_dine_in, has_takeaway, "
                "non_negotiables, preferred_language, "
                "communication_frequency, onboarding_complete, onboarding_step, "
                "profile_version) "
                'VALUES (:rid, :del, :din, :tak, :nn, :lang, :freq, :onb, :step, :ver)'
            ),
            {
                "rid": restaurant_id,
                "del": False,
                "din": True,
                "tak": False,
                "nn": '["never reduce portion sizes", "no dark roast"]',
                "lang": "english",
                "freq": "normal",
                "onb": False,
                "step": 0,
                "ver": 1,
            },
        )
        db.flush()

        finding = _make_finding(
            restaurant_id=restaurant_id,
            action_text="Reduce portion sizes for the avocado toast to improve margins",
        )
        passed, reason = actionability_check(finding, restaurant_id, db)
        # Should still pass but with identity_conflict flag
        assert passed is True
        assert "identity_conflict" in reason
