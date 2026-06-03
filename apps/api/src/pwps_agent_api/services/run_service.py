import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from pwps_agent_api.core.config import Settings, get_settings
from pwps_agent_api.db.models import RunRecord
from pwps_agent_api.events import EventStore
from pwps_agent_api.schemas import Mode, PendingUserDecision, Publishability, WorkflowState
from pwps_agent_api.schemas.api import (
    CreateRunRequest,
    CreateRunResponse,
    CurrentDecisionResponse,
    RunEventsResponse,
    RunOutputsResponse,
    RunProgress,
    RunStatusResponse,
    SubmitDecisionRequest,
    SubmitDecisionResponse,
)
from pwps_agent_api.workflow.auto import run_auto_draft
from pwps_agent_api.workflow.guided import resume_guided_draft, start_guided_draft


@dataclass(frozen=True)
class RunService:
    session: AsyncSession
    settings: Settings
    event_store: EventStore | None = None

    async def create_run(self, request: CreateRunRequest) -> CreateRunResponse:
        if request.mode is Mode.GUIDED:
            return await self._create_guided_run(request)

        result = await run_auto_draft(request.input, self.settings.local_artifact_dir)
        outputs = _read_outputs(result.output_paths)
        state_json = result.state.model_dump(mode="json")
        record = RunRecord(
            run_id=result.state.run_id,
            status=result.state.status.value,
            mode=None if result.state.mode is None else result.state.mode.value,
            raw_input=result.state.raw_input,
            workflow_state_json=state_json,
            outputs_json=outputs,
            trace_json=[event.model_dump(mode="json") for event in result.state.trace],
        )
        self.session.add(record)
        await self.session.commit()
        if self.event_store is not None:
            await self.event_store.publish_many(result.state.run_id, result.state.trace)
        return CreateRunResponse(run_id=record.run_id, status=result.state.status)

    async def _create_guided_run(self, request: CreateRunRequest) -> CreateRunResponse:
        checkpoint = await start_guided_draft(request.input)
        record = RunRecord(
            run_id=checkpoint.state.run_id,
            status=checkpoint.state.status.value,
            mode=Mode.GUIDED.value,
            raw_input=checkpoint.state.raw_input,
            workflow_state_json=checkpoint.state.model_dump(mode="json"),
            outputs_json={},
            trace_json=[event.model_dump(mode="json") for event in checkpoint.state.trace],
            pending_decision_json=None
            if checkpoint.pending_decision is None
            else checkpoint.pending_decision.model_dump(mode="json"),
        )
        self.session.add(record)
        await self.session.commit()
        if self.event_store is not None:
            await self.event_store.publish_many(record.run_id, checkpoint.state.trace)
        return CreateRunResponse(run_id=record.run_id, status=checkpoint.state.status)

    async def get_run(self, run_id: str) -> RunRecord | None:
        return await self.session.get(RunRecord, run_id)

    async def status_response(self, run_id: str) -> RunStatusResponse | None:
        record = await self.get_run(run_id)
        if record is None:
            return None

        state = WorkflowState.model_validate(record.workflow_state_json)
        return RunStatusResponse(
            run_id=state.run_id,
            status=state.status,
            mode=state.mode,
            current_target=state.current_target,
            progress=_progress_from_state(state),
            publishability=_publishability_from_state(state),
        )

    async def outputs_response(self, run_id: str) -> RunOutputsResponse | None:
        record = await self.get_run(run_id)
        if record is None:
            return None

        outputs = record.outputs_json
        publishability = outputs["risk_report"].get("publishability")
        return RunOutputsResponse(
            pwps=outputs["pwps"],
            field_report=outputs["field_report"],
            evidence_report={
                "evidence": list(outputs["field_report"].get("evidence_store", {}).values())
            },
            risk_report=outputs["risk_report"],
            discussion_trace=outputs["discussion_trace"],
            publishability=None if publishability is None else Publishability(publishability),
        )

    async def events_response(self, run_id: str) -> RunEventsResponse | None:
        record = await self.get_run(run_id)
        if record is None:
            return None

        if self.event_store is not None:
            events = await self.event_store.list_events(run_id)
            if events:
                return RunEventsResponse(run_id=run_id, events=events)

        state = WorkflowState.model_validate(record.workflow_state_json)
        return RunEventsResponse(run_id=state.run_id, events=state.trace)

    async def current_decision_response(self, run_id: str) -> CurrentDecisionResponse | None:
        record = await self.get_run(run_id)
        if record is None or record.pending_decision_json is None:
            return None
        return CurrentDecisionResponse.model_validate(record.pending_decision_json)

    async def submit_decision(
        self,
        run_id: str,
        request: SubmitDecisionRequest,
    ) -> SubmitDecisionResponse | None:
        record = await self.get_run(run_id)
        if record is None:
            return None
        if record.pending_decision_json is None:
            raise GuidedDecisionStateError("INVALID_STATE_TRANSITION")

        pending = PendingUserDecision.model_validate(record.pending_decision_json)
        if pending.session_id != request.session_id:
            raise GuidedDecisionStateError("DECISION_SESSION_EXPIRED")

        state = WorkflowState.model_validate(record.workflow_state_json)
        previous_trace_length = len(state.trace)
        checkpoint = await resume_guided_draft(
            state,
            pending,
            decision_type=request.decision_type,
            selected_values=request.selected_values,
            comment=request.comment,
            output_dir=self.settings.local_artifact_dir,
        )
        record.status = checkpoint.state.status.value
        record.workflow_state_json = checkpoint.state.model_dump(mode="json")
        record.trace_json = [event.model_dump(mode="json") for event in checkpoint.state.trace]
        record.pending_decision_json = (
            None
            if checkpoint.pending_decision is None
            else checkpoint.pending_decision.model_dump(mode="json")
        )
        if checkpoint.output_paths:
            record.outputs_json = _read_outputs(checkpoint.output_paths)
        await self.session.commit()
        if self.event_store is not None:
            await self.event_store.publish_many(
                record.run_id,
                checkpoint.state.trace[previous_trace_length:],
            )
        return SubmitDecisionResponse(
            run_id=record.run_id,
            status=checkpoint.state.status,
            accepted=True,
        )


def build_run_service(
    session: AsyncSession,
    settings: Settings | None = None,
    event_store: EventStore | None = None,
) -> RunService:
    return RunService(
        session=session,
        settings=settings or get_settings(),
        event_store=event_store,
    )


def _read_outputs(output_paths: dict[str, Path]) -> dict[str, Any]:
    return {
        name: json.loads(path.read_text(encoding="utf-8")) for name, path in output_paths.items()
    }


def _progress_from_state(state: WorkflowState) -> RunProgress:
    confirmed_groups = sorted({field.group for field in state.field_states.values() if field.value})
    queued_groups = [target.group_name for target in state.target_queue]
    remaining_groups = [group for group in queued_groups if group not in confirmed_groups]
    return RunProgress(confirmed_groups=confirmed_groups, remaining_groups=remaining_groups)


def _publishability_from_state(state: WorkflowState) -> Publishability | None:
    return None if state.audit_result is None else state.audit_result.publishability


class GuidedDecisionStateError(Exception):
    def __init__(self, error_code: str) -> None:
        self.error_code = error_code
