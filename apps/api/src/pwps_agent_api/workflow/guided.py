"""Guided Draft workflow — human-in-the-loop via LangGraph interrupts.

Uses LangGraph's native checkpointer and interrupt mechanism for
pause/resume functionality.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict
from uuid import uuid4

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.constants import START
from langgraph.graph import StateGraph
from langgraph.types import Command, interrupt

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
from pwps_agent_api.skills.field_planning import FieldPlanningSkill
from pwps_agent_api.skills.override_evaluation import OverrideEvaluationSkill
from pwps_agent_api.skills.requirement_understanding import RequirementUnderstandingSkill
from pwps_agent_api.workflow.common import (
    commit_decision,
    materialize_missing_fields,
    record_discussion,
    record_skill_call,
    trace,
)


class GuidedGraphState(TypedDict, total=False):
    workflow_state: dict[str, Any]
    output_dir: str
    output_paths: dict[str, str]
    # Interrupt data for human-in-the-loop
    pending_decision: dict[str, Any] | None
    user_decision: dict[str, Any] | None


_ACTIONABLE_RULE_TYPES: set[AuditRuleType] = {AuditRuleType.HARD, AuditRuleType.COMPLETENESS}
_MAX_REPAIR_LOOPS: int = 3


@dataclass(frozen=True)
class GuidedDraftResult:
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


def _build_guided_graph(
    registry: FieldRegistry,
    domain: DomainSpec | None = None,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
) -> Any:
    """Build the Guided Draft LangGraph with interrupt support."""
    graph = StateGraph(GuidedGraphState)

    # Add nodes
    graph.add_node("normalize_input", _normalize_input)
    graph.add_node("understand_requirement", _understand_requirement(registry, domain))
    graph.add_node("build_confirmation_queue", _build_confirmation_queue(registry, domain))
    graph.add_node("process_group", _process_group(registry, domain))
    graph.add_node("global_audit", _global_audit(registry, domain))
    graph.add_node("finalize_output", _finalize_output(domain))

    # Add edges
    graph.add_edge(START, "normalize_input")
    graph.add_edge("normalize_input", "understand_requirement")
    graph.add_edge("understand_requirement", "build_confirmation_queue")
    graph.add_edge("build_confirmation_queue", "process_group")
    graph.add_conditional_edges(
        "process_group",
        _should_continue_or_audit,
        {
            "process_group": "process_group",
            "global_audit": "global_audit",
        },
    )
    graph.add_conditional_edges(
        "global_audit",
        _should_repair_or_finalize,
        {
            "process_group": "process_group",
            "finalize_output": "finalize_output",
        },
    )
    from langgraph.graph import END
    graph.add_edge("finalize_output", END)

    return graph.compile(checkpointer=checkpointer)


def _should_continue_or_audit(state: GuidedGraphState) -> str:
    """Decide whether to process next group or move to audit."""
    workflow_state = WorkflowState.model_validate(state["workflow_state"])
    if workflow_state.target_queue:
        return "process_group"
    return "global_audit"


def _should_repair_or_finalize(state: GuidedGraphState) -> str:
    """Decide whether to repair or finalize after audit."""
    workflow_state = WorkflowState.model_validate(state["workflow_state"])
    audit_result = workflow_state.audit_result
    if (
        audit_result is not None
        and audit_result.publishability is not Publishability.DRAFT_PUBLISHABLE
        and len(workflow_state.repair_targets) < _MAX_REPAIR_LOOPS
        and workflow_state.target_queue
    ):
        return "process_group"
    return "finalize_output"


# --- Node implementations ---

def _normalize_input(state: GuidedGraphState) -> GuidedGraphState:
    workflow_state = WorkflowState.model_validate(state["workflow_state"])
    workflow_state.status = RunStatus.UNDERSTANDING
    workflow_state.normalized_input = {
        "text": " ".join(workflow_state.raw_input.strip().split()),
        "attachments": [],
    }
    trace(workflow_state, "normalize_input", "Normalized raw user input.")
    return {"workflow_state": workflow_state.model_dump(mode="json")}


def _understand_requirement(
    registry: FieldRegistry,
    domain: DomainSpec | None = None,
) -> Any:
    skill = RequirementUnderstandingSkill()

    async def node(state: GuidedGraphState) -> GuidedGraphState:
        workflow_state = WorkflowState.model_validate(state["workflow_state"])
        extracted = await skill.run(workflow_state.raw_input, domain=domain, registry=registry)
        for field_name, field_state in extracted.items():
            field_state.group = registry.get_field(field_name).group
            workflow_state.field_states[field_name] = field_state
        record_skill_call(
            workflow_state,
            skill_name=skill.skill_name,
            skill_version=skill.skill_version,
            prompt_version=skill.prompt_version,
        )
        trace(workflow_state, "understand_requirement", f"Extracted {len(extracted)} field(s).")
        return {"workflow_state": workflow_state.model_dump(mode="json")}

    return node


def _build_confirmation_queue(
    registry: FieldRegistry,
    domain: DomainSpec | None = None,
) -> Any:
    planning_skill = FieldPlanningSkill()

    async def node(state: GuidedGraphState) -> GuidedGraphState:
        workflow_state = WorkflowState.model_validate(state["workflow_state"])
        workflow_state.status = RunStatus.FIELD_CONFIRMING
        workflow_state.target_queue = registry.confirmation_queue()
        trace(
            workflow_state,
            "build_confirmation_queue",
            f"Built {len(workflow_state.target_queue)} target(s).",
        )

        # Generate retrieval plans
        field_specs = {name: registry.get_field(name) for name in registry.fields}
        for target in workflow_state.target_queue:
            plan = await planning_skill.run(
                target_fields=target.fields,
                field_specs=field_specs,
                field_states=workflow_state.field_states,
                domain=domain,
            )
            trace(
                workflow_state,
                "plan_field_retrieval",
                f"Generated retrieval plan for {target.group_name}.",
                {"group": target.group_name, "targets": len(plan.targets)},
            )
        record_skill_call(
            workflow_state,
            skill_name=planning_skill.skill_name,
            skill_version=planning_skill.skill_version,
            prompt_version=planning_skill.prompt_version,
        )

        return {"workflow_state": workflow_state.model_dump(mode="json")}

    return node


def _process_group(
    registry: FieldRegistry,
    domain: DomainSpec | None = None,
) -> Any:
    actor = HumanDecisionActor()
    override_skill = OverrideEvaluationSkill()

    async def node(state: GuidedGraphState) -> GuidedGraphState:
        workflow_state = WorkflowState.model_validate(state["workflow_state"])

        if not workflow_state.target_queue:
            return {"workflow_state": workflow_state.model_dump(mode="json")}

        target = workflow_state.target_queue[0]

        # If we have a user decision to process, apply it
        user_decision = state.get("user_decision")
        if user_decision:
            decision_type = DecisionType(user_decision["decision_type"])
            selected_values = user_decision["selected_values"]
            comment = user_decision.get("comment")

            # Evaluate overrides
            if decision_type is DecisionType.OVERRIDE:
                for field_name, value in selected_values.items():
                    if field_name not in target.fields:
                        continue
                    pending_data = state.get("pending_decision")
                    original_value = None
                    if isinstance(pending_data, dict):
                        original_value = pending_data.get("recommended", {}).get(field_name)
                    evaluation = await override_skill.run(
                        field_name=field_name,
                        override_value=str(value),
                        original_value=str(original_value) if original_value is not None else None,
                        field_states=workflow_state.field_states,
                        domain=domain,
                    )
                    record_skill_call(
                        workflow_state,
                        skill_name=override_skill.skill_name,
                        skill_version=override_skill.skill_version,
                        prompt_version=override_skill.prompt_version,
                    )
                    trace(
                        workflow_state,
                        "override_evaluation",
                        f"Override evaluation for {field_name}: {evaluation.recommendation}",
                        {
                            "field": field_name,
                            "is_safe": evaluation.is_safe,
                            "risk_level": evaluation.risk_level,
                            "recommendation": evaluation.recommendation,
                            "conflicts": evaluation.conflicts,
                        },
                    )

            # Commit the decision
            _commit_user_decision(
                workflow_state,
                target,
                decision_type=decision_type,
                selected_values=selected_values,
                comment=comment,
                registry=registry,
            )

            # Move to next group
            workflow_state.target_queue.pop(0)

            # Clear user decision
            return {
                "workflow_state": workflow_state.model_dump(mode="json"),
                "user_decision": None,
                "pending_decision": None,
            }

        # No user decision yet - build pending decision and interrupt
        pending_decision = await actor.build_pending_decision(workflow_state, target, registry)
        pending_dict = pending_decision.model_dump(mode="json")

        # Set status to waiting_for_user before interrupting
        workflow_state.status = RunStatus.WAITING_FOR_USER
        workflow_state.current_target = target

        # Interrupt to wait for user input - state is saved to checkpoint here
        user_response = interrupt({
            "pending_decision": pending_dict,
            "workflow_state": workflow_state.model_dump(mode="json"),
        })

        # --- Code below executes after resume ---

        # Process the user's response
        decision_type = DecisionType(user_response["decision_type"])
        selected_values = user_response["selected_values"]
        comment = user_response.get("comment")

        # Evaluate overrides
        if decision_type is DecisionType.OVERRIDE:
            for field_name, value in selected_values.items():
                if field_name not in target.fields:
                    continue
                original_value = pending_decision.recommended.get(field_name)
                evaluation = await override_skill.run(
                    field_name=field_name,
                    override_value=str(value),
                    original_value=str(original_value) if original_value is not None else None,
                    field_states=workflow_state.field_states,
                    domain=domain,
                )
                record_skill_call(
                    workflow_state,
                    skill_name=override_skill.skill_name,
                    skill_version=override_skill.skill_version,
                    prompt_version=override_skill.prompt_version,
                )
                trace(
                    workflow_state,
                    "override_evaluation",
                    f"Override evaluation for {field_name}: {evaluation.recommendation}",
                    {
                        "field": field_name,
                        "is_safe": evaluation.is_safe,
                        "risk_level": evaluation.risk_level,
                        "recommendation": evaluation.recommendation,
                        "conflicts": evaluation.conflicts,
                    },
                )

        # Commit the decision
        _commit_user_decision(
            workflow_state,
            target,
            decision_type=decision_type,
            selected_values=selected_values,
            comment=comment,
            registry=registry,
        )

        # Move to next group
        workflow_state.target_queue.pop(0)

        return {
            "workflow_state": workflow_state.model_dump(mode="json"),
            "user_decision": None,
            "pending_decision": None,
        }

    return node


def _commit_user_decision(
    state: WorkflowState,
    target: Any,
    *,
    decision_type: DecisionType,
    selected_values: dict[str, Any],
    comment: str | None,
    registry: FieldRegistry,
) -> None:
    """Commit a human user's decision to the workflow state."""
    for field_name, value in selected_values.items():
        if field_name not in target.fields:
            continue

        spec = registry.get_field(field_name)
        evidence_ids = state.field_evidence_map.get(field_name, [])
        source_type = (
            SourceType.USER_INPUT
            if decision_type in {DecisionType.CHOOSE_ALTERNATIVE, DecisionType.OVERRIDE}
            else None
        )

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
                target.group_name,
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
        session_id=f"session-{target.group_name}",
        target_fields=target.fields,
        actor_type=Mode.GUIDED,
        decision=decision,
        group_name=target.group_name,
    )
    trace(
        state,
        "commit_values",
        f"Committed Guided decision for {target.group_name}.",
        {"selected_fields": list(selected_values)},
    )


