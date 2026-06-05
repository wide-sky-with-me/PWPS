import asyncio
import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from pwps_agent_api.db.session import get_session
from pwps_agent_api.events import EventStore
from pwps_agent_api.events.store import get_event_store
from pwps_agent_api.schemas.api import (
    CreateRunRequest,
    CreateRunResponse,
    CurrentDecisionResponse,
    ErrorResponse,
    ListRunsResponse,
    RunEventsResponse,
    RunOutputsResponse,
    RunStatusResponse,
    SubmitDecisionRequest,
    SubmitDecisionResponse,
)
from pwps_agent_api.services.run_service import GuidedDecisionStateError, build_run_service

router = APIRouter(prefix="/api/runs", tags=["runs"])


class RunApiError(Exception):
    def __init__(self, *, status_code: int, error: ErrorResponse) -> None:
        self.status_code = status_code
        self.error = error


@router.get("", response_model=ListRunsResponse)
async def list_runs(
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: int = 50,
    offset: int = 0,
) -> ListRunsResponse:
    service = build_run_service(session)
    return await service.list_runs(limit=limit, offset=offset)


@router.post("", response_model=CreateRunResponse)
async def create_run(
    request: CreateRunRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    event_store: Annotated[EventStore, Depends(get_event_store)],
) -> CreateRunResponse:
    service = build_run_service(session, event_store=event_store)
    return await service.create_run(request)


@router.get(
    "/{run_id}",
    response_model=RunStatusResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_run(
    run_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RunStatusResponse:
    service = build_run_service(session)
    response = await service.status_response(run_id)
    if response is None:
        raise _run_not_found(run_id)
    return response


@router.get(
    "/{run_id}/outputs",
    response_model=RunOutputsResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_run_outputs(
    run_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RunOutputsResponse:
    service = build_run_service(session)
    response = await service.outputs_response(run_id)
    if response is None:
        raise _run_not_found(run_id)
    return response


@router.get(
    "/{run_id}/events",
    response_model=RunEventsResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_run_events(
    run_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    event_store: Annotated[EventStore, Depends(get_event_store)],
) -> RunEventsResponse:
    service = build_run_service(session, event_store=event_store)
    response = await service.events_response(run_id)
    if response is None:
        raise _run_not_found(run_id)
    return response


@router.get(
    "/{run_id}/events/stream",
    responses={404: {"model": ErrorResponse}},
)
async def stream_run_events(
    run_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    event_store: Annotated[EventStore, Depends(get_event_store)],
) -> StreamingResponse:
    """SSE endpoint for real-time run progress events."""

    async def event_generator() -> Any:
        service = build_run_service(session, event_store=event_store)
        if await service.get_run(run_id) is None:
            yield f"event: error\ndata: {json.dumps({'error': 'RUN_NOT_FOUND'})}\n\n"
            return
        service = build_run_service(session, event_store=event_store)
        if await service.get_run(run_id) is None:
            yield f"event: error\ndata: {json.dumps({'error': 'RUN_NOT_FOUND'})}\n\n"
            return

        last_index = 0
        while True:
            response = await service.events_response(run_id)
            if response is None:
                break

            events = response.events
            if len(events) > last_index:
                for event in events[last_index:]:
                    yield f"event: trace\ndata: {event.model_dump_json()}\n\n"
                last_index = len(events)

            # Check if run is finished
            status_response = await service.status_response(run_id)
            if status_response and status_response.status in ("finished", "blocked"):
                done_data = json.dumps({"status": status_response.status.value})
                yield f"event: done\ndata: {done_data}\n\n"
                break

            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/{run_id}/current-decision",
    response_model=CurrentDecisionResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def get_current_decision(
    run_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CurrentDecisionResponse:
    service = build_run_service(session)
    if await service.get_run(run_id) is None:
        raise _run_not_found(run_id)
    response = await service.current_decision_response(run_id)
    if response is None:
        raise _run_api_error(
            "INVALID_STATE_TRANSITION",
            "Run is not waiting for a user decision.",
            run_id,
        )
    return response


@router.post(
    "/{run_id}/decision",
    response_model=SubmitDecisionResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def submit_decision(
    run_id: str,
    request: SubmitDecisionRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    event_store: Annotated[EventStore, Depends(get_event_store)],
) -> SubmitDecisionResponse:
    service = build_run_service(session, event_store=event_store)
    try:
        response = await service.submit_decision(run_id, request)
    except GuidedDecisionStateError as exc:
        message = (
            "Decision session is expired."
            if exc.error_code == "DECISION_SESSION_EXPIRED"
            else "Run is not waiting for a user decision."
        )
        raise _run_api_error(exc.error_code, message, run_id) from exc
    if response is None:
        raise _run_not_found(run_id)
    return response


def _run_not_found(run_id: str) -> RunApiError:
    return _run_api_error("RUN_NOT_FOUND", "Run not found.", run_id, status_code=404)


def _run_api_error(
    error_code: str,
    message: str,
    run_id: str,
    *,
    status_code: int = 409,
) -> RunApiError:
    return RunApiError(
        status_code=status_code,
        error=ErrorResponse(
            error_code=error_code,
            message=message,
            details={"run_id": run_id},
        ),
    )
