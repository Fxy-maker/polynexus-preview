from __future__ import annotations

import json
from argparse import Namespace

from polynexus.cli.parser import parse_args
from polynexus.cli.run_validation_service import run_validation_cli
from polynexus.core.validation_harness import ValidationCase, ValidationExpectation


def test_cli_parser_exposes_validation_compare() -> None:
    args = parse_args(
        [
            "validate",
            "compare",
            "--case",
            "case.json",
            "--first-output",
            "first.json",
            "--second-output",
            "second.json",
            "--json",
        ]
    )
    assert args.cmd == "validate"
    assert args.operation == "compare"
    assert args.first_output == "first.json"


def test_cli_validation_compares_persisted_outputs(tmp_path, capsys) -> None:
    case = ValidationCase.create(
        case_id="cli_case",
        technique="tga",
        canonical_dataset_id="dataset-1",
        input_payload={"dataset_id": "dataset-1", "source": "canonical"},
        expectations=(
            ValidationExpectation.create(
                path="metrics.mass_loss",
                expected=12.0,
                absolute_tolerance=0.1,
                expected_status="computed",
            ),
        ),
        raw_sha256="a" * 64,
    )
    first = {"metrics": {"mass_loss": 12.04}}
    second = {"metrics": {"mass_loss": 12.04}}
    case_path = tmp_path / "case.json"
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"
    case_path.write_text(json.dumps(case.to_dict()), encoding="utf-8")
    first_path.write_text(json.dumps(first), encoding="utf-8")
    second_path.write_text(json.dumps(second), encoding="utf-8")

    exit_code = run_validation_cli(
        Namespace(
            case=str(case_path),
            first_output=str(first_path),
            second_output=str(second_path),
            raw_hash_before="a" * 64,
            raw_hash_after="a" * 64,
            json=True,
        )
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "passed"
    assert payload["deterministic"] is True
    assert payload["metric_comparisons"][0]["status"] == "passed"


def test_cli_validation_returns_nonzero_and_json_for_bad_case(tmp_path, capsys) -> None:
    bad_case = tmp_path / "bad.json"
    output = tmp_path / "output.json"
    bad_case.write_text("{}", encoding="utf-8")
    output.write_text("{}", encoding="utf-8")
    exit_code = run_validation_cli(
        Namespace(
            case=str(bad_case),
            first_output=str(output),
            second_output=str(output),
            raw_hash_before=None,
            raw_hash_after=None,
            json=True,
        )
    )
    assert exit_code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "failed"
    assert payload["reason_codes"] == ["validation_cli_input_invalid"]
