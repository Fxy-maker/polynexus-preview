from __future__ import annotations

import pytest

from polynexus.core.validation_harness import (
    ValidationCase,
    ValidationExpectation,
    ValidationReport,
    run_validation,
)


def _case(*expectations: ValidationExpectation, **kwargs) -> ValidationCase:
    return ValidationCase.create(
        case_id=kwargs.pop("case_id", "generic_case"),
        technique=kwargs.pop("technique", "tga"),
        canonical_dataset_id=kwargs.pop("canonical_dataset_id", "dataset-1"),
        input_payload=kwargs.pop("input_payload", {"dataset_id": "dataset-1", "x": [1, 2]}),
        expectations=expectations,
        **kwargs,
    )


def test_validation_case_round_trip_and_hash_rejects_tampering() -> None:
    case = _case(
        ValidationExpectation.create(
            path="metrics.mass_loss",
            expected=12.0,
            absolute_tolerance=0.2,
            unit="%",
            method="normalized",
            parameters={"baseline": "initial"},
            provenance={"source_measurement_id": "mass"},
        ),
        case_kind="standard",
        raw_sha256="a" * 64,
        metadata={"standard_sample": "reference-a"},
    )
    restored = ValidationCase.from_dict(case.to_dict())

    assert restored == case
    assert restored.case_hash == case.case_hash
    payload = case.to_dict()
    payload["input_payload"] = {"dataset_id": "dataset-1", "x": [9, 2]}
    with pytest.raises(ValueError, match="case_hash"):
        ValidationCase.from_dict(payload)


def test_generic_runner_replays_twice_and_compares_metadata_and_raw_hash() -> None:
    raw = {"sha256": "b" * 64}
    case = _case(
        ValidationExpectation.create(
            path="metrics.mass_loss",
            expected=12.0,
            absolute_tolerance=0.1,
            unit="%",
            method="normalized",
            parameters={"baseline": "initial"},
            provenance={"source_measurement_id": "mass"},
        ),
        raw_sha256=raw["sha256"],
    )

    def calculator(payload):
        assert payload["dataset_id"] == "dataset-1"
        return {
            "metrics": {"mass_loss": 12.04},
            "metric_manifest": [
                {
                    "path": "metrics.mass_loss",
                    "kind": "scalar",
                    "status": "computed",
                    "unit": "%",
                    "method": "normalized",
                    "parameters": {"baseline": "initial"},
                    "provenance": {"source_measurement_id": "mass"},
                    "value": 12.04,
                }
            ],
        }

    report = run_validation(case, calculator, raw_hash_provider=lambda: raw["sha256"])

    assert report.status == "passed"
    assert report.replay_count == 2
    assert report.deterministic is True
    assert report.raw_preservation["before_matches_expected"] is True
    assert report.raw_preservation["after_matches_before"] is True
    assert report.metric_comparisons[0]["status"] == "passed"
    assert ValidationReport.from_dict(report.to_dict()) == report


def test_series_tolerance_and_unavailable_status_are_explicit() -> None:
    case = _case(
        ValidationExpectation.create(
            path="metrics.curve",
            expected=[1.0, 2.0, 3.0],
            absolute_tolerance=0.01,
        ),
        ValidationExpectation.create(
            path="metrics.optional",
            expected=None,
            expected_status="unavailable",
        ),
    )

    report = run_validation(
        case,
        lambda _: {
            "metrics": {"curve": [1.005, 2.0, 3.0], "optional": None},
        },
    )

    assert report.status == "passed"
    assert [item["status"] for item in report.metric_comparisons] == ["passed", "passed"]


def test_mismatch_only_changes_report_and_does_not_mutate_input_or_run() -> None:
    case = _case(
        ValidationExpectation.create(path="metrics.value", expected=10.0, absolute_tolerance=0.01),
        input_payload={"dataset_id": "dataset-1", "value": 4},
    )
    original = case.input_payload
    run_marker = {"changed": False}

    def calculator(payload):
        payload["value"] = 999
        run_marker["changed"] = True
        return {"metrics": {"value": 8.0}}

    report = run_validation(case, calculator)

    assert report.status == "failed"
    assert "expected_metric_mismatch" in report.reason_codes
    assert dict(case.input_payload) == dict(original)
    assert run_marker["changed"] is True


def test_failed_calculator_and_cross_technique_reuse() -> None:
    failing = _case(case_id="failed_case", technique="nmr")
    failed_report = run_validation(failing, lambda _: (_ for _ in ()).throw(RuntimeError("boom")))
    assert failed_report.status == "failed"
    assert "replay_execution_failed" in failed_report.reason_codes

    rheology = _case(
        ValidationExpectation.create(path="metrics.tan_delta", expected=[0.5, 0.25]),
        case_id="rheology_case",
        technique="rheology",
        input_payload={"dataset_id": "dataset-1", "frequency": [1.0, 2.0]},
    )
    report = run_validation(
        rheology,
        lambda _: {"metrics": {"tan_delta": [0.5, 0.25]}},
    )
    assert report.status == "passed"
    assert report.technique == "rheology"


def test_case_requires_canonical_binding_and_optional_standard_metadata() -> None:
    with pytest.raises(ValueError, match="canonical_dataset_id"):
        ValidationCase.create(
            case_id="bad",
            technique="tga",
            canonical_dataset_id="",
            input_payload={"x": [1, 2]},
        )

    case = _case(case_kind="negative_control", metadata={"negative_control": "blank"})
    assert case.case_kind == "negative_control"
    assert case.metadata["negative_control"] == "blank"
