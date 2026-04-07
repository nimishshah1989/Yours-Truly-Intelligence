"""Quality Council Stage 3: Actionability + Identity Filter.

Validates that a finding is actionable and safe to send:
1. Has specific action text (> 20 chars)
2. Has deadline
3. Has estimated impact
4. Not a duplicate of recent sent finding (Jaccard > 0.6)
5. Deadline not already passed
6. Identity filter: check non_negotiables for conflicts

Returns: (passed: bool, reason: str)
"""

import logging
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from intelligence.agents.base_agent import Finding
from intelligence.models import AgentFinding, RestaurantProfile

logger = logging.getLogger("ytip.quality_council.actionability")

DEDUP_WINDOW_DAYS = 7
JACCARD_THRESHOLD = 0.6
MIN_ACTION_LENGTH = 20


def _tokenize(text: str) -> set[str]:
    """Simple word tokenizer for Jaccard similarity."""
    return set(text.lower().split())


def _jaccard_similarity(text_a: str, text_b: str) -> float:
    """Compute Jaccard similarity between two text strings."""
    tokens_a = _tokenize(text_a)
    tokens_b = _tokenize(text_b)
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


def actionability_check(
    finding: Finding, restaurant_id: int, db: Session
) -> tuple[bool, str]:
    """Stage 3: Is this finding actionable and safe to send?

    Args:
        finding: The Finding to evaluate.
        restaurant_id: Restaurant context.
        db: Database session.

    Returns:
        (passed, reason)
    """
    # Check 1: Has specific action text
    if not finding.action_text or len(finding.action_text) < MIN_ACTION_LENGTH:
        return False, "action_text_too_vague"

    # Check 2: Has deadline
    if not finding.action_deadline:
        return False, "no_deadline"

    # Check 3: Has estimated impact
    if finding.estimated_impact_paisa is None:
        return False, "no_estimated_impact"

    # Check 4: Deadline not already passed
    if finding.action_deadline < date.today():
        return False, "action_deadline_already_passed"

    # Check 5: Not a duplicate of recent sent finding
    cutoff = datetime.now() - timedelta(days=DEDUP_WINDOW_DAYS)
    recent_sent = (
        db.query(AgentFinding)
        .filter(
            AgentFinding.restaurant_id == restaurant_id,
            AgentFinding.agent_name == finding.agent_name,
            AgentFinding.category == finding.category,
            AgentFinding.status == "sent",
            AgentFinding.sent_at >= cutoff,
        )
        .all()
    )

    for sent in recent_sent:
        similarity = _jaccard_similarity(finding.action_text, sent.action_text)
        if similarity > JACCARD_THRESHOLD:
            return False, "duplicate_of_recent_finding"

    # Check 6: Identity filter — load non_negotiables
    identity_conflict = False
    try:
        profile = (
            db.query(RestaurantProfile)
            .filter_by(restaurant_id=restaurant_id)
            .first()
        )
        if profile and profile.non_negotiables:
            non_negs = profile.non_negotiables
            # Handle SQLite TEXT storage (JSON string) vs Postgres ARRAY
            if isinstance(non_negs, str):
                import json
                try:
                    non_negs = json.loads(non_negs)
                except (json.JSONDecodeError, TypeError):
                    non_negs = []

            action_lower = finding.action_text.lower()
            for non_neg in non_negs:
                # Simple keyword overlap check
                non_neg_tokens = set(non_neg.lower().split())
                action_tokens = set(action_lower.split())
                overlap = non_neg_tokens & action_tokens
                # If more than half of non-negotiable tokens appear in action
                if len(overlap) > len(non_neg_tokens) * 0.5:
                    identity_conflict = True
                    finding.action_text = (
                        f"[Note: review against policy '{non_neg}'] "
                        + finding.action_text
                    )
                    break
    except Exception as e:
        logger.debug("Could not check non-negotiables: %s", e)

    if identity_conflict:
        return True, "passed_with_identity_conflict"

    return True, "passed"