def _global_audit(
    registry: FieldRegistry,
    domain: DomainSpec | None = None,
) -> Any:
    async def node(state: GuidedGraphState) -> GuidedGraphState:
        workflow_state = WorkflowState.model_validate(state["workflow_state"])
        materialize_missing_fields(workflow_state, registry)
        workflow_state.status = RunStatus.AUDITING

        audit_engine = AuditEngine()
        if domain is not None:
            workflow_state.audit_result = await audit_engine.async_audit(
                workflow_state.field_states, registry, workflow_state.evidence_store, domain
            )
        else:
            workflow_state.audit_result = audit_engine.audit(
                workflow_state.field_states, registry, workflow_state.evidence_store
            )

        trace(
            workflow_state,
            "global_audit",
            workflow_state.audit_result.summary,
            {
                "publishability": workflow_state.audit_result.publishability,
                "issue_count": len(workflow_state.audit_result.issues),
            },
        )

        # Check for repair targets
        repair_loop_count = len(workflow_state.repair_targets)
        if (
            workflow_state.audit_result.publishability is not Publishability.DRAFT_PUBLISHABLE
            and repair_loop_count < _MAX_REPAIR_LOOPS
        ):
            repair_targets = build_repair_targets(
                workflow_state.audit_result,
                registry,
                workflow_state.field_states,
                actionable_rule_types=_ACTIONABLE_RULE_TYPES,
            )
            if repair_targets:
                workflow_state.repair_targets = repair_targets
                workflow_state.target_queue = repair_targets
                trace(
                    workflow_state,
                    "repair_loop",
                    f"Repair loop {repair_loop_count + 1}/{_MAX_REPAIR_LOOPS}: "
                    f"{len(repair_targets)} repair target(s) queued.",
                    {"repair_groups": [t.group_name for t in repair_targets]},
                )

        return {"workflow_state": workflow_state.model_dump(mode="json")}

    return node


