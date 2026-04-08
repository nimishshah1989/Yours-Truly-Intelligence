"""Quality Council — 3-stage vetting orchestrator.

Every Finding must pass through:
  Stage 1: Significance — is it statistically meaningful?
  Stage 2: Corroboration — does another agent point the same direction?
  Stage 3: Actionability — is it actionable, non-duplicate, identity-safe?

Verdicts:
  SEND   — all 3 stages pass → (True, reason, enriched_finding)
  HOLD   — significance passes but corr/act fails → (False, reason, finding)
  REJECT — significance fails OR max hold cycles exceeded → (False, reason, finding)

Hold cycle tracking: max 3 holds before auto-reject.
Nothing bypasses Quality Council. Ever.
"""

import copy
import json
import logging
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from intelligence.agents.base_agent import Finding
from intelligence.models import AgentFinding
from intelligence.quality_council.significance import significance_check
from intelligence.quality_council.corroboration import corroboration_check
from intelligence.quality_council.actionability import actionability_check

logger = logging.getLogger("ytip.quality_council")

MAX_HOLD_CYCLES = 3


class QualityCouncil:
    """Orchestrates the 3-stage vetting pipeline."""

    def __init__(self, db_session: Session, readonly_db: Session = None):
        self.db = db_session
        self.rodb = readonly_db or db_session

    def vet(
        self, finding: Finding, restaurant_id: int = None
    ) -> tuple[bool, str, Finding]:
        """Run a single finding through all 3 stages.

        Args:
            finding: The Finding to evaluate.
            restaurant_id: Override restaurant_id (uses finding.restaurant_id
                if not provided).

        Returns:
            (passed, reason, enriched_finding)
            passed: True if verdict is SEND, False otherwise.
            reason: Human-readable explanation of the verdict.
            enriched_finding: Copy of finding, possibly with reworked action_text.
        """
        rid = restaurant_id or finding.restaurant_id
        enriched = copy.copy(finding)

        # Check hold cycle count for similar existing held findings
        hold_count = self._get_hold_count(finding, rid)
        if hold_count >= MAX_HOLD_CYCLES:
            reason = f"max_hold_cycles_exceeded ({hold_count} holds)"
            self._persist(finding, rid, "REJECT", reason, None)
            return False, reason, enriched

        # Stage 1: Significance
        sig_passed, sig_score, sig_reason = significance_check(finding, rid)

        if not sig_passed:
            reason = f"significance_failed: {sig_reason}"
            self._persist(finding, rid, "REJECT", reason, {
                "significance": {"passed": False, "score": sig_score, "reason": sig_reason},
            })
            return False, reason, enriched

        # Stage 2: Corroboration
        corr_passed, corr_agents, corr_reason = corroboration_check(
            finding, rid, self.rodb
        )

        if not corr_passed:
            verdict = "HOLD"
            reason = f"corroboration_failed: {corr_reason}"
            self._persist(finding, rid, verdict, reason, {
                "significance": {"passed": True, "score": sig_score, "reason": sig_reason},
                "corroboration": {"passed": False, "agents": corr_agents, "reason": corr_reason},
            })
            return False, reason, enriched

        # Stage 3: Actionability
        act_passed, act_reason, reworked_action = actionability_check(
            finding, rid, self.db
        )

        if not act_passed:
            verdict = "HOLD"
            reason = f"actionability_failed: {act_reason}"
            self._persist(finding, rid, verdict, reason, {
                "significance": {"passed": True, "score": sig_score, "reason": sig_reason},
                "corroboration": {"passed": True, "agents": corr_agents, "reason": corr_reason},
                "actionability": {"passed": False, "reason": act_reason},
            })
            return False, reason, enriched

        # All stages passed — SEND
        if reworked_action:
            enriched.action_text = reworked_action

        reason = f"all_stages_passed"
        if act_reason == "identity_conflict_reworked":
            reason = "passed_with_identity_rework"

        self._persist(enriched, rid, "SEND", reason, {
            "significance": {"passed": True, "score": sig_score, "reason": sig_reason},
            "corroboration": {"passed": True, "agents": corr_agents, "reason": corr_reason},
            "actionability": {"passed": True, "reason": act_reason},
        })
        return True, reason, enriched

    def vet_batch(
        self, findings: list[Finding], restaurant_id: int = None
    ) -> list[tuple[bool, str, Finding]]:
        """Run multiple findings through the council."""
        return [self.vet(f, restaurant_id) for f in findings]

    def _get_hold_count(self, finding: Finding, restaurant_id: int) -> int:
        """Check how many times a similar finding has been held."""
        try:
            held = (
                self.rodb.query(AgentFinding)
                .filter(
                    AgentFinding.restaurant_id == restaurant_id,
                    AgentFinding.agent_name == finding.agent_name,
                    AgentFinding.category == finding.category,
                    AgentFinding.status == "held",
                )
                .order_by(AgentFinding.created_at.desc())
                .first()
            )
            if held:
                return held.hold_count or 0
            return 0
        except Exception as e:
            logger.debug("Hold count check failed: %s", e)
            return 0

    @staticmethod
    def _sanitize_evidence(data) -> dict:
        """Convert Decimal/non-serializable values for JSONB storage."""
        if not data:
            return data
        # Round-trip through JSON with a custom encoder
        class _Encoder(json.JSONEncoder):
            def default(self, o):
                if isinstance(o, Decimal):
                    return float(o)
                return super().default(o)
        try:
            return json.loads(json.dumps(data, cls=_Encoder))
        except (TypeError, ValueError):
            return {"raw": str(data)}

    def _persist(
        self, finding: Finding, restaurant_id: int,
        verdict: str, reason: str, stage_results: dict = None
    ) -> None:
        """Save finding with QC metadata to agent_findings table."""
        try:
            status_map = {
                "SEND": "approved",
                "HOLD": "held",
                "REJECT": "rejected",
            }

            stage_results = stage_results or {}
            sig = stage_results.get("significance", {})
            corr = stage_results.get("corroboration", {})
            act = stage_results.get("actionability", {})

            # Compute hold_count
            hold_count = 0
            if verdict == "HOLD":
                hold_count = self._get_hold_count(finding, restaurant_id) + 1

            corr_agents = corr.get("agents", [])
            corr_agents_value = corr_agents if corr_agents else None

            af = AgentFinding(
                restaurant_id=restaurant_id,
                agent_name=finding.agent_name,
                category=finding.category,
                urgency=(
                    finding.urgency.value
                    if hasattr(finding.urgency, "value")
                    else str(finding.urgency)
                ),
                optimization_impact=(
                    finding.optimization_impact.value
                    if hasattr(finding.optimization_impact, "value")
                    else str(finding.optimization_impact)
                ),
                finding_text=finding.finding_text,
                action_text=finding.action_text,
                action_deadline=finding.action_deadline,
                evidence_data=self._sanitize_evidence(finding.evidence_data),
                confidence_score=finding.confidence_score,
                estimated_impact_size=(
                    finding.estimated_impact_size.value
                    if finding.estimated_impact_size
                    and hasattr(finding.estimated_impact_size, "value")
                    else None
                ),
                estimated_impact_paisa=finding.estimated_impact_paisa,
                significance_passed=sig.get("passed"),
                significance_score=sig.get("score"),
                corroboration_passed=corr.get("passed"),
                corroborating_agents=corr_agents_value,
                actionability_passed=act.get("passed"),
                identity_conflict="identity_conflict" in reason,
                qc_notes=reason,
                status=status_map.get(verdict, "pending"),
                hold_count=hold_count,
            )
            self.db.add(af)
            self.db.flush()
        except Exception as e:
            logger.warning("Failed to persist finding: %s", e)
