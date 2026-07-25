from __future__ import annotations

import pytest

from polynexus.core.preprocess_optimization import (
    AnalysisSnapshot,
    PreprocessEvidence,
    get_preprocess_adapter,
    get_preprocess_policy,
)
from polynexus.core.preprocess_optimization.decision import decide_preprocess_candidate


TECHNIQUES = ("DSC", "IR", "WAXS", "SAXS", "NMR")


def _evidence(**overrides) -> PreprocessEvidence:
    values = {
        "schema_version": "1.0",
        "candidate_id": "candidate-matrix",
        "run_status": "ok",
        "evidence_coverage": 1.0,
        "noise_reduction": 0.30,
        "baseline_flatness": 0.20,
        "negative_fraction": 0.0,
        "peak_shift": 0.02,
        "fwhm_change": 0.02,
        "integrated_area_change": 0.01,
        "weak_peak_retention": 1.0,
        "physical_parameter_drift": 0.01,
        "technique_specific": {"sensitivity_stability": 0.95},
    }
    values.update(overrides)
    return PreprocessEvidence(**values)


@pytest.mark.parametrize("technique", TECHNIQUES)
def test_single_technique_ai_off_matrix_is_registered_and_shadowed(technique: str) -> None:
    policy = get_preprocess_policy(technique)

    assert get_preprocess_adapter(technique).technique == technique
    assert policy.automation_state == "shadow"
    assert policy.calibrated is False


@pytest.mark.parametrize("technique", TECHNIQUES)
def test_single_technique_failure_matrix_keeps_original(technique: str) -> None:
    outcome = decide_preprocess_candidate(
        _evidence(run_status="failed", warnings=("engine failed",)),
        get_preprocess_policy(technique),
        candidate_margin=1.0,
        metadata_complete=True,
    )

    assert outcome.decision == "keep_original"
    assert outcome.confidence_band == "low"
    assert "run_status" in outcome.reason_codes


@pytest.mark.parametrize("technique", TECHNIQUES)
def test_adapter_normalizes_fallback_for_every_single_technique(technique: str) -> None:
    adapter = get_preprocess_adapter(technique)
    control = AnalysisSnapshot.from_parts(
        config={},
        output_parameters={"peaks": []},
        residual_pattern={"rmse": 1.0},
        analysis_evidence={},
    )
    candidate = AnalysisSnapshot.from_parts(
        config={},
        output_parameters={
            "peaks": [],
            "calibrated_fallback_active": True,
            "calibrated_fallback_reason": "matrix fallback",
        },
        residual_pattern={"rmse": 0.5},
        analysis_evidence={},
    )

    evidence = adapter.build_evidence("candidate-matrix", control, candidate)
    outcome = decide_preprocess_candidate(
        evidence,
        get_preprocess_policy(technique),
        candidate_margin=1.0,
        metadata_complete=True,
    )

    assert evidence.fallback_active is True
    assert evidence.fallback_reason == "matrix fallback"
    assert evidence.to_dict()["fallback_reason"] == "matrix fallback"
    assert outcome.decision == "keep_original"
    assert outcome.confidence_band == "low"
    assert "fallback_active" in outcome.reason_codes


def test_joint_is_explicitly_outside_single_technique_preprocessing_matrix() -> None:
    assert "JOINT" not in TECHNIQUES
