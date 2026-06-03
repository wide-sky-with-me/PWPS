"""Shared workflow helpers used by both Auto and Guided modes.

Extracted to avoid logic duplication between the two workflow paths.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pwps_agent_api.fields import FieldRegistry
from pwps_agent_api.guard import GuardViolation
from pwps_agent_api.knowledge import strongest_evidence_source
from pwps_agent_api.schemas import (
    DecisionResult,
    DiscussionRound,
    DiscussionSession,
    FieldState,
    FieldStatus,
    Mode,
    RiskLevel,
    SkillCallRecord,
    TraceEvent,
    WorkflowState,
)


def commit_decision(
    workflow_state: WorkflowState,
    group_name: str,
    selected_values: dict[str, Any],
    registry: FieldRegistry,
    *,
    actor_type: Mode,
) -> list[GuardViolation]:
    """Commit selected field values to the workflow state.

    Shared by auto (VirtualDecisionActor) and guided (HumanDecisionActor).
    Returns any guard violations found during validation.
    """
    from pwps_agent_api.guard import GuardValidator

    guard = GuardValidator()
    violations: list[GuardViolation] = []

    for field_name, value in selected_values.items():
        field_spec = registry.get_field(field_name)
        evidence_ids = workflow_state.field_evidence_map.get(field_name, [])

        # In guided mode with user override, source is USER_INPUT
        # In auto mode, source is derived from strongest evidence
        source_type = strongest_evidence_source(workflow_state.evidence_store, evidence_ids)

        new_state = FieldState(
            name=field_name,
            group=group_name,
            value=value,
            status=FieldStatus.CONFIRMED,
            source_type=source_type,
            inference_policy=field_spec.inference_policy,
            candidates=[],
            evidence_ids=evidence_ids,
            confidence=0.55,
            risk_level=RiskLevel.HIGH if field_spec.high_risk else RiskLevel.MEDIUM,
            needs_human_confirmation=field_spec.high_risk and actor_type is Mode.AUTO,
        )

        # Validate against guard constraints
        field_violations = guard.validate_field_state(
            new_state, field_spec, workflow_state.evidence_store
        )
        violations.extend(field_violations)

        workflow_state.field_states[field_name] = new_state

    # Log guard violations as trace events
    if violations:
        errors = [v for v in violations if v.severity == "error"]
        warnings = [v for v in violations if v.severity == "warning"]
        trace(
            workflow_state,
            "guard_check",
            f"Guard found {len(errors)} error(s), {len(warnings)} warning(s).",
            {
                "violations": [
                    {
                        "rule": v.rule,
                        "field": v.field_name,
                        "message": v.message,
                        "severity": v.severity,
                    }
                    for v in violations
                ]
            },
        )

    return violations


def record_discussion(
    workflow_state: WorkflowState,
    session_id: str,
    target_fields: list[str],
    actor_type: Mode,
    decision: DecisionResult,
    group_name: str,
) -> None:
    """Record a discussion session for a completed field group.

    Enforces the max_rounds limit from the field group spec.
    """
    # Find existing session for this group to check round count
    existing = next(
        (s for s in workflow_state.discussion_sessions if s.session_id == session_id),
        None,
    )
    if existing is not None:
        if len(existing.rounds) >= existing.max_rounds:
            existing.closed_reason = "max_rounds_reached"
            return
        existing.rounds.append(
            DiscussionRound(
                round_index=len(existing.rounds) + 1,
                decision=decision,
                evaluation={"accepted": True},
                created_at=now(),
            )
        )
        existing.final_decision = decision
        existing.closed_reason = f"{actor_type.value}_decision_committed"
    else:
        workflow_state.discussion_sessions.append(
            DiscussionSession(
                session_id=session_id,
                target_fields=target_fields,
                actor_type=actor_type,
                progress_summary={"current_group": group_name},
                rounds=[
                    DiscussionRound(
                        round_index=1,
                        decision=decision,
                        evaluation={"accepted": True},
                        created_at=now(),
                    )
                ],
                final_decision=decision,
                closed_reason=f"{actor_type.value}_decision_committed",
            )
        )


def check_discussion_round_limit(
    workflow_state: WorkflowState,
    session_id: str,
) -> bool:
    """Return True if the session has NOT reached its max_rounds limit."""
    session = next(
        (s for s in workflow_state.discussion_sessions if s.session_id == session_id),
        None,
    )
    if session is None:
        return True  # New session, no limit reached
    return len(session.rounds) < session.max_rounds


def materialize_missing_fields(workflow_state: WorkflowState, registry: FieldRegistry) -> None:
    """Create UNKNOWN FieldState entries for any registry fields not yet present."""
    for field_name, spec in registry.fields.items():
        if field_name in workflow_state.field_states:
            continue
        workflow_state.field_states[field_name] = FieldState(
            name=field_name,
            group=spec.group,
            value=None,
            status=FieldStatus.UNKNOWN,
            source_type=None,
            inference_policy=spec.inference_policy,
            risk_level=RiskLevel.LOW,
            needs_human_confirmation=False,
        )


def trace(
    workflow_state: WorkflowState,
    event: str,
    summary: str,
    payload: dict[str, Any] | None = None,
) -> None:
    """Append a trace event to the workflow state."""
    workflow_state.trace.append(
        TraceEvent(
            event=event,
            summary=summary,
            payload=payload or {},
            created_at=now(),
        )
    )


def record_skill_call(
    workflow_state: WorkflowState,
    skill_name: str,
    skill_version: str,
    prompt_version: str,
    *,
    model_name: str | None = None,
    input_hash: str | None = None,
    output_hash: str | None = None,
    validation_status: str = "ok",
    latency_ms: int | None = None,
) -> None:
    """Record a skill call for observability and reproducibility."""
    workflow_state.skill_calls.append(
        SkillCallRecord(
            skill_name=skill_name,
            skill_version=skill_version,
            prompt_version=prompt_version,
            model_name=model_name,
            input_hash=input_hash,
            output_hash=output_hash,
            validation_status=validation_status,
            latency_ms=latency_ms,
            created_at=now(),
        )
    )
    # Also update the simple version map for backward compatibility
    workflow_state.skill_versions[skill_name] = skill_version


def now() -> str:
    """Return the current UTC timestamp as ISO format string."""
    return datetime.now(UTC).isoformat()
