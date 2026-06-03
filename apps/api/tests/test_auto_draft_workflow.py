import json
from pathlib import Path
from typing import Any, cast

from pwps_agent_api.schemas import FieldStatus, Publishability, RunStatus, SourceType
from pwps_agent_api.workflow.auto import run_auto_draft

SAMPLE_INPUT = "Q345R，12mm，对接焊，平焊，GMAW，生成 pWPS 草案"


def _load_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


async def test_auto_draft_writes_required_outputs(tmp_path: Path) -> None:
    result = await run_auto_draft(SAMPLE_INPUT, tmp_path)

    assert result.state.status is RunStatus.FINISHED
    assert result.output_paths["pwps"].name == "pwps.json"
    assert sorted(path.name for path in result.output_paths.values()) == [
        "discussion_trace.json",
        "evidence_report.json",
        "field_report.json",
        "pwps.json",
        "render_payload.json",
        "risk_report.json",
    ]
    for path in result.output_paths.values():
        assert path.exists()


async def test_auto_draft_extracts_sample_fields_and_keeps_meta_empty(tmp_path: Path) -> None:
    await run_auto_draft(SAMPLE_INPUT, tmp_path)

    pwps = _load_json(tmp_path / "pwps.json")
    field_report = _load_json(tmp_path / "field_report.json")

    assert pwps["mode"] == "auto"
    assert pwps["publishability"] == Publishability.NEEDS_CONFIRMATION
    assert pwps["fields"]["base_material"]["value"] == "Q345R"
    assert pwps["fields"]["thickness"]["value"] == "12mm"
    assert pwps["fields"]["welding_process"]["value"] == "GMAW"
    assert pwps["fields"]["joint_type"]["value"] == "对接焊"
    assert pwps["fields"]["welding_position"]["value"] == "平焊"
    assert pwps["fields"]["project_name"]["value"] is None
    assert pwps["fields"]["client_name"]["value"] is None
    assert pwps["fields"]["document_number"]["value"] is None

    assert field_report["field_states"]["base_material"]["status"] == FieldStatus.PROVIDED
    assert field_report["field_states"]["consumable"]["value"] == "ER50-6"
    assert field_report["field_states"]["consumable"]["status"] == FieldStatus.CONFIRMED


async def test_auto_draft_records_risks_and_discussion_trace(tmp_path: Path) -> None:
    await run_auto_draft(SAMPLE_INPUT, tmp_path)

    risk_report = _load_json(tmp_path / "risk_report.json")
    discussion_trace = _load_json(tmp_path / "discussion_trace.json")

    issue_rules = {issue["source_rule"] for issue in risk_report["issues"]}
    assert "high_risk_auto_confirmation" in issue_rules
    assert risk_report["publishability"] == Publishability.NEEDS_CONFIRMATION

    assert discussion_trace["trace"]
    assert discussion_trace["discussion_sessions"]
    assert {session["target_fields"][0] for session in discussion_trace["discussion_sessions"]} >= {
        "base_material",
        "consumable",
        "current_range",
        "preheat_temperature",
    }


async def test_auto_draft_attaches_local_document_evidence_to_supported_fields(
    tmp_path: Path,
) -> None:
    result = await run_auto_draft(SAMPLE_INPUT, tmp_path)

    consumable = result.state.field_states["consumable"]
    evidence = [result.state.evidence_store[item] for item in consumable.evidence_ids]

    assert consumable.source_type is SourceType.LOCAL_DOCUMENT
    assert evidence
    assert {item.source_type for item in evidence} == {SourceType.LOCAL_DOCUMENT}
    assert all(item.section_path for item in evidence)
    assert all(item.limitations for item in evidence)
