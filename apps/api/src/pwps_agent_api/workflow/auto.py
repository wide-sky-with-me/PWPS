"""Auto Draft workflow — fully automated LangGraph state machine.

Refactored to:
- Accept DomainSpec for domain-agnostic operation
- Use LLM audit when domain pack is available
- Pass domain to all skills for prompt loading
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict
from uuid import uuid4

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from pwps_agent_api.actors.virtual import VirtualDecisionActor
from pwps_agent_api.audit.engine import AuditEngine
from pwps_agent_api.audit.repair import build_repair_targets
from pwps_agent_api.domain.spec import DomainSpec
from pwps_agent_api.fields import FieldRegistry, load_default_field_registry
from pwps_agent_api.knowledge import KnowledgeService
from pwps_agent_api.output.builder import JsonOutputBuilder
from pwps_agent_api.schemas import (
    AuditRuleType,
    DecisionContext,
    FieldStatus,
    Mode,
    Publishability,
    RunStatus,
    WorkflowState,
)
from pwps_agent_api.skills.candidate_generation import CandidateGenerationSkill
from pwps_agent_api.skills.field_planning import FieldPlanningSkill
from pwps_agent_api.skills.requirement_understanding import RequirementUnderstandingSkill
from pwps_agent_api.workflow.common import (
    commit_decision,
    materialize_missing_fields,
    record_discussion,
    record_skill_call,
    trace,
)


class AutoGraphState(TypedDict, total=False):
    workflow_state: dict[str, Any]
    output_dir: str
    output_paths: dict[str, str]


@dataclass(frozen=True)
class AutoDraftResult:
    state: WorkflowState
    output_paths: dict[str, Path]


async def run_auto_draft(
    raw_input: str,
    output_dir: Path,
    domain: DomainSpec | None = None,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
) -> AutoDraftResult:
    """Run the Auto Draft workflow.

    Args:
        raw_input: User's natural language input.
        output_dir: Directory for output files.
        domain: Domain pack. If None, loads the default welding domain.
        checkpointer: Optional LangGraph checkpointer for state persistence.
    """
    if domain is None:
        from pwps_agent_api.domain.loader import load_domain
        try:
            domain = load_domain("welding")
        except FileNotFoundError:
            # No domain pack available — use legacy behavior
            domain = None

    registry = domain.field_registry if domain is not None else load_default_field_registry()
    workflow = _build_auto_graph(registry, domain, checkpointer)
    run_id = f"run-{uuid4()}"
    initial_state = WorkflowState(
        run_id=run_id,
        status=RunStatus.INITIALIZED,
        raw_input=raw_input,
        field_registry_version=registry.field_registry_version,
        workflow_version="0.2.0",
    )

    # Use run_id as thread_id for checkpoint isolation
    config = {"configurable": {"thread_id": run_id}}

    result = await workflow.ainvoke(
        {
            "workflow_state": initial_state.model_dump(mode="json"),
            "output_dir": str(output_dir),
        },
        config=config,
    )
    state = WorkflowState.model_validate(result["workflow_state"])
    output_paths = {name: Path(path) for name, path in result["output_paths"].items()}
    return AutoDraftResult(state=state, output_paths=output_paths)


_ACTIONABLE_RULE_TYPES: set[AuditRuleType] = {AuditRuleType.HARD, AuditRuleType.COMPLETENESS}
_MAX_REPAIR_LOOPS: int = 3


def _build_auto_graph(
    registry: FieldRegistry,
    domain: DomainSpec | None = None,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
) -> Any:
    graph = StateGraph(AutoGraphState)
    graph.add_node("normalize_input", _normalize_input)
    graph.add_node("understand_requirement", _understand_requirement(registry, domain))  # type: ignore[arg-type]
    graph.add_node("select_mode", _select_mode)
    graph.add_node("build_confirmation_queue", _build_confirmation_queue(registry, domain))  # type: ignore[arg-type]
    graph.add_node("confirm_target_subgraph", _confirm_all_targets(registry, domain))  # type: ignore[arg-type]
    graph.add_node("global_audit", _global_audit(registry, domain))  # type: ignore[arg-type]
    graph.add_node("finalize_output", _finalize_output(domain))  # type: ignore[arg-type]

    graph.add_edge(START, "normalize_input")
    graph.add_edge("normalize_input", "understand_requirement")
    graph.add_edge("understand_requirement", "select_mode")
    graph.add_edge("select_mode", "build_confirmation_queue")
    graph.add_edge("build_confirmation_queue", "confirm_target_subgraph")
    graph.add_edge("confirm_target_subgraph", "global_audit")
    graph.add_conditional_edges(
        "global_audit",
        _should_repair_or_finalize,
        {
            "finalize_output": "finalize_output",
            "confirm_target_subgraph": "confirm_target_subgraph",
        },
    )
    graph.add_edge("finalize_output", END)
    return graph.compile(checkpointer=checkpointer)


def _should_repair_or_finalize(state: AutoGraphState) -> str:
    workflow_state = WorkflowState.model_validate(state["workflow_state"])
    audit_result = workflow_state.audit_result
    if (
        audit_result is not None
        and audit_result.publishability is not Publishability.DRAFT_PUBLISHABLE
        and len(workflow_state.repair_targets) < _MAX_REPAIR_LOOPS
        and workflow_state.target_queue
    ):
        return "confirm_target_subgraph"
    return "finalize_output"


async def _normalize_input(state: AutoGraphState) -> AutoGraphState:
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
) -> Callable[[AutoGraphState], Any]:
    skill = RequirementUnderstandingSkill()

    async def node(state: AutoGraphState) -> AutoGraphState:
        workflow_state = WorkflowState.model_validate(state["workflow_state"])
        extracted_states = await skill.run(
            workflow_state.raw_input, domain=domain, registry=registry
        )
        for field_name, field_state in extracted_states.items():
            field_state.group = registry.get_field(field_name).group
            workflow_state.field_states[field_name] = field_state

        record_skill_call(
            workflow_state,
            skill_name=skill.skill_name,
            skill_version=skill.skill_version,
            prompt_version=skill.prompt_version,
        )
        trace(
            workflow_state,
            "understand_requirement",
            f"Extracted {len(extracted_states)} user-provided field(s).",
        )
        return {"workflow_state": workflow_state.model_dump(mode="json")}

    return node


async def _select_mode(state: AutoGraphState) -> AutoGraphState:
    workflow_state = WorkflowState.model_validate(state["workflow_state"])
    workflow_state.mode = Mode.AUTO
    trace(workflow_state, "select_mode", "Selected Auto Draft mode.")
    return {"workflow_state": workflow_state.model_dump(mode="json")}


def _build_confirmation_queue(
    registry: FieldRegistry,
    domain: DomainSpec | None = None,
) -> Callable[[AutoGraphState], Any]:
    planning_skill = FieldPlanningSkill()

    async def node(state: AutoGraphState) -> AutoGraphState:
        workflow_state = WorkflowState.model_validate(state["workflow_state"])
        workflow_state.status = RunStatus.FIELD_CONFIRMING
        workflow_state.target_queue = registry.confirmation_queue()
        trace(
            workflow_state,
            "build_confirmation_queue",
            f"Built {len(workflow_state.target_queue)} field group target(s).",
        )

        # Generate retrieval plans for field groups
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


def _confirm_all_targets(
    registry: FieldRegistry,
    domain: DomainSpec | None = None,
) -> Callable[[AutoGraphState], Any]:
    knowledge = KnowledgeService()
    candidate_skill = CandidateGenerationSkill()
    actor = VirtualDecisionActor()

    async def node(state: AutoGraphState) -> AutoGraphState:
        workflow_state = WorkflowState.model_validate(state["workflow_state"])
        for target in workflow_state.target_queue:
            workflow_state.current_target = target
            missing_fields = [
                field_name
                for field_name in target.fields
                if field_name not in workflow_state.field_states
                or workflow_state.field_states[field_name].status is FieldStatus.NEEDS_REPAIR
            ]
            evidence = await knowledge.evidence_for_fields(missing_fields)
            for item in evidence:
                workflow_state.evidence_store[item.evidence_id] = item
                for field_name in item.target_fields:
                    workflow_state.field_evidence_map.setdefault(field_name, []).append(
                        item.evidence_id
                    )

            candidate_bundle = await candidate_skill.run(
                target_fields=target.fields,
                field_states=workflow_state.field_states,
                evidence=evidence,
                registry=registry,
                domain=domain,
            )
            decision = await actor.decide(
                DecisionContext(
                    run_id=workflow_state.run_id,
                    session_id=f"session-{target.group_name}",
                    target_fields=target.fields,
                    progress_summary={"current_group": target.group_name},
                    candidate_bundle=candidate_bundle,
                    evidence_summary=[item.model_dump(mode="json") for item in evidence],
                    risks=[],
                    recommended_values={
                        field_name: candidates[0]["value"]
                        for field_name, candidates in candidate_bundle.items()
                        if candidates
                    },
                    discussion_history=[],
                )
            )
            commit_decision(
                workflow_state,
                target.group_name,
                decision.selected_values,
                registry,
                actor_type=Mode.AUTO,
            )
            record_discussion(
                workflow_state,
                session_id=f"session-{target.group_name}",
                target_fields=target.fields,
                actor_type=Mode.AUTO,
                decision=decision,
                group_name=target.group_name,
            )
            record_skill_call(
                workflow_state,
                skill_name=candidate_skill.skill_name,
                skill_version=candidate_skill.skill_version,
                prompt_version=candidate_skill.prompt_version,
            )
            trace(
                workflow_state,
                "confirm_target_subgraph",
                f"Confirmed group {target.group_name}.",
                {"selected_fields": list(decision.selected_values)},
            )

        workflow_state.current_target = None
        workflow_state.target_queue = []
        return {"workflow_state": workflow_state.model_dump(mode="json")}

    return node


def _global_audit(
    registry: FieldRegistry,
    domain: DomainSpec | None = None,
) -> Callable[[AutoGraphState], Any]:
    audit_engine = AuditEngine()

    async def node(state: AutoGraphState) -> AutoGraphState:
        workflow_state = WorkflowState.model_validate(state["workflow_state"])
        workflow_state.status = RunStatus.AUDITING
        materialize_missing_fields(workflow_state, registry)

        # Use async_audit for LLM-powered audit when domain is available
        if domain is not None:
            workflow_state.audit_result = await audit_engine.async_audit(
                workflow_state.field_states,
                registry,
                workflow_state.evidence_store,
                domain,
            )
        else:
            workflow_state.audit_result = audit_engine.audit(
                workflow_state.field_states, registry, workflow_state.evidence_store
            )

        trace(
            workflow_state,
            "global_audit",
            workflow_state.audit_result.summary,
            {"publishability": workflow_state.audit_result.publishability},
        )

        if workflow_state.audit_result.publishability is not Publishability.DRAFT_PUBLISHABLE:
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
                    f"Repair loop {len(workflow_state.repair_targets)}: "
                    f"{len(repair_targets)} repair target(s) queued.",
                    {"repair_groups": [t.group_name for t in repair_targets]},
                )

        return {"workflow_state": workflow_state.model_dump(mode="json")}

    return node


def _finalize_output(
    domain: DomainSpec | None = None,
) -> Callable[[AutoGraphState], Any]:
    async def node(state: AutoGraphState) -> AutoGraphState:
        workflow_state = WorkflowState.model_validate(state["workflow_state"])
        workflow_state.status = RunStatus.FINALIZING
        trace(workflow_state, "finalize_output", "Writing structured JSON outputs.")

        builder = JsonOutputBuilder()
        if domain is not None:
            bundle = await builder.write_with_llm_summaries(
                workflow_state, Path(state["output_dir"]), domain
            )
        else:
            bundle = builder.write(workflow_state, Path(state["output_dir"]))

        workflow_state.status = RunStatus.FINISHED
        trace(workflow_state, "finalize_output", "Auto Draft output complete.")
        return {
            "workflow_state": workflow_state.model_dump(mode="json"),
            "output_paths": {name: str(path) for name, path in bundle.output_paths.items()},
        }

    return node