def _finalize_output(
    domain: DomainSpec | None = None,
) -> Any:
    async def node(state: GuidedGraphState) -> GuidedGraphState:
        workflow_state = WorkflowState.model_validate(state["workflow_state"])
        output_dir = Path(state["output_dir"])
        workflow_state.status = RunStatus.FINALIZING
        trace(workflow_state, "finalize_output", "Writing Guided Draft JSON outputs.")

        builder = JsonOutputBuilder()
        if domain is not None:
            bundle = await builder.write_with_llm_summaries(
                workflow_state, output_dir / workflow_state.run_id, domain
            )
        else:
            bundle = builder.write(workflow_state, output_dir / workflow_state.run_id)

        workflow_state.status = RunStatus.FINISHED
        workflow_state.current_target = None
        workflow_state.current_discussion_id = None
        trace(workflow_state, "finalize_output", "Guided Draft output complete.")

        return {
            "workflow_state": workflow_state.model_dump(mode="json"),
            "output_paths": {name: str(path) for name, path in bundle.output_paths.items()},
        }

    return node


# --- Public API ---

async def start_guided_draft(
    raw_input: str,
    output_dir: Path,
    domain: DomainSpec | None = None,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
) -> GuidedDraftResult:
    """Start a new Guided Draft workflow.

    Args:
        raw_input: User's natural language input.
        output_dir: Directory for output files.
        domain: Domain pack. If None, loads the default welding domain.
        checkpointer: Optional LangGraph checkpointer for state persistence.
    """
    from pwps_agent_api.core.checkpoint import get_checkpointer

    # Always use the checkpointer for interrupts to work
    if checkpointer is None:
        checkpointer = await get_checkpointer()

    domain, registry = _resolve_domain_and_registry(domain)
    workflow = _build_guided_graph(registry, domain, checkpointer)

    run_id = f"run-{uuid4()}"
    initial_state = WorkflowState(
        run_id=run_id,
        status=RunStatus.INITIALIZED,
        raw_input=raw_input,
        mode=Mode.GUIDED,
        field_registry_version=registry.field_registry_version,
        workflow_version="0.3.0",
    )

    config = {"configurable": {"thread_id": run_id}}

    # Run until first interrupt
    result = None
    async for event in workflow.astream(
        {
            "workflow_state": initial_state.model_dump(mode="json"),
            "output_dir": str(output_dir),
        },
        config=config,
        stream_mode="updates",
    ):
        if "__interrupt__" in event:
            # Graph paused at interrupt - extract state from interrupt value
            interrupt_data = event["__interrupt__"][0]
            interrupt_value = interrupt_data.value

            # Extract workflow state and pending decision from interrupt value
            workflow_state = WorkflowState.model_validate(
                interrupt_value.get("workflow_state", {})
            )
            pending_decision = PendingUserDecision.model_validate(
                interrupt_value.get("pending_decision", {})
            )
            return GuidedDraftResult(
                state=workflow_state,
                pending_decision=pending_decision,
                output_paths={},
            )
        result = event

    # Workflow completed without interrupt (shouldn't happen for guided)
    final_state_dict = result.get("workflow_state", {}) if result else {}
    final_state = WorkflowState.model_validate(final_state_dict)
    output_paths = {
        name: Path(path)
        for name, path in (result.get("output_paths") or {}).items()
    } if result else {}
    return GuidedDraftResult(
        state=final_state,
        pending_decision=None,
        output_paths=output_paths,
    )


