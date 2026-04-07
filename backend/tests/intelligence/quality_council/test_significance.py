"""Tests for Quality Council Stage 1: Significance Check."""

import pytest
from datetime import date, timedelta

from intelligence.agents.base_agent import Finding, Urgency, OptimizationImpact
from intelligence.quality_council.significance import significance_check


def _make_finding(**overrides) -> Finding:
    """Build a Finding with sensible defaults, overridable per test."""
    defaults = {
        "agent_name": "ravi",
        "restaurant_id": 1,
        "category": "revenue",
        "urgency": Urgency.THIS_WEEK,
        "optimization_impact": OptimizationImpact.REVENUE_INCREASE,
        "finding_text": "Revenue declined 20% vs baseline",
        "action_text": "Investigate the drop and run a promo this week",
        "evidence_data": {
            "data_points_count": 7,
            "deviation_pct": 0.20,
            "baseline_mean": 50000,
            "baseline_std": 5000,
            "current_value": 40000,
        },
        "confidence_score": 70,
        "action_deadline": date.today() + timedelta(days=7),
    }
    defaults.update(overrides)
    return Finding(**defaults)


class TestSignificanceCheck:
    """Stage 1: significance_check(finding, restaurant_id)."""

    def test_passes_when_all_criteria_met(self):
        """Finding with enough data points, high deviation, and z-score passes."""
        finding = _make_finding()
        passed, score, reason = significance_check(finding, 1)
        assert passed is True
        assert reason == "passed"

    def test_fails_insufficient_data_points(self):
        """< 3 data points -> fail."""
        finding = _make_finding(evidence_data={
            "data_points_count": 2,
            "deviation_pct": 0.30,
        })
        passed, score, reason = significance_check(finding, 1)
        assert passed is False
        assert reason == "insufficient_data_points"

    def test_fails_below_revenue_threshold(self):
        """Revenue deviation < 15% -> fail."""
        finding = _make_finding(
            category="revenue",
            evidence_data={
                "data_points_count": 10,
                "deviation_pct": 0.10,
            },
        )
        passed, score, reason = significance_check(finding, 1)
        assert passed is False
        assert reason == "below_significance_threshold"

    def test_menu_threshold_lower_than_revenue(self):
        """Menu category uses 10% threshold — 12% deviation passes."""
        finding = _make_finding(
            agent_name="maya",
            category="menu",
            evidence_data={
                "data_points_count": 10,
                "deviation_pct": 0.12,
            },
        )
        passed, score, reason = significance_check(finding, 1)
        assert passed is True

    def test_stock_threshold_higher(self):
        """Stock category uses 30% threshold — 25% deviation fails."""
        finding = _make_finding(
            agent_name="arjun",
            category="stock",
            evidence_data={
                "data_points_count": 10,
                "deviation_pct": 0.25,
            },
        )
        passed, score, reason = significance_check(finding, 1)
        assert passed is False
        assert reason == "below_significance_threshold"

    def test_stock_threshold_passes_at_35pct(self):
        """Stock category — 35% deviation passes."""
        finding = _make_finding(
            agent_name="arjun",
            category="stock",
            evidence_data={
                "data_points_count": 10,
                "deviation_pct": 0.35,
            },
        )
        passed, score, reason = significance_check(finding, 1)
        assert passed is True

    def test_fails_low_z_score(self):
        """Z-score < 1.5 -> not statistically significant."""
        finding = _make_finding(evidence_data={
            "data_points_count": 10,
            "deviation_pct": 0.20,
            "baseline_mean": 50000,
            "baseline_std": 20000,  # high std -> low z-score
            "current_value": 45000,
        })
        passed, score, reason = significance_check(finding, 1)
        assert passed is False
        assert reason == "not_statistically_significant"

    def test_passes_when_no_baseline_std(self):
        """If baseline_std not provided, skip z-score check."""
        finding = _make_finding(evidence_data={
            "data_points_count": 10,
            "deviation_pct": 0.20,
        })
        passed, score, reason = significance_check(finding, 1)
        assert passed is True

    def test_customer_threshold(self):
        """Customer category uses 15% threshold."""
        finding = _make_finding(
            agent_name="sara",
            category="customer",
            evidence_data={
                "data_points_count": 50,
                "deviation_pct": 0.16,
            },
        )
        passed, score, reason = significance_check(finding, 1)
        assert passed is True

    def test_returns_deviation_as_score(self):
        """Score returned should be the deviation_pct."""
        finding = _make_finding(evidence_data={
            "data_points_count": 10,
            "deviation_pct": 0.25,
        })
        passed, score, reason = significance_check(finding, 1)
        assert score == 0.25
