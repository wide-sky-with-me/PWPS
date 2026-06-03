import json
import subprocess
import sys
from pathlib import Path

SAMPLE_INPUT = "Q345R，12mm，对接焊，平焊，GMAW，生成 pWPS 草案"


def test_auto_draft_cli_writes_outputs(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pwps_agent_api.cli.auto_draft",
            "--input",
            SAMPLE_INPUT,
            "--output-dir",
            str(tmp_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["output_dir"] == str(tmp_path)
    assert sorted(payload["outputs"]) == [
        "discussion_trace",
        "evidence_report",
        "field_report",
        "pwps",
        "render_payload",
        "risk_report",
    ]

    assert (tmp_path / "pwps.json").exists()
    assert (tmp_path / "field_report.json").exists()
    assert (tmp_path / "evidence_report.json").exists()
    assert (tmp_path / "risk_report.json").exists()
    assert (tmp_path / "discussion_trace.json").exists()
    assert (tmp_path / "render_payload.json").exists()
