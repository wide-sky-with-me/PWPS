from pwps_agent_api.audit.engine import AuditEngine
from pwps_agent_api.audit.repair import build_repair_targets
from pwps_agent_api.fields import load_default_field_registry
from pwps_agent_api.schemas import (
    Evidence,
    FieldState,
    FieldStatus,
    InferencePolicy,
    Publishability,
    SourceType,
)


def test_high_risk_field_with_low_credibility_evidence_needs_confirmation() -> None:
    registry = load_default_field_registry()
    fields = {
        "consumable": FieldState(
            name="consumable",
            group="consumable_group",
            value="ER50-6",
            status=FieldStatus.CONFIRMED,
            source_type=SourceType.LOCAL_DOCUMENT,
            inference_policy=InferencePolicy.MODEL_ALLOWED,
            evidence_ids=["evidence-consumable"],
        )
    }
    evidence = {
        "evidence-consumable": Evidence(
            evidence_id="evidence-consumable",
            source_type=SourceType.LOCAL_DOCUMENT,
            source_title="Bundled drafting reference",
            section_path=["GMAW"],
            content="Review ER50-6 as a candidate value.",
            target_fields=["consumable"],
            credibility=0.65,
            limitations="Drafting reference only.",
            retrieved_at="2026-06-01T00:00:00Z",
        )
    }

    result = AuditEngine().audit(fields, registry, evidence)

    assert result.publishability is Publishability.NEEDS_CONFIRMATION
    assert {issue.source_rule for issue in result.issues} >= {"low_credibility_evidence"}


def test_repair_targets_deduplicate_issue_groups_and_mark_fields_for_repair() -> None:
    registry = load_default_field_registry()
    fields = {
        "welding_process": FieldState(
            name="welding_process",
            group="basic_condition_group",
            value="GMAW",
            status=FieldStatus.PROVIDED,
            source_type=SourceType.USER_INPUT,
            inference_policy=InferencePolicy.MODEL_ALLOWED,
        ),
        "consumable": FieldState(
            name="consumable",
            group="consumable_group",
            value="J422",
            status=FieldStatus.CONFIRMED,
            source_type=SourceType.USER_INPUT,
            inference_policy=InferencePolicy.MODEL_ALLOWED,
        ),
    }
    result = AuditEngine().audit(fields, registry, {})

    targets = build_repair_targets(result, registry, fields)

    assert [target.group_name for target in targets] == [
        "consumable_group",
        "basic_condition_group",
        "parameter_group",
        "thermal_group",
    ]
    assert targets[0].source_issue_id == "process-consumable-match"
    assert fields["consumable"].status is FieldStatus.NEEDS_REPAIR
