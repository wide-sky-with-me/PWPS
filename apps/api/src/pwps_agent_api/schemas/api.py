from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from pwps_agent_api.schemas.enums import DecisionType, Mode, Publishability, RunStatus
from pwps_agent_api.schemas.models import FieldTarget, PendingUserDecision, TraceEvent


class CreateRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input: str
    mode: Mode = Mode.AUTO
    attachments: list[str] = Field(default_factory=list)


class CreateRunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    status: RunStatus


class RunProgress(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmed_groups: list[str] = Field(default_factory=list)
    remaining_groups: list[str] = Field(default_factory=list)


class RunStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    status: RunStatus
    mode: Mode | None
    current_target: FieldTarget | None
    progress: RunProgress
    publishability: Publishability | None


class RunOutputsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pwps: dict[str, Any]
    field_report: dict[str, Any]
    evidence_report: dict[str, Any]
    risk_report: dict[str, Any]
    discussion_trace: dict[str, Any]
    publishability: Publishability | None


class RunEventsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    events: list[TraceEvent]


class SubmitDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    decision_type: DecisionType
    selected_values: dict[str, Any] = Field(default_factory=dict)
    comment: str | None = None


class SubmitDecisionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    status: RunStatus
    accepted: bool


class CurrentDecisionResponse(PendingUserDecision):
    pass


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error_code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
