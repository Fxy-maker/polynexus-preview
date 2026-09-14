from __future__ import annotations

import json
from pathlib import Path

from polynexus.cli.parser import parse_args
from polynexus.cli.run_validation_suite_service import run_validation_suite_cli


def test_validation_suite_cli_aggregates_smoke_report_and_persists_project_report(
    tmp_path: Path,
    capsys,
) -> None:
    smoke = tmp_path / "smoke.json"
    smoke.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "entries": [
                    {
                        "technique": "dma",
                        "status": "completed",
                        "valid_result": True,
                        "route": "dma_curve_1d.v1 -> dma.processing.v1",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    project = tmp_path / "project"
    project.mkdir()
    args = parse_args(
        [
            "validation-suite",
            "--smoke-report",
            str(smoke),
            "--project-root",
            str(project),
            "--json",
        ]
    )

    assert run_validation_suite_cli(args) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "complete_with_review"
    assert payload["coverage"]["by_kind"] == {"smoke_only": 1}
    assert Path(payload["report_path"]).is_file()
    assert (project / ".polynexus" / "validation" / "suite.json").is_file()


def test_validation_suite_cli_requires_a_source(capsys) -> None:
    args = parse_args(["validation-suite", "--json"])

    assert run_validation_suite_cli(args) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["reason_codes"] == ["validation_suite_input_invalid"]
