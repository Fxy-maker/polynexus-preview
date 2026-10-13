from __future__ import annotations

import json
from argparse import Namespace

from polynexus.cli.parser import parse_args
from polynexus.cli.run_agent_workflow_service import run_agent_workflow
from polynexus.core.project_workflow.validation import ProjectValidationEntry
from polynexus.core.validation_harness import ValidationCase, ValidationExpectation


def _entry() -> ProjectValidationEntry:
    case = ValidationCase.create(
        case_id="agent_project_validation",
        technique="tga",
        canonical_dataset_id="dataset-1",
        input_payload={"dataset_id": "dataset-1"},
        expectations=(ValidationExpectation.create(path="metrics.value", expected=1.0),),
    )
    return ProjectValidationEntry.create(
        case=case,
        first_output={"metrics": {"value": 1.0}},
        second_output={"metrics": {"value": 1.0}},
    )


def test_agent_parser_exposes_project_validation_operation() -> None:
    args = parse_args(
        [
            "agent-workflow",
            "validate-project",
            "--project-root",
            "project",
            "--manifest",
            "validation.json",
        ]
    )
    assert args.operation == "validate-project"
    assert args.project_root == "project"


def test_agent_validation_operation_uses_project_batch_and_persists_report(tmp_path, capsys) -> None:
    manifest = tmp_path / "validation.json"
    manifest.write_text(json.dumps({"entries": [_entry().to_dict()]}), encoding="utf-8")

    code = run_agent_workflow(
        Namespace(
            operation="validate-project",
            manifest=str(manifest),
            project_root=str(tmp_path),
            recipe=None,
            run=None,
            output_dir=None,
            export_dir=None,
        )
    )

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["operation"] == "validate-project"
    assert payload["status"] == "passed"
    assert (tmp_path / ".polynexus" / "validation" / "latest.json").is_file()


def test_agent_validation_operation_rejects_invalid_or_failed_manifest(tmp_path, capsys) -> None:
    malformed = tmp_path / "invalid.json"
    malformed.write_text("{}", encoding="utf-8")
    code = run_agent_workflow(
        Namespace(
            operation="validate-project", manifest=str(malformed), project_root=str(tmp_path),
            recipe=None, run=None, output_dir=None, export_dir=None,
        )
    )
    payload = json.loads(capsys.readouterr().out)
    assert code == 2
    assert payload["reason_codes"] == ["project_validation_manifest_invalid"]

    failed = _entry().to_dict()
    failed["first_output"] = {"metrics": {"value": 2.0}}
    # Deliberately omit entry_hash after editing: Agent must parse through the
    # shared integrity gate instead of treating a changed dict as a case.
    failed.pop("entry_hash")
    failed_manifest = tmp_path / "failed.json"
    failed_manifest.write_text(json.dumps({"entries": [failed]}), encoding="utf-8")
    code = run_agent_workflow(
        Namespace(
            operation="validate-project", manifest=str(failed_manifest), project_root=str(tmp_path),
            recipe=None, run=None, output_dir=None, export_dir=None,
        )
    )
    payload = json.loads(capsys.readouterr().out)
    assert code == 2
    assert payload["status"] == "failed"
