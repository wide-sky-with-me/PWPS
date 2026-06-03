"""Human decision actor for Guided Draft workflow.

This actor does not make decisions itself.  Instead it prepares a
PendingUserDecision card for the frontend and signals that the workflow
should pause until the user submits their choice.
"""

from __future__ import annotations

from uuid import uuid4

from pwps_agent_api.actors.base import DecisionActor
from pwps_agent_api.fields import FieldRegistry
from pwps_agent_api.knowledge import KnowledgeService
from pwps_agent_api.schemas import (
    DecisionContext,
    DecisionResult,
    FieldTarget,
    PendingUserDecision,
    RunStatus,
    WorkflowState,
)
from pwps_agent_api.skills.candidate_generation import CandidateGenerationSkill
from pwps_agent_api.workflow.common import record_skill_call


class HumanDecisionActor(DecisionActor):
    """Presents a decision card to the user and blocks until they respond."""

    @property
    def actor_name(self) -> str:
        return "human_decision_actor"

    async def decide(self, context: DecisionContext) -> DecisionResult:
        """Not used directly — call build_pending_decision instead."""
        raise NotImplementedError(
            "HumanDecisionActor does not decide programmatically. "
            "Use build_pending_decision() to create a card for the user."
        )

    async def build_pending_decision(
        self,
        state: WorkflowState,
        target: FieldTarget,
        registry: FieldRegistry,
    ) -> PendingUserDecision:
        """Build a PendingUserDecision card for the given target group."""
        state.current_target = target
        missing_fields = [name for name in target.fields if name not in state.field_states]
        evidence = await KnowledgeService().evidence_for_fields(missing_fields)
        for item in evidence:
            state.evidence_store[item.evidence_id] = item
            for field_name in item.target_fields:
                state.field_evidence_map.setdefault(field_name, []).append(item.evidence_id)

        candidate_skill = CandidateGenerationSkill()
        candidates = await candidate_skill.run(
            target_fields=target.fields,
            field_states=state.field_states,
            evidence=evidence,
            registry=registry,
        )
        recommended = {
            field_name: state.field_states[field_name].value
            for field_name in target.fields
            if field_name in state.field_states and state.field_states[field_name].value is not None
        }
        recommended.update(
            {
                field_name: field_candidates[0]["value"]
                for field_name, field_candidates in candidates.items()
                if field_candidates
            }
        )

        session_id = f"session-{uuid4()}"
        pending = PendingUserDecision(
            run_id=state.run_id,
            session_id=session_id,
            target_group=target.group_name,
            target_fields=target.fields,
            summary=f"Confirm {target.group_name} fields.",
            candidates=candidates,
            evidence=[item.model_dump(mode="json") for item in evidence],
            risks=[],
            recommended=recommended,
            created_at=_now(),
        )
        state.status = RunStatus.WAITING_FOR_USER
        state.current_discussion_id = session_id
        record_skill_call(
            state,
            skill_name=candidate_skill.skill_name,
            skill_version=candidate_skill.skill_version,
            prompt_version=candidate_skill.prompt_version,
        )
        return pending


def _now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()
