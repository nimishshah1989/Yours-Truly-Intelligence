"""Quality Council — 15 golden test cases.

6 significance + 4 corroboration + 5 actionability.
Target: >= 14/15 correct (93%+).
"""

import json
import pytest
from datetime import date, datetime, timedelta
from unittest.mock import patch

from sqlalchemy.orm import Session

from intelligence.agents.base_agent import (
    Finding, Urgency, OptimizationImpact, ImpactSize,
)
from intelligence.quality_council.council import QualityCouncil
from intelligence.quality_council.significance import significance_check
from intelligence.quality_council.corroboration import corroboration_check
from intelligence.quality_council.actionability import actionability_check
from intelligence.models import AgentFinding, RestaurantProfile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_finding(**overrides) -> Finding:
    """Build a Finding with sane defaults that passes all stages."""
    defaults = {
        "agent_name": "ravi",
        "restaurant_id": 1,
        "category": "revenue",
        "urgency": Urgency.THIS_WEEK,
        "optimization_impact": OptimizationImpact.REVENUE_INCREASE,
        "finding_text": "Revenue declined 20% vs baseline over past 5 days",
        "action_text": "Investigate the revenue drop and launch a Tuesday lunch promo targeting regulars",
        "evidence_data": {
            "data_points_count": 10,
            "deviation_pct": 0.20,
            "baseline_mean": 50000,
            "baseline_std": 5000,
            "current_value": 40000,
        },
        "confidence_score": 75,
        "action_deadline": date.today() + timedelta(days=7),
        "estimated_impact_paisa": 500000,
        "estimated_impact_size": ImpactSize.MEDIUM,
    }
    defaults.update(overrides)
    return Finding(**defaults)


def _insert_corroborating(db: Session, restaurant_id: int,
                           agent_name: str, category: str,
                           optimization_impact: str = "revenue_increase"):
    """Insert a recent finding from another agent for corroboration."""
    af = AgentFinding(
        restaurant_id=restaurant_id,
        agent_name=agent_name,
        category=category,
        urgency="this_week",
        optimization_impact=optimization_impact,
        finding_text=f"Corroborating signal from {agent_name}",
        action_text="Corroborating action text that is long enough",
        confidence_score=70,
        status="pending",
        created_at=datetime.now() - timedelta(days=1),
    )
    db.add(af)
    db.flush()


def _insert_sent_finding(db: Session, restaurant_id: int,
                          agent_name: str, category: str,
                          action_text: str):
    """Insert a recently-sent finding for dedup testing."""
    af = AgentFinding(
        restaurant_id=restaurant_id,
        agent_name=agent_name,
        category=category,
        urgency="this_week",
        optimization_impact="revenue_increase",
        finding_text="Previously sent finding",
        action_text=action_text,
        confidence_score=70,
        status="sent",
        sent_at=datetime.now() - timedelta(days=2),
        created_at=datetime.now() - timedelta(days=2),
    )
    db.add(af)
    db.flush()


def _insert_restaurant_profile(db: Session, restaurant_id: int,
                                non_negotiables: list[str] = None):
    """Insert a RestaurantProfile for identity filter testing."""
    profile = RestaurantProfile(
        restaurant_id=restaurant_id,
        city="Kolkata",
        non_negotiables=json.dumps(non_negotiables or []),
    )
    db.add(profile)
    db.flush()


# ===========================================================================
# STAGE 1: SIGNIFICANCE — 6 tests
# ===========================================================================

