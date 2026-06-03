"""Tests for GuardValidator — output validation layer."""

import pytest

from pwps_agent_api.guard import GuardValidator
from pwps_agent_api.schemas import (
    ConfirmationPolicy,
    Evidence,
    FieldSpec,
    FieldState,
    FieldStatus,
    FieldType,
    InferencePolicy,
    SourceType,
)


@pytest.fixture
def validator() -> GuardValidator:
    return GuardValidator()


@pytest.fixture
def provided_only_spec() -> FieldSpec:
    return FieldSpec(
        name="project_name",
        label="项目名称",
        group="meta_group",
        field_type=FieldType.STRING,
        description="Project name",
        inference_policy=InferencePolicy.PROVIDED_ONLY,
        confirmation_policy=ConfirmationPolicy.NEVER_INFER,
    )


@pytest.fixture
def high_risk_spec() -> FieldSpec:
    return FieldSpec(
        name="current_range",
        label="电流",
        group="parameter_group",
        field_type=FieldType.RANGE,
        description="Welding current range",
        high_risk=True,
        inference_policy=InferencePolicy.EVIDENCE_REQUIRED,
        confirmation_policy=ConfirmationPolicy.ALWAYS_CONFIRM,
    )


@pytest.fixture
def normal_spec() -> FieldSpec:
    return FieldSpec(
        name="joint_type",
        label="接头形式",
        group="basic_condition_group",
        field_type=FieldType.STRING,
        description="Joint type",
        inference_policy=InferencePolicy.MODEL_ALLOWED,
    )


class TestProvidedOnlyValidation:
    def test_provided_only_filled_by_user_is_ok(
        self, validator: GuardValidator, provided_only_spec: FieldSpec
    ) -> None:
        state = FieldState(
            name="project_name",
            group="meta_group",
            value="Project A",
            status=FieldStatus.CONFIRMED,
            source_type=SourceType.USER_INPUT,
            inference_policy=InferencePolicy.PROVIDED_ONLY,
        )
        violations = validator.validate_field_state(state, provided_only_spec)
        assert len(violations) == 0

    def test_provided_only_filled_by_model_is_violation(
        self, validator: GuardValidator, provided_only_spec: FieldSpec
    ) -> None:
        state = FieldState(
            name="project_name",
            group="meta_group",
            value="Project A",
            status=FieldStatus.CONFIRMED,
            source_type=SourceType.MODEL_PRIOR,
            inference_policy=InferencePolicy.PROVIDED_ONLY,
        )
        violations = validator.validate_field_state(state, provided_only_spec)
        assert len(violations) == 1
        assert violations[0].rule == "provided_only_violation"


class TestHighRiskValidation:
    def test_high_risk_with_evidence_is_ok(
        self, validator: GuardValidator, high_risk_spec: FieldSpec
    ) -> None:
        state = FieldState(
            name="current_range",
            group="parameter_group",
            value={"min": "180A", "max": "240A"},
            status=FieldStatus.CONFIRMED,
            source_type=SourceType.LOCAL_STANDARD,
            inference_policy=InferencePolicy.EVIDENCE_REQUIRED,
            evidence_ids=["ev-1"],
        )
        evidence_store = {
            "ev-1": Evidence(
                evidence_id="ev-1",
                source_type=SourceType.LOCAL_STANDARD,
                source_title="NB/T 47014",
                content="...",
                target_fields=["current_range"],
                credibility=0.8,
                retrieved_at="2026-01-01T00:00:00Z",
            )
        }
        violations = validator.validate_field_state(state, high_risk_spec, evidence_store)
        assert len(violations) == 0

    def test_high_risk_without_evidence_is_violation(
        self, validator: GuardValidator, high_risk_spec: FieldSpec
    ) -> None:
        state = FieldState(
            name="current_range",
            group="parameter_group",
            value={"min": "180A", "max": "240A"},
            status=FieldStatus.CONFIRMED,
            source_type=SourceType.MODEL_PRIOR,
            inference_policy=InferencePolicy.EVIDENCE_REQUIRED,
            evidence_ids=[],
        )
        violations = validator.validate_field_state(state, high_risk_spec)
        assert len(violations) == 1
        assert violations[0].rule == "high_risk_no_evidence"

    def test_high_risk_with_low_credibility_evidence_is_warning(
        self, validator: GuardValidator, high_risk_spec: FieldSpec
    ) -> None:
        state = FieldState(
            name="current_range",
            group="parameter_group",
            value={"min": "180A", "max": "240A"},
            status=FieldStatus.CONFIRMED,
            source_type=SourceType.MODEL_PRIOR,
            inference_policy=InferencePolicy.EVIDENCE_REQUIRED,
            evidence_ids=["ev-1"],
        )
        evidence_store = {
            "ev-1": Evidence(
                evidence_id="ev-1",
                source_type=SourceType.MODEL_PRIOR,
                source_title="Model prior",
                content="...",
                target_fields=["current_range"],
                credibility=0.35,
                retrieved_at="2026-01-01T00:00:00Z",
            )
        }
        violations = validator.validate_field_state(state, high_risk_spec, evidence_store)
        assert any(v.rule == "low_credibility_evidence" for v in violations)
        assert all(
            v.severity == "warning"
            for v in violations
            if v.rule == "low_credibility_evidence"
        )


class TestCandidateValidation:
    def test_candidate_for_provided_only_is_violation(
        self, validator: GuardValidator, provided_only_spec: FieldSpec
    ) -> None:
        violations = validator.validate_candidate(
            "project_name",
            {"value": "Project A", "confidence": 0.5, "reason": "test", "evidence_ids": []},
            provided_only_spec,
        )
        assert len(violations) == 1
        assert violations[0].rule == "candidate_for_provided_only"

    def test_candidate_for_normal_field_is_ok(
        self, validator: GuardValidator, normal_spec: FieldSpec
    ) -> None:
        violations = validator.validate_candidate(
            "joint_type",
            {"value": "对接焊", "confidence": 0.8, "reason": "test", "evidence_ids": ["ev-1"]},
            normal_spec,
        )
        assert len(violations) == 0


class TestStateTransition:
    def test_confirmed_without_source_or_evidence_is_violation(
        self, validator: GuardValidator, normal_spec: FieldSpec
    ) -> None:
        state = FieldState(
            name="joint_type",
            group="basic_condition_group",
            value="对接焊",
            status=FieldStatus.CONFIRMED,
            source_type=None,
            inference_policy=InferencePolicy.MODEL_ALLOWED,
            evidence_ids=[],
        )
        violations = validator.validate_field_state(state, normal_spec)
        assert any(v.rule == "invalid_confirmation" for v in violations)
