from __future__ import annotations

import json

import pytest

from polynexus.core.project_workflow.validation import (
    ProjectValidationBatch,
    ProjectValidationEntry,
    run_project_validation_batch,
)
from polynexus.core.project_workflow.workspace import ProjectWorkspace
from polynexus.core.validation_harness import ValidationCase, ValidationExpectation
from polynexus.cli.parser import parse_args
from polynexus.cli.run_project_validation_service import run_project_validation_cli


def _case(case_id: str, technique: str, expected: float) -> ValidationCase:
    return ValidationCase.create(
        case_id=case_id,
        technique=technique,
        canonical_dataset_id=f"dataset-{case_id}",
        input_payload={"dataset_id": f"dataset-{case_id}"},
        expectations=(ValidationExpectation.create(path="metrics.value", expected=expected),),
    )


def test_project_batch_aggregates_multiple_techniques_and_round_trips() -> None:
    entries = (
        ProjectValidationEntry.create(
            case=_case("tga_case", "tga", 1.0),
            first_output={"metrics": {"value": 1.0}},
            second_output={"metrics": {"value": 1.0}},
        ),
        ProjectValidationEntry.create(
            case=_case("rheo_case", "rheology", 2.0),
            first_output={"metrics": {"value": 2.0}},
            second_output={"metrics": {"value": 2.0}},
        ),
    )

    batch = run_project_validation_batch(entries)

    assert batch.status == "passed"
    assert batch.techniques == ("rheology", "tga")
    assert [item.status for item in batch.reports] == ["passed", "passed"]
    assert ProjectValidationBatch.from_dict(batch.to_dict()) == batch


def test_project_batch_retains_failure_without_blocking_other_cases() -> None:
    entries = (
        ProjectValidationEntry.create(
            case=_case("bad", "dsc", 10.0),
            first_output={"metrics": {"value": 1.0}},
            second_output={"metrics": {"value": 1.0}},
        ),
        ProjectValidationEntry.create(
            case=_case("good", "nmr", 2.0),
            first_output={"metrics": {"value": 2.0}},
            second_output={"metrics": {"value": 2.0}},
        ),
    )
    batch = run_project_validation_batch(entries)

    assert batch.status == "failed"
    assert [item.status for item in batch.reports] == ["failed", "passed"]


def test_project_batch_rejects_entry_tampering_and_workspace_writes_derived_only(tmp_path) -> None:
    entry = ProjectValidationEntry.create(
        case=_case("one", "tga", 1.0),
        first_output={"metrics": {"value": 1.0}},
        second_output={"metrics": {"value": 1.0}},
    )
    payload = entry.to_dict()
    payload["first_output"] = {"metrics": {"value": 9.0}}
    with pytest.raises(ValueError, match="entry_hash"):
        ProjectValidationEntry.from_dict(payload)

    workspace = ProjectWorkspace.open(tmp_path)
    path = workspace.write_validation_batch(run_project_validation_batch((entry,)))
    assert path == tmp_path / ".polynexus" / "validation" / "latest.json"
    assert json.loads(path.read_text(encoding="utf-8"))["status"] == "passed"
    with pytest.raises(ValueError):
        workspace.write_json(tmp_path / "raw" / "validation.json", {"status": "bad"})


def test_project_validation_cli_persists_batch_report(tmp_path, capsys) -> None:
    entry = ProjectValidationEntry.create(
        case=_case("cli", "nmr", 3.0),
        first_output={"metrics": {"value": 3.0}},
        second_output={"metrics": {"value": 3.0}},
    )
    manifest = tmp_path / "validation.json"
    manifest.write_text(json.dumps({"entries": [entry.to_dict()]}), encoding="utf-8")
    args = parse_args(["project-validate", "--project-root", str(tmp_path), "--manifest", str(manifest), "--json"])
    assert args.cmd == "project-validate"
    assert run_project_validation_cli(args) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "passed"
    assert (tmp_path / ".polynexus" / "validation" / "latest.json").is_file()
