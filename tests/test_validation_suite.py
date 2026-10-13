from __future__ import annotations

import json

import pytest

from polynexus.core.project_workflow.validation import ProjectValidationBatch
from polynexus.core.validation_harness import ValidationCase, run_validation
from polynexus.core.validation_suite import (
    ValidationSuiteReport,
    build_validation_suite_report,
)


def _replay_batch() -> ProjectValidationBatch:
    case = ValidationCase.create(
        case_id="public_ir",
        technique="ir",
        canonical_dataset_id="dataset-ir",
        input_payload={"dataset_id": "dataset-ir"},
    )
    report = run_validation(case, lambda _: {"metrics": {"run_status": "completed"}})
    return ProjectValidationBatch(status="passed", reports=(report,))


def _smoke_report() -> dict[str, object]:
    return {
        "schema_version": 1,
        "run_id": "all-modules",
        "entries": [
            {
                "technique": "tga",
                "status": "completed",
                "valid_result": True,
                "route": "thermal_curve_1d.v1 -> tga.processing.v1",
                "core_status": "completed",
                "scientific_use": "parser smoke only",
            },
            {
                "technique": "sec",
                "status": "unavailable",
                "valid_result": False,
                "core_status": "portable_chromatogram_missing",
                "reason": "portable chromatogram missing",
            },
        ],
    }


def test_suite_aggregates_replay_and_smoke_without_scientific_overclaim() -> None:
    report = build_validation_suite_report(
        replay_batch=_replay_batch(),
        replay_source_ref="public-replay.json",
        smoke_report=_smoke_report(),
        smoke_source_ref="all-modules-report.json",
    )

    assert report.status == "complete_with_review"
    assert report.scientific_review_required is True
    assert report.techniques == ("ir", "sec", "tga")
    assert report.coverage == {
        "entry_count": 3,
        "techniques": ["ir", "sec", "tga"],
        "by_kind": {
            "deterministic_replay": 1,
            "smoke_only": 1,
            "unavailable": 1,
        },
        "by_status": {"needs_review": 1, "passed": 1, "unavailable": 1},
        "replay_case_count": 1,
        "replay_count": 2,
    }
    smoke = {item.evidence_id: item for item in report.entries if item.kind != "deterministic_replay"}
    assert smoke["smoke-tga-001"].status == "needs_review"
    assert smoke["smoke-sec-002"].status == "unavailable"
    assert "not an independent scientific validation" in report.limitations[0].lower()


def test_suite_round_trip_rejects_entry_and_derived_coverage_tampering() -> None:
    report = build_validation_suite_report(replay_batch=_replay_batch())
    restored = ValidationSuiteReport.from_dict(report.to_dict())
    assert restored == report

    payload = json.loads(json.dumps(report.to_dict()))
    payload["entries"][0]["technique"] = "tga"
    with pytest.raises(ValueError, match="entry_hash"):
        ValidationSuiteReport.from_dict(payload)

    payload = report.to_dict()
    payload["coverage"]["entry_count"] = 99
    with pytest.raises(ValueError, match="coverage"):
        ValidationSuiteReport.from_dict(payload)


def test_suite_requires_at_least_one_existing_evidence_source() -> None:
    with pytest.raises(ValueError, match="requires a replay batch or smoke report"):
        build_validation_suite_report()
