"""Quality Council — 3-stage vetting orchestrator.

Every Finding must pass through:
  Stage 1: Significance — is it statistically meaningful?
  Stage 2: Corroboration — does another agent point the same direction?
  Stage 3: Actionability — is it actionable, non-duplicate, identity-safe?

Verdicts:
  SEND   — all 3 stages pass
  HOLD   — significance passes but corroboration or actionability fails
  REJECT — significance fails (not worth revisiting without more data)

Nothing bypasses Quality Council. Ever.
"""

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from intelligence.agents.base_agent import Finding
from intelligence.models import AgentFinding
from intelligence.quality_council.significance import significance_check
from intelligence.quality_council.corroboration import corroboration_check
from intelligence.quality_council.actionability import actionability_check

logger = logging.getLogger("ytip.quality_council")


class QualityCouncil:
    """Orchestrates the 3-stage vetting pipeline."""

    def __init__(self, db: Session):
        self.db = db

    def vet(self, finding: Finding) -> dict:
        """Run a single finding through all 3 stages.

        Returns a dict with:
          verdict: SEND | HOLD | REJECT
          significance: {passed, score, reason}
          corroboration: {passed, agents, reason}
          actionability: {passed, reason}
        """
        restaurant_id = finding.restaurant_id

        # Stage 1: Significance
        sig_passed, sig_score, sig_reason = significance_check(
            finding, restaurant_id
        )

        result = {
            "verdict": "REJECT",
            "significance": {
                "passed": sig_passed,
                "score": sig_score,
                "reason": sig_reason,
            },
            "corroboration": {"passed": False, "agents": [], "reason": "skipped"},
            "actionability": {"passed": False, "reason": "skipped"},
        }

        if not sig_passed:
            self._persist(finding, result)
            return result

        # Stage 2: Corroboration
        corr_passed, corr_agents, corr_reason = corroboration_check(
            finding, restaurant_id, self.db
        )

        result["corroboration"] = {
            "passed": corr_passed,
            "agents": corr_agents,
            "reason": corr_reason,
        }

        if not corr_passed:
            result["verdict"] = "HOLD"
            self._persist(finding, result)
            return result

        # Stage 3: Actionability
        act_passed, act_reason = actionability_check(
            finding, restaurant_id, self.db
        )

        result["actionability"] = {
            "passed": act_passed,
            "reason": act_reason,
        }

        if not act_passed:
            result["verdict"] = "HOLD"
            self._persist(finding, result)
            return result

        result["verdict"] = "SEND"
        self._persist(finding, result)
        return result

    def vet_batch(self, findings: list[Finding]) -> list[dict]:
        """Run multiple findings through the council."""
        return [self.vet(f) for f in findings]

    def _persist(self, finding: Finding, result: dict) -> None:
        """Save finding with QC metadata to agent_findings table."""
        try:
            status_map = {
                "SEND": "approved",
                "HOLD": "held",
                "REJECT": "rejected",
            }

            corr_agents = result["corroboration"].get("agents", [])

            af = AgentFinding(
                restaurant_id=finding.restaurant_id,
                agent_name=finding.agent_name,
                category=finding.category,
                urgency=finding.urgency.value if hasattr(finding.urgency, "value") else str(finding.urgency),
                optimization_impact=finding.optimization_impact.value if hasattr(finding.optimization_impact, "value") else str(finding.optimization_impact),
                finding_text=finding.finding_text,
                action_text=finding.action_text,
                action_deadline=finding.action_deadline,
                evidence_data=finding.evidence_data,
                confidence_score=finding.confidence_score,
                estimated_impact_size=finding.estimated_impact_size.value if finding.estimated_impact_size and hasattr(finding.estimated_impact_size, "value") else None,
                estimated_impact_paisa=finding.estimated_impact_paisa,
                significance_passed=result["significance"]["passed"],
                significance_score=result["significance"]["score"],
                corroboration_passed=result["corroboration"]["passed"],
                corroborating_agents=corr_agents if corr_agents else None,
                actionability_passed=result["actionability"]["passed"],
                identity_conflict="identity_conflict" in result["actionability"].get("reason", ""),
                qc_notes=(
                    f"sig:{result['significance']['reason']} "
                    f"corr:{result['corroboration']['reason']} "
                    f"act:{result['actionability']['reason']}"
                ),
                status=status_map.get(result["verdict"], "pending"),
            )
            self.db.add(af)
            self.db.flush()
        except Exception as e:
            logger.warning("Failed to persist finding: %s", e)
