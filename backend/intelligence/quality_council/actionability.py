"""Quality Council Stage 3: Actionability + Identity Filter.

Validates that a finding is actionable and safe to send:
1. Has specific action text (>= 20 chars)
2. Has deadline (not already passed)
3. Not a duplicate of recent sent finding (Jaccard > 0.6 in last 7 days)
4. Identity filter: check non_negotiables via Claude call (keyword fallback)
5. Rework findings that conflict with identity — never pass them raw

Returns: (passed: bool, reason: str, reworked_action: str | None)
"""

import json
import logging
import os
from datetime import date, datetime, timedelta
from typing import Optional

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


def _load_non_negotiables(
    restaurant_id: int, db: Session
) -> list[str]:
    """Load non_negotiables from restaurant profile."""
    try:
        profile = (
            db.query(RestaurantProfile)
            .filter_by(restaurant_id=restaurant_id)
            .first()
        )
        if not profile or not profile.non_negotiables:
            return []

        non_negs = profile.non_negotiables
        # Handle SQLite TEXT storage (JSON string) vs Postgres ARRAY
        if isinstance(non_negs, str):
            try:
                non_negs = json.loads(non_negs)
            except (json.JSONDecodeError, TypeError):
                return []
        return list(non_negs) if non_negs else []
    except Exception as e:
        logger.debug("Could not load non_negotiables: %s", e)
        return []


def _check_identity_claude(
    action_text: str, non_negotiables: list[str]
) -> tuple[bool, Optional[str]]:
    """Use Claude to check if action_text conflicts with non_negotiables.

    Returns (has_conflict, reworked_action_text).
    If no conflict, reworked is None.
    If conflict, reworked contains a modified action that respects identity.
    Falls back to keyword matching if Claude unavailable.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return _check_identity_keywords(action_text, non_negotiables)

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        prompt = (
            "You are a restaurant intelligence quality filter.\n\n"
            f"Restaurant owner's non-negotiables (things they will NEVER compromise on):\n"
            + "\n".join(f"- {nn}" for nn in non_negotiables)
            + f"\n\nProposed action for the owner:\n\"{action_text}\"\n\n"
            "Does this action conflict with any non-negotiable? "
            "If YES: respond with JSON {\"conflict\": true, \"conflicting_rule\": \"<which one>\", "
            "\"reworked_action\": \"<rewritten action that achieves the same goal without violating the non-negotiable>\"}\n"
            "If NO: respond with JSON {\"conflict\": false}\n"
            "Respond ONLY with valid JSON, no markdown."
        )

        response = client.messages.create(
            model="claude-sonnet-4-6-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )

        result_text = response.content[0].text.strip()
        result = json.loads(result_text)

        if result.get("conflict"):
            reworked = result.get("reworked_action", action_text)
            return True, reworked
        return False, None

    except Exception as e:
        logger.warning("Claude identity check failed, falling back to keywords: %s", e)
        return _check_identity_keywords(action_text, non_negotiables)


def _check_identity_keywords(
    action_text: str, non_negotiables: list[str]
) -> tuple[bool, Optional[str]]:
    """Keyword-based fallback for identity conflict detection.

    Returns (has_conflict, reworked_action_text).
    Keyword check: if >50% of a non-negotiable's tokens appear in the action.
    """
    action_lower = action_text.lower()
    action_tokens = set(action_lower.split())

    for non_neg in non_negotiables:
        non_neg_tokens = set(non_neg.lower().split())
        if not non_neg_tokens:
            continue
        overlap = non_neg_tokens & action_tokens
        if len(overlap) > len(non_neg_tokens) * 0.5:
            # Conflict detected — prepend review note as rework
            reworked = (
                f"[Review against policy: '{non_neg}'] {action_text}"
            )
            return True, reworked

    return False, None


def actionability_check(
    finding: Finding, restaurant_id: int, db: Session
) -> tuple[bool, str, Optional[str]]:
    """Stage 3: Is this finding actionable and safe to send?

    Args:
        finding: The Finding to evaluate.
        restaurant_id: Restaurant context.
        db: Database session.

    Returns:
        (passed, reason, reworked_action_text)
        reworked_action_text is non-None only when identity rework occurred.
    """
    # Check 1: Has specific action text
    if not finding.action_text or len(finding.action_text) < MIN_ACTION_LENGTH:
        return False, "action_text_too_vague", None

    # Check 2: Has deadline
    if not finding.action_deadline:
        return False, "no_deadline", None

    # Check 3: Has estimated impact
    if finding.estimated_impact_paisa is None:
        return False, "no_estimated_impact", None

    # Check 4: Deadline not already passed
    if finding.action_deadline < date.today():
        return False, "deadline_already_passed", None

    # Check 4: Not a duplicate of recent sent finding
    cutoff = datetime.now() - timedelta(days=DEDUP_WINDOW_DAYS)
    try:
        recent_sent = (
            db.query(AgentFinding)
            .filter(
                AgentFinding.restaurant_id == restaurant_id,
                AgentFinding.agent_name == finding.agent_name,
                AgentFinding.category == finding.category,
                AgentFinding.status.in_(["sent", "approved"]),
                AgentFinding.created_at >= cutoff,
            )
            .all()
        )

        for sent in recent_sent:
            if sent.action_text:
                similarity = _jaccard_similarity(finding.action_text, sent.action_text)
                if similarity > JACCARD_THRESHOLD:
                    return False, "duplicate_of_recent_finding", None
    except Exception as e:
        logger.debug("Dedup check failed: %s", e)

    # Check 5: Identity filter — non_negotiables
    non_negotiables = _load_non_negotiables(restaurant_id, db)
    if non_negotiables:
        has_conflict, reworked = _check_identity_claude(
            finding.action_text, non_negotiables
        )
        if has_conflict:
            # Finding is reworked, not rejected — passes with modified action
            return True, "identity_conflict_reworked", reworked

    return True, "actionable", None