class TestSignificance:
    """6 golden test cases for Stage 1."""

    def test_sig_01_passes_all_checks(self, db, restaurant_id):
        """Revenue finding with 10 data points, 20% deviation, z=2.0 → PASS."""
        finding = _make_finding(
            restaurant_id=restaurant_id,
            evidence_data={
                "data_points_count": 10,
                "deviation_pct": 0.20,
                "baseline_mean": 50000,
                "baseline_std": 5000,
                "current_value": 40000,  # z = |40000-50000|/5000 = 2.0
            },
        )
        passed, score, reason = significance_check(finding, restaurant_id)
        assert passed is True
        assert reason == "significant"

    def test_sig_02_insufficient_data_points(self, db, restaurant_id):
        """Only 2 data points (< 3 minimum) → FAIL."""
        finding = _make_finding(
            restaurant_id=restaurant_id,
            evidence_data={
                "data_points_count": 2,
                "deviation_pct": 0.25,
            },
        )
        passed, score, reason = significance_check(finding, restaurant_id)
        assert passed is False
        assert reason == "insufficient_data_points"

    def test_sig_03_below_revenue_threshold(self, db, restaurant_id):
        """Revenue deviation 10% < 15% threshold → FAIL."""
        finding = _make_finding(
            restaurant_id=restaurant_id,
            category="revenue",
            evidence_data={
                "data_points_count": 10,
                "deviation_pct": 0.10,
            },
        )
        passed, score, reason = significance_check(finding, restaurant_id)
        assert passed is False
        assert reason == "below_significance_threshold"

    def test_sig_04_z_score_too_low(self, db, restaurant_id):
        """Deviation exceeds threshold but z-score = 1.0 < 1.5 → FAIL."""
        finding = _make_finding(
            restaurant_id=restaurant_id,
            evidence_data={
                "data_points_count": 10,
                "deviation_pct": 0.20,
                "baseline_mean": 50000,
                "baseline_std": 10000,
                "current_value": 40000,  # z = |40000-50000|/10000 = 1.0
            },
        )
        passed, score, reason = significance_check(finding, restaurant_id)
        assert passed is False
        assert reason == "z_score_below_threshold"

    def test_sig_05_menu_category_10pct_threshold(self, db, restaurant_id):
        """Menu category: 12% deviation exceeds 10% threshold → PASS."""
        finding = _make_finding(
            restaurant_id=restaurant_id,
            agent_name="maya",
            category="menu",
            evidence_data={
                "data_points_count": 8,
                "deviation_pct": 0.12,
                # No baseline stats → z-score check skipped
            },
        )
        passed, score, reason = significance_check(finding, restaurant_id)
        assert passed is True
        assert reason == "significant"

    def test_sig_06_stock_category_30pct_threshold(self, db, restaurant_id):
        """Stock category: 25% deviation below 30% threshold → FAIL."""
        finding = _make_finding(
            restaurant_id=restaurant_id,
            agent_name="arjun",
            category="stock",
            evidence_data={
                "data_points_count": 7,
                "deviation_pct": 0.25,
            },
        )
        passed, score, reason = significance_check(finding, restaurant_id)
        assert passed is False
        assert reason == "below_significance_threshold"


# ===========================================================================
# STAGE 2: CORROBORATION — 4 tests
# ===========================================================================

class TestCorroboration:
    """4 golden test cases for Stage 2."""

    def test_corr_01_aligned_agent_corroborates(self, db, restaurant_id):
        """Ravi finding corroborated by Arjun (stock) → PASS."""
        _insert_corroborating(db, restaurant_id, "arjun", "stock")

        finding = _make_finding(restaurant_id=restaurant_id)
        passed, agents, reason = corroboration_check(finding, restaurant_id, db)
        assert passed is True
        assert "arjun" in agents
        assert reason == "corroborated"

    def test_corr_02_no_corroboration(self, db, restaurant_id):
        """Ravi finding with no aligned agent findings → FAIL."""
        finding = _make_finding(restaurant_id=restaurant_id)
        passed, agents, reason = corroboration_check(finding, restaurant_id, db)
        assert passed is False
        assert agents == []
        assert reason == "no_corroboration"

    def test_corr_03_solo_high_urgency_exception(self, db, restaurant_id):
        """Immediate urgency + confidence 85 >= 80 → PASS (solo exception)."""
        finding = _make_finding(
            restaurant_id=restaurant_id,
            urgency=Urgency.IMMEDIATE,
            confidence_score=85,
        )
        passed, agents, reason = corroboration_check(finding, restaurant_id, db)
        assert passed is True
        assert agents == []
        assert reason == "solo_high_urgency_exception"

    def test_corr_04_contradiction_detected(self, db, restaurant_id):
        """Ravi (revenue_increase) contradicted by Arjun (risk_mitigation) → FAIL + escalate."""
        _insert_corroborating(
            db, restaurant_id, "arjun", "stock",
            optimization_impact="risk_mitigation",
        )

        finding = _make_finding(
            restaurant_id=restaurant_id,
            optimization_impact=OptimizationImpact.REVENUE_INCREASE,
        )
        passed, agents, reason = corroboration_check(finding, restaurant_id, db)
        assert passed is False
        assert reason == "contradiction_detected"


# ===========================================================================
# STAGE 3: ACTIONABILITY — 5 tests
# ===========================================================================

class TestActionability:
    """5 golden test cases for Stage 3."""

    def test_act_01_passes_all_checks(self, db, restaurant_id):
        """Well-formed finding with action, deadline, no dupes → PASS."""
        finding = _make_finding(restaurant_id=restaurant_id)
        passed, reason, reworked = actionability_check(finding, restaurant_id, db)
        assert passed is True
        assert reason == "actionable"
        assert reworked is None

    def test_act_02_action_text_too_short(self, db, restaurant_id):
        """Action text < 20 chars → FAIL."""
        finding = _make_finding(
            restaurant_id=restaurant_id,
            action_text="Do something",  # 12 chars
        )
        passed, reason, reworked = actionability_check(finding, restaurant_id, db)
        assert passed is False
        assert reason == "action_text_too_vague"

    def test_act_03_no_deadline(self, db, restaurant_id):
        """Missing action_deadline → FAIL."""
        finding = _make_finding(
            restaurant_id=restaurant_id,
            action_deadline=None,
        )
        passed, reason, reworked = actionability_check(finding, restaurant_id, db)
        assert passed is False
        assert reason == "no_deadline"

    def test_act_04_duplicate_recent_finding(self, db, restaurant_id):
        """Action text Jaccard > 0.6 with recently sent finding → FAIL."""
        _insert_sent_finding(
            db, restaurant_id, "ravi", "revenue",
            "Investigate the revenue drop and launch a Tuesday lunch promo targeting regulars",
        )

        finding = _make_finding(restaurant_id=restaurant_id)
        passed, reason, reworked = actionability_check(finding, restaurant_id, db)
        assert passed is False
        assert reason == "duplicate_of_recent_finding"

    def test_act_05_identity_conflict_reworks(self, db, restaurant_id):
        """Action conflicts with non_negotiable → PASS with reworked action."""
        _insert_restaurant_profile(
            db, restaurant_id,
            non_negotiables=["never use lower quality ingredients"],
        )

        finding = _make_finding(
            restaurant_id=restaurant_id,
            action_text="Switch to lower quality ingredients to save costs on the Dal Makhani",
        )

        # Patch Claude call to use keyword fallback
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}, clear=False):
            passed, reason, reworked = actionability_check(
                finding, restaurant_id, db
            )

        assert passed is True
        assert reason == "identity_conflict_reworked"
        assert reworked is not None
        assert "Review against policy" in reworked


