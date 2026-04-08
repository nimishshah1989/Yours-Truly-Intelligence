"""Quality Council Stage 2: Corroboration Check.

Verifies that a finding is supported by signals from other agents:
1. Look for findings from other agents in the last 7 days
2. Check if any align (same direction, related domain)
3. Solo high-urgency exception: urgency=immediate AND confidence >= 80
4. Contradiction detection: aligned agents pointing opposite directions → escalate

Returns: (passed: bool, corroborating_agents: list[str], reason: str)
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from intelligence.agents.base_agent import Finding, Urgency
from intelligence.models import AgentFinding

logger = logging.getLogger("ytip.quality_council.corroboration")

CORROBORATION_WINDOW_DAYS = 7
SOLO_MIN_CONFIDENCE = 80

# Which (category, agent) pairs align with each other
ALIGNMENT_MAP: dict[tuple[str, str], list[tuple[str, str]]] = {
    ("revenue", "ravi"): [("stock", "arjun"), ("customer", "sara")],
    ("menu", "maya"): [("stock", "arjun"), ("competition", "kiran")],
    ("cultural", "priya"): [("revenue", "ravi"), ("stock", "arjun")],
    ("competition", "kiran"): [("revenue", "ravi"), ("customer", "sara")],
    ("stock", "arjun"): [("revenue", "ravi"), ("menu", "maya")],
    ("customer", "sara"): [("revenue", "ravi"), ("competition", "kiran")],
}


def _urgency_value(urgency) -> str:
    """Normalise urgency to string regardless of enum or raw string."""
    if hasattr(urgency, "value"):
        return urgency.value
    return str(urgency).lower()


def _impacts_contradict(impact_a, impact_b) -> bool:
    """Heuristic: two findings contradict if one says opportunity/revenue_increase
    while the other says risk_mitigation on an aligned category pair."""
    a = impact_a.value if hasattr(impact_a, "value") else str(impact_a)
    b = impact_b.value if hasattr(impact_b, "value") else str(impact_b)
    positive = {"revenue_increase", "opportunity"}
    negative = {"risk_mitigation"}
    return (a in positive and b in negative) or (a in negative and b in positive)


def signals_align(f1: Finding, f2) -> bool:
    """Check if two findings point in the same direction.

    f2 can be a Finding or an AgentFinding ORM object.
    """
    f1_key = (f1.category, f1.agent_name)

    f2_cat = getattr(f2, "category", "")
    f2_agent = getattr(f2, "agent_name", "")
    f2_key = (f2_cat, f2_agent)

    # Same agent never aligns with itself
    if f1.agent_name == f2_agent:
        return False

    aligned_pairs = ALIGNMENT_MAP.get(f1_key, [])
    return f2_key in aligned_pairs


def corroboration_check(
    finding: Finding, restaurant_id: int, db: Session
) -> tuple[bool, list[str], str]:
    """Stage 2: Is this finding corroborated by another agent?

    Args:
        finding: The Finding to evaluate.
        restaurant_id: Restaurant context.
        db: Database session for querying recent findings.

    Returns:
        (passed, corroborating_agents, reason)
    """
    cutoff = datetime.now() - timedelta(days=CORROBORATION_WINDOW_DAYS)

    # Get recent findings from other agents
    recent_findings = (
        db.query(AgentFinding)
        .filter(
            AgentFinding.restaurant_id == restaurant_id,
            AgentFinding.agent_name != finding.agent_name,
            AgentFinding.created_at >= cutoff,
        )
        .all()
    )

    corroborating = []
    contradictions = []

    for rf in recent_findings:
        if signals_align(finding, rf):
            # Check for contradiction: aligned agent but opposite impact
            if _impacts_contradict(finding.optimization_impact, rf.optimization_impact):
                contradictions.append(rf.agent_name)
            else:
                corroborating.append(rf.agent_name)

    # Contradictions escalate — hold both findings for review
    if contradictions and not corroborating:
        unique_contradicting = list(set(contradictions))
        return False, unique_contradicting, "contradiction_detected"

    if corroborating:
        unique_agents = list(set(corroborating))
        return True, unique_agents, "corroborated"

    # Solo high-urgency exception: immediate + confidence >= 80
    urgency_str = _urgency_value(finding.urgency)
    if urgency_str == "immediate" and finding.confidence_score >= SOLO_MIN_CONFIDENCE:
        return True, [], "solo_high_urgency_exception"

    return False, [], "no_corroboration"
