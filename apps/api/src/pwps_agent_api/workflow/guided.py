"""Guided Draft workflow — human-in-the-loop via checkpoint/resume.

Refactored to:
- Accept DomainSpec for domain-agnostic operation
- Use LLM audit when domain pack is available
- Pass domain to all skills for prompt loading
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from pwps_agent_api.actors.human import HumanDecisionActor
from pwps_agent_api.audit.engine import AuditEngine
from pwps_agent_api.audit.repair import build_repair_targets
from pwps_agent_api.domain.spec import DomainSpec
from pwps_agent_api.fields import FieldRegistry, load_default_field_registry
from pwps_agent_api.output.builder import JsonOutputBuilder
from pwps_agent_api.schemas import (
    AuditRuleType,
    DecisionResult,
    DecisionType,
    FieldStatus,
    Mode,
    PendingUserDecision,
    Publishability,
    RiskLevel,
    RunStatus,
    SourceType,
    WorkflowState,
)
from pwps_agent_api.skills.requirement_understanding import RequirementUnderstandingSkill
from pwps_agent_api.workflow.common import (
    commit_decision,
    materialize_missing_fields,
    record_discussion,
    record_skill_call,
    trace,
)


@dataclass(frozen=True)
class GuidedDraftCheckpoint:
    state: WorkflowState
    pending_decision: PendingUserDecision | None
    output_paths: dict[str, Path]


def _resolve_domain_and_registry(
    domain: DomainSpec | None = None,
) -> tuple[DomainSpec | None, FieldRegistry]:
    """Resolve domain and registry from parameter or default."""
    if domain is not None:
        return domain, domain.field_registry

    from pwps_agent_api.domain.loader import load_domain
    try:
        loaded = load_domain("welding")
        return loaded, loaded.field_registry
    except FileNotFoundError:
        return None, load_default_field_registry()


async def start_guided_draft(
    raw_input: str,
    domain: DomainSpec | None = None,
) -> GuidedDraftCheckpoint:
    """Start a new Guided Draft workflow.

    Args:
        raw_input: User's natural language input.
        domain: Domain pack. If None, loads the default welding domain.
    """
    domain, registry = _resolve_domain_and_registry(domain)
    understanding_skill = RequirementUnderstandingSkill()
    state = WorkflowState(
        run_id=f"run-{uuid4()}",
        status=RunStatus.UNDERSTANDING,
        raw_input=raw_input,
        normalized_input={"text": " ".join(raw_input.strip().split()), "attachments": []},
        mode=Mode.GUIDED,
        field_registry_version=registry.field_registry_version,
        workflow_version="0.3.0",
    )
    trace(state, "normalize_input", "Normalized raw user input.")

    extracted_states = await understanding_skill.run(
        raw_input, domain=domain, registry=registry
    )
    for field_name, field_state in extracted_states.items():
        field_state.group = registry.get_field(field_name).group
        state.field_states[field_name] = field_state
    record_skill_call(
        state,
        skill_name=understanding_skill.skill_name,
        skill_version=understanding_skill.skill_version,
        prompt_version=understanding_skill.prompt_version,
    )
    trace(state, "understand_requirement", f"Extracted {len(extracted_states)} field(s).")

    state.target_queue = registry.confirmation_queue()
    trace(state, "build_confirmation_queue", f"Built {len(state.target_queue)} target(s).")

    actor = HumanDecisionActor()
    pending = await actor.build_pending_decision(state, state.target_queue[0], registry)
    return GuidedDraftCheckpoint(state=state, pending_decision=pending, output_paths={})


_ACTIONABLE_RULE_TYPES: set[AuditRuleType] = {AuditRuleType.HARD, AuditRuleType.COMPLETENESS}
_MAX_REPAIR_LOOPS: int = 3


async def resume_guided_draft(
    state: WorkflowState,
    pending: PendingUserDecision,
    *,
    decision_type: DecisionType,
    selected_values: dict[str, Any],
    comment: str | None,
    output_dir: Path,
    domain: DomainSpec | None = None,
) -> GuidedDraftCheckpoint:
    """Resume a Guided Draft workflow after user decision.

    Args:
        state: Current workflow state.
        pending: The pending decision that was presented to the user.
        decision_type: Type of decision (accept, choose_alternative, override).
        selected_values: User's selected values.
        comment: Optional user comment.
        output_dir: Directory for output files.
        domain: Domain pack. If None, loads the default welding domain.
    """
    domain, registry = _resolve_domain_and_registry(domain)
    _commit_user_decision(
        state,
        pending,
        decision_type=decision_type,
        selected_values=selected_values,
        comment=comment,
        registry=registry,
    )
    if state.target_queue and state.target_queue[0].group_name == pending.target_group:
        state.target_queue.pop(0)

    if state.target_queue:
        actor = HumanDecisionActor()
        next_pending = await actor.build_pending_decision(state, state.target_queue[0], registry)
        return GuidedDraftCheckpoint(state=state, pending_decision=next_pending, output_paths={})

    materialize_missing_fields(state, registry)
    state.status = RunStatus.AUDITING

    # Use async_audit for LLM-powered audit when domain is available
    audit_engine = AuditEngine()
    if domain is not None:
        state.audit_result = await audit_engine.async_audit(
            state.field_states, registry, state.evidence_store, domain
        )
    else:
        state.audit_result = audit_engine.audit(
            state.field_states, registry, state.evidence_store
        )

    trace(
        state,
        "global_audit",
        state.audit_result.summary,
        {
            "publishability": state.audit_result.publishability,
            "issue_count": len(state.audit_result.issues),
        },
    )

    repair_loop_count = len(state.repair_targets)
    if (
        state.audit_result.publishability is not Publishability.DRAFT_PUBLISHABLE
        and repair_loop_count < _MAX_REPAIR_LOOPS
    ):
        repair_targets = build_repair_targets(
            state.audit_result,
            registry,
            state.field_states,
            actionable_rule_types=_ACTIONABLE_RULE_TYPES,
        )
        if repair_targets:
            state.repair_targets = repair_targets
            state.target_queue = repair_targets
            trace(
                state,
                "repair_loop",
                f"Repair loop {repair_loop_count + 1}/{_MAX_REPAIR_LOOPS}: "
                f"{len(repair_targets)} repair target(s) queued.",
                {"repair_groups": [t.group_name for t in repair_targets]},
            )
            actor = HumanDecisionActor()
            next_pending = await actor.build_pending_decision(
                state, state.target_queue[0], registry
            )
            return GuidedDraftCheckpoint(
                state=state, pending_decision=next_pending, output_paths={}
            )

    state.status = RunStatus.FINALIZING
    trace(state, "finalize_output", "Writing Guided Draft JSON outputs.")
    bundle = JsonOutputBuilder().write(state, output_dir / state.run_id)
    state.status = RunStatus.FINISHED
    state.current_target = None
    state.current_discussion_id = None
    trace(state, "finalize_output", "Guided Draft output complete.")
    return GuidedDraftCheckpoint(
        state=state,
        pending_decision=None,
        output_paths=bundle.output_paths,
    )


def _commit_user_decision(
    state: WorkflowState,
    pending: PendingUserDecision,
    *,
    decision_type: DecisionType,
    selected_values: dict[str, Any],
    comment: str | None,
    registry: FieldRegistry,
) -> None:
    """Commit a human user's decision to the workflow state.

    Unlike auto mode, user overrides set source_type to USER_INPUT.
    """
    for field_name, value in selected_values.items():
        if field_name not in pending.target_fields:
            continue
        existing = state.field_states.get(field_name)
        if existing is not None and existing.status is not None:
            pass  # will be overwritten below

        spec = registry.get_field(field_name)
        evidence_ids = state.field_evidence_map.get(field_name, [])
        source_type = (
            SourceType.USER_INPUT
            if decision_type in {DecisionType.CHOOSE_ALTERNATIVE, DecisionType.OVERRIDE}
            else None  # will be filled by commit_decision
        )

        # Use common commit with USER_INPUT source override for user choices
        if source_type is SourceType.USER_INPUT:
            from pwps_agent_api.schemas import FieldState

            state.field_states[field_name] = FieldState(
                name=field_name,
                group=spec.group,
                value=value,
                status=FieldStatus.CONFIRMED,
                source_type=source_type,
                inference_policy=spec.inference_policy,
                evidence_ids=evidence_ids,
                confidence=1.0,
                risk_level=RiskLevel.HIGH if spec.high_risk else RiskLevel.MEDIUM,
                needs_human_confirmation=False,
            )
        else:
            commit_decision(
                state,
                pending.target_group,
                {field_name: value},
                registry,
                actor_type=Mode.GUIDED,
            )

    decision = DecisionResult(
        decision_type=decision_type,
        selected_values=selected_values,
        reason=comment or "Guided user decision accepted.",
        risk_level=RiskLevel.MEDIUM,
    )
    record_discussion(
        state,
        session_id=pending.session_id,
        target_fields=pending.target_fields,
        actor_type=Mode.GUIDED,
        decision=decision,
        group_name=pending.target_group,
    )
    trace(
        state,
        "commit_values",
        f"Committed Guided decision for {pending.target_group}.",
        {"session_id": pending.session_id, "selected_fields": list(selected_values)},
    )
