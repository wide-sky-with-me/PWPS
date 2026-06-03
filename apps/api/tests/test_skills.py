"""Tests for LLM Skills.

Tests both the LLM path (when API key is configured) and the deterministic
fallback path (when no API key is available).
"""

import json
from pathlib import Path
from typing import Any

import pytest

from pwps_agent_api.schemas import FieldStatus, InferencePolicy, SourceType
from pwps_agent_api.skills.candidate_generation import CandidateGenerationSkill
from pwps_agent_api.skills.requirement_understanding import RequirementUnderstandingSkill

_EVAL_DATASET = Path(__file__).parent / "eval" / "dataset.json"


def _load_eval_cases(category: str | None = None) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = json.loads(_EVAL_DATASET.read_text(encoding="utf-8"))
    if category:
        cases = [c for c in cases if c["category"] == category]
    return cases


# --- RequirementUnderstandingSkill tests ---


async def test_understanding_extracts_material_and_thickness() -> None:
    skill = RequirementUnderstandingSkill()
    result = await skill.run("Q345R，12mm，对接焊，平焊，GMAW，生成 pWPS 草案")

    assert "base_material" in result
    assert result["base_material"].value == "Q345R"
    assert result["base_material"].source_type is SourceType.USER_INPUT
    assert result["base_material"].status is FieldStatus.PROVIDED


async def test_understanding_extracts_welding_process() -> None:
    skill = RequirementUnderstandingSkill()
    result = await skill.run("Q345R，12mm，GMAW")

    assert "welding_process" in result
    assert result["welding_process"].value == "GMAW"


async def test_understanding_extracts_joint_and_position() -> None:
    skill = RequirementUnderstandingSkill()
    result = await skill.run("对接焊，平焊")

    assert "joint_type" in result
    assert result["joint_type"].value == "对接焊"
    assert "welding_position" in result
    assert result["welding_position"].value == "平焊"


async def test_understanding_does_not_fabricate_unmentioned_fields() -> None:
    skill = RequirementUnderstandingSkill()
    result = await skill.run("Q345R，GMAW")

    # Should NOT extract thickness, joint_type, position if not mentioned
    assert "thickness" not in result
    assert "joint_type" not in result
    assert "welding_position" not in result


async def test_understanding_handles_english_input() -> None:
    skill = RequirementUnderstandingSkill()
    result = await skill.run("Q345R, 12mm, butt joint, flat position, GMAW")

    assert "base_material" in result
    assert result["base_material"].value == "Q345R"
    assert "welding_process" in result
    assert result["welding_process"].value == "GMAW"


async def test_understanding_all_fields_have_correct_status() -> None:
    skill = RequirementUnderstandingSkill()
    result = await skill.run("Q345R，12mm，GMAW")

    for _field_name, field_state in result.items():
        assert field_state.status is FieldStatus.PROVIDED
        assert field_state.source_type is SourceType.USER_INPUT
        assert field_state.confidence == 1.0


# --- CandidateGenerationSkill tests ---


async def test_candidate_generation_skips_provided_only_fields() -> None:
    skill = CandidateGenerationSkill()
    from pwps_agent_api.fields import load_default_field_registry
    from pwps_agent_api.schemas import FieldState

    registry = load_default_field_registry()
    field_states = {
        "project_name": FieldState(
            name="project_name",
            group="meta_group",
            value=None,
            status=FieldStatus.UNKNOWN,
            inference_policy=InferencePolicy.PROVIDED_ONLY,
        )
    }

    result = await skill.run(
        target_fields=["project_name"],
        field_states=field_states,
        evidence=[],
        registry=registry,
    )

    assert "project_name" not in result


async def test_candidate_generation_skips_confirmed_fields() -> None:
    skill = CandidateGenerationSkill()
    from pwps_agent_api.fields import load_default_field_registry
    from pwps_agent_api.schemas import FieldState

    registry = load_default_field_registry()
    field_states = {
        "consumable": FieldState(
            name="consumable",
            group="consumable_group",
            value="ER50-6",
            status=FieldStatus.CONFIRMED,
            inference_policy=InferencePolicy.MODEL_ALLOWED,
        )
    }

    result = await skill.run(
        target_fields=["consumable"],
        field_states=field_states,
        evidence=[],
        registry=registry,
    )

    assert "consumable" not in result


async def test_candidate_generation_generates_for_needs_repair_fields() -> None:
    skill = CandidateGenerationSkill()
    from pwps_agent_api.fields import load_default_field_registry
    from pwps_agent_api.schemas import FieldState

    registry = load_default_field_registry()
    field_states = {
        "consumable": FieldState(
            name="consumable",
            group="consumable_group",
            value="J422",
            status=FieldStatus.NEEDS_REPAIR,
            inference_policy=InferencePolicy.MODEL_ALLOWED,
        )
    }

    result = await skill.run(
        target_fields=["consumable"],
        field_states=field_states,
        evidence=[],
        registry=registry,
    )

    assert "consumable" in result
    assert len(result["consumable"]) > 0


async def test_candidate_generation_candidates_have_required_keys() -> None:
    skill = CandidateGenerationSkill()
    from pwps_agent_api.fields import load_default_field_registry

    registry = load_default_field_registry()

    result = await skill.run(
        target_fields=["consumable", "current_range"],
        field_states={},
        evidence=[],
        registry=registry,
    )

    for _field_name, candidates in result.items():
        for candidate in candidates:
            assert "value" in candidate
            assert "confidence" in candidate
            assert "reason" in candidate
            assert "risks" in candidate


async def test_candidate_generation_confidence_in_range() -> None:
    skill = CandidateGenerationSkill()
    from pwps_agent_api.fields import load_default_field_registry

    registry = load_default_field_registry()

    result = await skill.run(
        target_fields=["consumable"],
        field_states={},
        evidence=[],
        registry=registry,
    )

    for candidates in result.values():
        for candidate in candidates:
            assert 0 <= candidate["confidence"] <= 1


# --- Evaluation dataset tests ---


@pytest.mark.parametrize(
    "case",
    _load_eval_cases("normal"),
    ids=[c["id"] for c in _load_eval_cases("normal")],
)
async def test_eval_normal_cases(case: dict[str, Any]) -> None:
    skill = RequirementUnderstandingSkill()
    result = await skill.run(case["input"])

    for field_name, expected_value in case["expected_fields"].items():
        if expected_value is not None:
            assert field_name in result, f"Expected field '{field_name}' not extracted"
            assert result[field_name].value == expected_value


@pytest.mark.parametrize(
    "case",
    _load_eval_cases("fabrication_risk"),
    ids=[c["id"] for c in _load_eval_cases("fabrication_risk")],
)
async def test_eval_fabrication_risk_cases(case: dict[str, Any]) -> None:
    skill = RequirementUnderstandingSkill()
    result = await skill.run(case["input"])

    for field_name, expected_value in case["expected_fields"].items():
        if expected_value is None:
            # These fields should NOT be fabricated
            if field_name in result:
                assert result[field_name].value is None or field_name not in result
