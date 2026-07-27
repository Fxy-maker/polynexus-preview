from __future__ import annotations

import json

import numpy as np

from polynexus.core.saxs_engine.saxs_quality_contracts import (
    DataQualityReport,
    GuinierEvidence,
    MetricEvidence,
    QualityLevel,
    RescueCandidate,
    RescueValidationReport,
    build_data_quality_report,
)
from tests.fixtures.saxs_quality_cases import (
    clean_guinier_case,
    dirty_guinier_case,
    low_q_truncated_case,
)


def test_quality_report_counts_faults_without_mutating_input_arrays():
    q = np.asarray(
        [0.01, 0.02, np.nan, 0.02, 0.04, 0.03, 0.05, 0.06, 0.07, 0.08,
         0.09, 0.10, 0.11, 0.12, 0.13]
    )
    intensity = np.asarray(
        [10.0, -1.0, 2.0, np.nan, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0,
         10.0, 11.0, 12.0, 13.0, 14.0]
    )
    q_before = q.copy()
    intensity_before = intensity.copy()

    report = build_data_quality_report(q, intensity, source_id="frame-003")

    assert np.array_equal(q, q_before, equal_nan=True)
    assert np.array_equal(intensity, intensity_before, equal_nan=True)
    assert report.original_point_count == 15
    assert report.nonfinite_q_count == 1
    assert report.nonfinite_intensity_count == 1
    assert report.nonpositive_intensity_count == 1
    assert report.duplicate_q_count == 1
    assert report.nonmonotonic_q is True
    assert "q_nonfinite" in report.reason_codes
    assert report.level is QualityLevel.TREND


def test_quality_report_marks_too_few_usable_points_unusable():
    report = build_data_quality_report([0.01, 0.02, 0.03], [1.0, -1.0, np.nan])

    assert report.usable_point_count == 1
    assert report.level is QualityLevel.UNUSABLE
    assert "insufficient_points" in report.reason_codes


def test_contracts_round_trip_to_strict_json_without_numpy_or_enum_values():
    quality = build_data_quality_report(
        np.linspace(0.01, 0.12, 12), np.linspace(10.0, 5.0, 12),
        source_id="frame-001", raw_data_ref="raw/frame-001.xy",
        processing_config_ref="sha256:config",
    )
    metric = MetricEvidence(
        metric_name="Rg", value=4.5, unit="nm", level=QualityLevel.QUANTITATIVE,
        uncertainty=0.2, data_quality_ref="frame-001", source_ref="guinier-fit",
    )
    guinier = GuinierEvidence(
        rg_nm=4.5, rg_uncertainty_nm=0.2, q_rg_max=1.1, point_count=18,
        r_squared=0.998, level=QualityLevel.QUANTITATIVE,
        metric=metric,
    )
    candidate = RescueCandidate(
        candidate_id="candidate-1", kind="ai", parameters={"q_max": 0.12},
        reason_codes=("fit_window_candidate",),
    )
    validation = RescueValidationReport(
        candidate_id="candidate-1", hard_gate_passed=True,
        physical_gate_passed=True, data_preserved=True,
        decision="accepted",
    )
    payload = {
        "quality": quality.to_dict(),
        "guinier": guinier.to_dict(),
        "candidate": candidate.to_dict(),
        "validation": validation.to_dict(),
    }

    encoded = json.dumps(payload, allow_nan=False, sort_keys=True)

    assert json.loads(encoded)["quality"]["level"] == "Quantitative"
    assert DataQualityReport.from_dict(payload["quality"]) == quality
    assert GuinierEvidence.from_dict(payload["guinier"]).rg_nm == 4.5
    assert RescueCandidate.from_dict(payload["candidate"]).kind == "ai"
    assert RescueValidationReport.from_dict(payload["validation"]).decision == "accepted"


def test_ai_candidate_cannot_be_marked_accepted_without_validation_gates():
    candidate = RescueCandidate(candidate_id="candidate-2", kind="ai")
    report = RescueValidationReport(
        candidate_id=candidate.candidate_id,
        hard_gate_passed=False,
        physical_gate_passed=False,
        data_preserved=True,
        decision="accepted",
    )

    assert report.effective_decision() == "rejected"
    assert "hard_gate_failed" in report.rejection_reasons
    assert "physical_gate_failed" in report.rejection_reasons


def test_clean_synthetic_guinier_case_is_quantitative():
    q, intensity = clean_guinier_case()

    report = build_data_quality_report(q, intensity, source_id="clean")

    assert report.level is QualityLevel.QUANTITATIVE
    assert report.reason_codes == ()


def test_dirty_synthetic_case_retains_explicit_fault_reasons():
    q, intensity = dirty_guinier_case()

    report = build_data_quality_report(q, intensity, source_id="dirty")

    assert report.level is QualityLevel.TREND
    assert {"q_nonfinite", "intensity_nonfinite", "intensity_nonpositive", "q_duplicate"} <= set(report.reason_codes)


def test_low_q_truncated_case_stays_diagnostic_without_rescue_validation():
    q, intensity = low_q_truncated_case()

    report = build_data_quality_report(
        q, intensity, source_id="truncated", low_q_truncated=True
    )

    assert report.level is QualityLevel.DIAGNOSTIC
    assert "low_q_truncated" in report.reason_codes
