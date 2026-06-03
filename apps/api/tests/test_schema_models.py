import pytest
from pydantic import ValidationError

from pwps_agent_api.schemas import (
    AuditResult,
    Evidence,
    FieldState,
    FieldStatus,
    InferencePolicy,
    Mode,
    Publishability,
    RiskLevel,
    RunStatus,
    SourceType,
    WorkflowState,
)


def test_field_state_rejects_unknown_attributes() -> None:
    with pytest.raises(ValidationError):
        FieldState.model_validate(
            {
                "name": "base_material",
                "group": "basic_condition_group",
                "inference_policy": InferencePolicy.MODEL_ALLOWED,
                "unsupported": "not allowed",
            }
        )


def test_workflow_state_serializes_nested_enum_values() -> None:
    state = WorkflowState(
        run_id="run-001",
        status=RunStatus.FIELD_CONFIRMING,
        raw_input="Q345R, 12mm, GMAW",
        mode=Mode.AUTO,
        field_states={
            "base_material": FieldState(
                name="base_material",
                group="basic_condition_group",
                value="Q345R",
                status=FieldStatus.PROVIDED,
                source_type=SourceType.USER_INPUT,
                inference_policy=InferencePolicy.MODEL_ALLOWED,
                confidence=1.0,
            )
        },
        evidence_store={
            "ev-001": Evidence(
                evidence_id="ev-001",
                source_type=SourceType.MODEL_PRIOR,
                source_title="MVP model prior",
                content="Q345R is treated as the provided base material.",
                target_fields=["base_material"],
                credibility=0.5,
                retrieved_at="2026-06-01T12:00:00Z",
            )
        },
        audit_result=AuditResult(
            publishability=Publishability.NEEDS_CONFIRMATION,
            summary="Draft requires human confirmation.",
        ),
    )

    dumped = state.model_dump(mode="json")
    restored = WorkflowState.model_validate(dumped)

    assert dumped["status"] == "field_confirming"
    assert dumped["mode"] == "auto"
    assert dumped["field_states"]["base_material"]["status"] == "provided"
    assert restored.status is RunStatus.FIELD_CONFIRMING
    assert restored.field_states["base_material"].source_type is SourceType.USER_INPUT


def test_high_risk_field_state_tracks_human_confirmation_need() -> None:
    field_state = FieldState(
        name="pwht",
        group="thermal_group",
        status=FieldStatus.CANDIDATE_GENERATED,
        inference_policy=InferencePolicy.EVIDENCE_REQUIRED,
        risk_level=RiskLevel.HIGH,
        needs_human_confirmation=True,
    )

    assert field_state.risk_level is RiskLevel.HIGH
    assert field_state.needs_human_confirmation is True
