import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pwps_agent_api.core.config import get_settings
from pwps_agent_api.domain.spec import DomainSpec
from pwps_agent_api.schemas import WorkflowState


@dataclass(frozen=True)
class OutputBundle:
    output_paths: dict[str, Path]


class JsonOutputBuilder:
    def write(self, state: WorkflowState, output_dir: Path) -> OutputBundle:
        output_dir.mkdir(parents=True, exist_ok=True)
        payloads = {
            "pwps": _build_pwps_payload(state),
            "field_report": _build_field_report(state),
            "evidence_report": _build_evidence_report(state),
            "risk_report": _build_risk_report(state),
            "discussion_trace": _build_discussion_trace(state),
            "render_payload": _build_render_payload(state),
        }
        output_paths: dict[str, Path] = {}
        for name, payload in payloads.items():
            path = output_dir / f"{name}.json"
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            output_paths[name] = path
        return OutputBundle(output_paths=output_paths)

    async def write_with_llm_summaries(
        self, state: WorkflowState, output_dir: Path, domain: DomainSpec | None = None
    ) -> OutputBundle:
        """Write outputs with LLM-generated summaries when available."""
        from pwps_agent_api.skills.field_summary import FieldSummarySkill
        from pwps_agent_api.skills.risk_summary import RiskSummarySkill

        settings = get_settings()
        use_llm = settings.llm_api_key and domain is not None

        output_dir.mkdir(parents=True, exist_ok=True)

        # Build base payloads
        field_report = _build_field_report(state)
        risk_report = _build_risk_report(state)

        # Enhance with LLM summaries if available
        if use_llm:
            field_summary_skill = FieldSummarySkill()
            risk_summary_skill = RiskSummarySkill()

            field_summary = await field_summary_skill.run(
                field_states=state.field_states,
                domain=domain,
            )
            field_report["llm_summary"] = field_summary.summary
            field_report["highlights"] = field_summary.highlights

            if state.audit_result:
                risk_summary = await risk_summary_skill.run(
                    audit_result=state.audit_result,
                    field_states=state.field_states,
                    domain=domain,
                )
                risk_report["llm_summary"] = risk_summary.summary
                risk_report["risk_items"] = [
                    item.model_dump(mode="json") for item in risk_summary.risks
                ]

        payloads = {
            "pwps": _build_pwps_payload(state),
            "field_report": field_report,
            "evidence_report": _build_evidence_report(state),
            "risk_report": risk_report,
            "discussion_trace": _build_discussion_trace(state),
            "render_payload": _build_render_payload(state),
        }
        output_paths: dict[str, Path] = {}
        for name, payload in payloads.items():
            path = output_dir / f"{name}.json"
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            output_paths[name] = path
        return OutputBundle(output_paths=output_paths)


def _build_pwps_payload(state: WorkflowState) -> dict[str, Any]:
    return {
        "run_id": state.run_id,
        "mode": state.mode,
        "schema_version": state.schema_version,
        "field_registry_version": state.field_registry_version,
        "workflow_version": state.workflow_version,
        "publishability": None if state.audit_result is None else state.audit_result.publishability,
        "fields": {
            name: {
                "value": field.value,
                "status": field.status,
                "source_type": field.source_type,
                "risk_level": field.risk_level,
                "needs_human_confirmation": field.needs_human_confirmation,
                "evidence_ids": field.evidence_ids,
            }
            for name, field in state.field_states.items()
        },
    }


def _build_field_report(state: WorkflowState) -> dict[str, Any]:
    return {
        "run_id": state.run_id,
        "field_states": {
            name: field.model_dump(mode="json") for name, field in state.field_states.items()
        },
        "evidence_store": {
            evidence_id: evidence.model_dump(mode="json")
            for evidence_id, evidence in state.evidence_store.items()
        },
    }


def _build_evidence_report(state: WorkflowState) -> dict[str, Any]:
    return {
        "run_id": state.run_id,
        "evidence": [
            evidence.model_dump(mode="json") for evidence in state.evidence_store.values()
        ],
        "field_evidence_map": state.field_evidence_map,
    }


def _build_risk_report(state: WorkflowState) -> dict[str, Any]:
    if state.audit_result is None:
        return {"run_id": state.run_id, "publishability": None, "issues": [], "repair_targets": []}
    return {
        "run_id": state.run_id,
        "publishability": state.audit_result.publishability,
        "summary": state.audit_result.summary,
        "issues": [issue.model_dump(mode="json") for issue in state.audit_result.issues],
        "repair_targets": [target.model_dump(mode="json") for target in state.repair_targets],
    }


def _build_discussion_trace(state: WorkflowState) -> dict[str, Any]:
    return {
        "run_id": state.run_id,
        "trace": [event.model_dump(mode="json") for event in state.trace],
        "discussion_sessions": [
            session.model_dump(mode="json") for session in state.discussion_sessions
        ],
    }


def _build_render_payload(state: WorkflowState) -> dict[str, Any]:
    """Build a render-ready payload for frontend consumption."""
    return {
        "run_id": state.run_id,
        "mode": state.mode,
        "status": state.status,
        "publishability": None if state.audit_result is None else state.audit_result.publishability,
        "fields": {
            name: {
                "value": field.value,
                "label": name,
                "status": field.status,
                "source_type": field.source_type,
                "risk_level": field.risk_level,
                "needs_human_confirmation": field.needs_human_confirmation,
                "candidates": field.candidates,
                "evidence_ids": field.evidence_ids,
            }
            for name, field in state.field_states.items()
        },
        "groups": [
            {
                "name": session.session_id.split("-", 1)[-1]
                if "-" in session.session_id
                else session.session_id,
                "status": "completed" if session.closed_reason else "pending",
                "fields": session.target_fields,
            }
            for session in state.discussion_sessions
        ],
        "audit": None
        if state.audit_result is None
        else {
            "publishability": state.audit_result.publishability,
            "issue_count": len(state.audit_result.issues),
            "summary": state.audit_result.summary,
        },
    }
