"""Tests for Quality Council orchestrator."""

import pytest
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from intelligence.agents.base_agent import Finding, Urgency, OptimizationImpact
from intelligence.quality_council.council import QualityCouncil
from intelligence.models import AgentFinding


def _make_finding(**overrides) -> Finding:
    defaults = {
        "agent_name": "ravi",
        "restaurant_id": 1,
        "category": "revenue",
        "urgency": Urgency.THIS_WEEK,
        "optimization_impact": OptimizationImpact.REVENUE_INCREASE,
        "finding_text": "Revenue declined 20% vs baseline over past 5 days",
        "action_text": "Investigate the revenue drop and launch a Tuesday lunch promo",
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
    }
    defaults.update(overrides)
    return Finding(**defaults)


def _insert_corroborating_finding(db: Session, restaurant_id: int,
                                   agent_name: str, category: str):
    af = AgentFinding(
        restaurant_id=restaurant_id,
        agent_name=agent_name,
        category=category,
        urgency="this_week",
        optimization_impact="revenue_increase",
        finding_text=f"Corroborating from {agent_name}",
        action_text="Corroborating action text for alignment",
        confidence_score=70,
        status="pending",
        created_at=datetime.now() - timedelta(days=1),
    )
    db.add(af)
    db.flush()


class TestQualityCouncil:

    def test_full_pass_returns_send(self, db, restaurant_id):
        """Finding passing all 3 stages gets SEND verdict."""
        _insert_corroborating_finding(db, restaurant_id, "arjun", "stock")

        finding = _make_finding(restaurant_id=restaurant_id)
        qc = QualityCouncil(db)
        result = qc.vet(finding)

        assert result["verdict"] == "SEND"
        assert result["significance"]["passed"] is True
        assert result["corroboration"]["passed"] is True
        assert result["actionability"]["passed"] is True

    def test_significance_fail_returns_reject(self, db, restaurant_id):
        """Finding failing significance gets REJECT."""
        finding = _make_finding(
            restaurant_id=restaurant_id,
            evidence_data={"data_points_count": 1, "deviation_pct": 0.05},
        )
        qc = QualityCouncil(db)
        result = qc.vet(finding)

        assert result["verdict"] == "REJECT"
        assert result["significance"]["passed"] is False

    def test_corroboration_fail_returns_hold(self, db, restaurant_id):
        """Finding passing significance but failing corroboration gets HOLD."""
        finding = _make_finding(restaurant_id=restaurant_id)
        qc = QualityCouncil(db)
        result = qc.vet(finding)

        assert result["verdict"] == "HOLD"
        assert result["significance"]["passed"] is True
        assert result["corroboration"]["passed"] is False

    def test_actionability_fail_returns_hold(self, db, restaurant_id):
        """Finding passing sig+corr but failing actionability gets HOLD."""
        _insert_corroborating_finding(db, restaurant_id, "arjun", "stock")

        finding = _make_finding(
            restaurant_id=restaurant_id,
            action_deadline=None,  # fails actionability
        )
        qc = QualityCouncil(db)
        result = qc.vet(finding)

        assert result["verdict"] == "HOLD"
        assert result["actionability"]["passed"] is False

    def test_persists_to_agent_findings(self, db, restaurant_id):
        """Council should persist finding with QC metadata to agent_findings."""
        _insert_corroborating_finding(db, restaurant_id, "arjun", "stock")

        finding = _make_finding(restaurant_id=restaurant_id)
        qc = QualityCouncil(db)
        result = qc.vet(finding)

        # Check it was persisted
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
        assert stored.corroboration_passed is True
        assert stored.actionability_passed is True
        assert stored.status == "approved"

    def test_vet_batch(self, db, restaurant_id):
        """vet_batch processes multiple findings and returns results list."""
        _insert_corroborating_finding(db, restaurant_id, "arjun", "stock")

        findings = [
            _make_finding(restaurant_id=restaurant_id),
            _make_finding(
                restaurant_id=restaurant_id,
                evidence_data={"data_points_count": 1, "deviation_pct": 0.01},
            ),
        ]
        qc = QualityCouncil(db)
        results = qc.vet_batch(findings)

        assert len(results) == 2
        assert results[0]["verdict"] == "SEND"
        assert results[1]["verdict"] == "REJECT"