async def resume_guided_draft(
    run_id: str,
    decision_type: DecisionType,
    selected_values: dict[str, Any],
    comment: str | None,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
) -> GuidedDraftResult:
    """Resume a Guided Draft workflow after user decision.

    Args:
        run_id: The run ID to resume.
        decision_type: Type of decision (accept, choose_alternative, override).
        selected_values: User's selected values.
        comment: Optional user comment.
        checkpointer: Optional LangGraph checkpointer for state persistence.
    """
    from pwps_agent_api.core.checkpoint import get_checkpointer
    from pwps_agent_api.domain.loader import load_domain

    # Always use the checkpointer for resume
    if checkpointer is None:
        checkpointer = await get_checkpointer()

    try:
        domain = load_domain("welding")
    except FileNotFoundError:
        domain = None

    registry = domain.field_registry if domain is not None else load_default_field_registry()
    workflow = _build_guided_graph(registry, domain, checkpointer)

    config = {"configurable": {"thread_id": run_id}}

    # Resume with user's decision
    command = Command(resume={
        "decision_type": decision_type.value,
        "selected_values": selected_values,
        "comment": comment,
    })  # type: ignore[var-annotated]

    result = None
    async for event in workflow.astream(command, config, stream_mode="updates"):
        if "__interrupt__" in event:
            # Another interrupt - need more user input
            interrupt_data = event["__interrupt__"][0]
            interrupt_value = interrupt_data.value

            # Extract workflow state and pending decision from interrupt value
            workflow_state = WorkflowState.model_validate(
                interrupt_value.get("workflow_state", {})
            )
            pending_decision = PendingUserDecision.model_validate(
                interrupt_value.get("pending_decision", {})
            )
            return GuidedDraftResult(
                state=workflow_state,
                pending_decision=pending_decision,
                output_paths={},
            )
        result = event

    # Workflow completed
    final_state_dict = result.get("workflow_state", {}) if result else {}
    final_state = WorkflowState.model_validate(final_state_dict)
    output_paths = {
        name: Path(path)
        for name, path in (result.get("output_paths") or {}).items()
    } if result else {}
    return GuidedDraftResult(
        state=final_state,
        pending_decision=None,
        output_paths=output_paths,
    )
