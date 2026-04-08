"""Quality Council Stage 1: Significance Check.

Validates that a finding is statistically meaningful:
1. Minimum 3 data points
2. Deviation exceeds category-specific threshold
3. Z-score >= 1.5 against baseline (when data available)

Category thresholds (from PRD):
  revenue  — 15%
  menu     — 10%
  stock    — 30%
  customer — 15%

Returns: (passed: bool, score: float, reason: str)
"""

import logging

from intelligence.agents.base_agent import Finding

logger = logging.getLogger("ytip.quality_council.significance")

# Category-specific deviation thresholds
DEVIATION_THRESHOLDS = {
    "revenue": 0.15,   # 15%
    "menu": 0.10,      # 10% CM change
    "stock": 0.30,     # 30% waste ratio
    "customer": 0.15,  # 15% retention change
    "cultural": 0.15,  # 15% default
    "competition": 0.15,
}

MIN_DATA_POINTS = 3
MIN_Z_SCORE = 1.5


def significance_check(
    finding: Finding, restaurant_id: int
) -> tuple[bool, float, str]:
    """Stage 1: Is this finding statistically significant?

    Args:
        finding: The Finding to evaluate.
        restaurant_id: Restaurant context (reserved for per-restaurant tuning).

    Returns:
        (passed, score, reason) where score is the deviation_pct or z_score.
    """
    evidence = finding.evidence_data or {}

    # Check 1: Minimum data points
    data_points = evidence.get("data_points_count", 0)
    if data_points < MIN_DATA_POINTS:
        return False, 0.0, "insufficient_data_points"

    # Check 2: Deviation magnitude by category
    deviation_pct = abs(evidence.get("deviation_pct", 0))
    threshold = DEVIATION_THRESHOLDS.get(finding.category, 0.15)

    if deviation_pct < threshold:
        return False, deviation_pct, "below_significance_threshold"

    # Check 3: Z-score (when baseline stats available)
    baseline_std = evidence.get("baseline_std")
    baseline_mean = evidence.get("baseline_mean")
    current_value = evidence.get("current_value")

    if (baseline_std is not None and baseline_mean is not None
            and current_value is not None and baseline_std > 0):
        z_score = abs(current_value - baseline_mean) / baseline_std
        if z_score < MIN_Z_SCORE:
            return False, z_score, "z_score_below_threshold"

    return True, deviation_pct, "significant"