# ===========================================================================
# INTEGRATION: Full QC Pipeline
# ===========================================================================

class TestQualityCouncilIntegration:
    """End-to-end council tests verifying the 3-stage pipeline."""

    def test_full_pass_returns_true(self, db, restaurant_id):
        """Finding passing all 3 stages → (True, reason, enriched)."""
        _insert_corroborating(db, restaurant_id, "arjun", "stock")

        finding = _make_finding(restaurant_id=restaurant_id)
        qc = QualityCouncil(db_session=db, readonly_db=db)
        passed, reason, enriched = qc.vet(finding, restaurant_id=restaurant_id)

        assert passed is True
        assert "all_stages_passed" in reason
        assert enriched.agent_name == "ravi"

    def test_significance_fail_rejects(self, db, restaurant_id):
        """Significance failure → (False, reason, finding)."""
        finding = _make_finding(
            restaurant_id=restaurant_id,
            evidence_data={"data_points_count": 1, "deviation_pct": 0.05},
        )
        qc = QualityCouncil(db_session=db, readonly_db=db)
        passed, reason, enriched = qc.vet(finding, restaurant_id=restaurant_id)

        assert passed is False
        assert "significance_failed" in reason

    def test_corroboration_fail_holds(self, db, restaurant_id):
        """No corroboration → HOLD → (False, reason, finding)."""
        finding = _make_finding(restaurant_id=restaurant_id)
        qc = QualityCouncil(db_session=db, readonly_db=db)
        passed, reason, enriched = qc.vet(finding, restaurant_id=restaurant_id)

        assert passed is False
        assert "corroboration_failed" in reason

    def test_max_hold_cycles_rejects(self, db, restaurant_id):
        """Finding held 3 times → auto-reject on 4th attempt."""
        # Insert a held finding with hold_count=3
        af = AgentFinding(
            restaurant_id=restaurant_id,
            agent_name="ravi",
            category="revenue",
            urgency="this_week",
            optimization_impact="revenue_increase",
            finding_text="Held finding",
            action_text="Some action that keeps getting held repeatedly",
            confidence_score=70,
            status="held",
            hold_count=3,
            created_at=datetime.now() - timedelta(hours=12),
        )
        db.add(af)
        db.flush()

        finding = _make_finding(restaurant_id=restaurant_id)
        qc = QualityCouncil(db_session=db, readonly_db=db)
        passed, reason, enriched = qc.vet(finding, restaurant_id=restaurant_id)

        assert passed is False
        assert "max_hold_cycles_exceeded" in reason

    def test_persists_to_db(self, db, restaurant_id):
        """Council persists finding with QC metadata."""
        _insert_corroborating(db, restaurant_id, "arjun", "stock")

        finding = _make_finding(restaurant_id=restaurant_id)
        qc = QualityCouncil(db_session=db, readonly_db=db)
        qc.vet(finding, restaurant_id=restaurant_id)

        stored = (
            db.query(AgentFinding)
            .filter(
                AgentFinding.restaurant_id == restaurant_id,
                AgentFinding.agent_name == "ravi",
            )
            .order_by(AgentFinding.id.desc())
            .first()
        )
        assert stored is not None
        assert stored.significance_passed is True
        assert stored.status == "approved"

    def test_vet_batch(self, db, restaurant_id):
        """vet_batch processes multiple findings."""
        _insert_corroborating(db, restaurant_id, "arjun", "stock")

        findings = [
            _make_finding(restaurant_id=restaurant_id),
            _make_finding(
                restaurant_id=restaurant_id,
                evidence_data={"data_points_count": 1, "deviation_pct": 0.01},
            ),
        ]
        qc = QualityCouncil(db_session=db, readonly_db=db)
        results = qc.vet_batch(findings, restaurant_id=restaurant_id)

        assert len(results) == 2
        assert results[0][0] is True   # first passes
        assert results[1][0] is False  # second fails significance
