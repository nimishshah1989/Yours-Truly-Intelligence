"""Quality Council Stage 2: Corroboration Check.

Verifies that a finding is supported by signals from other agents:
1. Look for findings from other agents in the last 7 days
2. Check if any align (same direction, related domain)
3. Solo exception: urgency=immediate AND confidence >= 85
   for competition/cultural categories

Returns: (passed: bool, corroborating_agents: list[str], reason: str)
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from intelligence.agents.base_agent import Finding
from intelligence.models import AgentFinding

logger = logging.getLogger("ytip.quality_council.corroboration")

CORROBORATION_WINDOW_DAYS = 7

# Which (category, agent) pairs align with each other
ALIGNMENT_MAP: dict[tuple[str, str], list[tuple[str, str]]] = {
    ("revenue", "ravi"): [("stock", "arjun"), ("customer", "sara")],
    ("menu", "maya"): [("stock", "arjun"), ("competition", "kiran")],
    ("cultural", "priya"): [("revenue", "ravi"), ("stock", "arjun")],
    ("competition", "kiran"): [("revenue", "ravi"), ("customer", "sara")],
    ("stock", "arjun"): [("revenue", "ravi"), ("menu", "maya")],
    ("customer", "sara"): [("revenue", "ravi"), ("competition", "kiran")],
}

# Categories eligible for solo exception
SOLO_EXCEPTION_CATEGORIES = {"competition", "cultural"}


def signals_align(f1: Finding, f2) -> bool:
    """Check if two findings point in the same direction.

    f2 can be a Finding or an AgentFinding ORM object.
    """
    f1_key = (f1.category, f1.agent_name)

    # Extract f2 attributes (works for both Finding and AgentFinding)
    f2_cat = f2.category if hasattr(f2, "category") else getattr(f2, "category", "")
    f2_agent = f2.agent_name if hasattr(f2, "agent_name") else getattr(f2, "agent_name", "")
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
    for rf in recent_findings:
        if signals_align(finding, rf):
            corroborating.append(rf.agent_name)

    if corroborating:
        # Deduplicate agent names
        unique_agents = list(set(corroborating))
        return True, unique_agents, "corroborated"

    # Solo exception: high-confidence immediate finding in eligible categories
    if (finding.urgency == "immediate"
            and finding.confidence_score >= 85
            and finding.category in SOLO_EXCEPTION_CATEGORIES):
        return True, [], "solo_high_confidence_exception"

    return False, [], "no_corroboration"
