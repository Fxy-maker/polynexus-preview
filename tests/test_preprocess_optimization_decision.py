from __future__ import annotations

from dataclasses import replace

import pytest

from polynexus.core.preprocess_optimization import PreprocessEvidence, get_preprocess_policy
from polynexus.core.preprocess_optimization.decision import decide_preprocess_candidate


def _safe_evidence(**overrides) -> PreprocessEvidence:
    values = {
        "schema_version": "1.0",
        "candidate_id": "candidate-1",
        "run_status": "ok",
        "evidence_coverage": 1.0,
        "noise_reduction": 0.30,
        "baseline_flatness": 0.20,
        "residual_autocorrelation": 0.05,
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


def _policy(state: str):
    return replace(
        get_preprocess_policy("DSC"),
        calibrated=state == "tiered_auto",
        automation_state=state,
    )


def test_hard_guard_cannot_be_outvoted_by_large_improvement() -> None:
    outcome = decide_preprocess_candidate(
        _safe_evidence(integrated_area_change=0.40, noise_reduction=1.0),
        _policy("tiered_auto"),
        candidate_margin=1.0,
        metadata_complete=True,
    )

    assert outcome.decision == "keep_original"
    assert outcome.confidence_band == "low"
    assert "integrated_area_change" in outcome.reason_codes
    assert outcome.hard_guard_results["integrated_area_change"] is False


def test_missing_metadata_caps_high_candidate_at_confirmation() -> None:
    outcome = decide_preprocess_candidate(
        _safe_evidence(),
        _policy("tiered_auto"),
        candidate_margin=1.0,
        metadata_complete=False,
    )

    assert outcome.confidence_band == "medium"
    assert outcome.decision == "request_confirmation"
    assert "metadata_incomplete" in outcome.reason_codes


def test_shadow_never_mutates_even_for_simulated_high_confidence() -> None:
    outcome = decide_preprocess_candidate(
        _safe_evidence(),
        _policy("shadow"),
        candidate_margin=1.0,
        metadata_complete=True,
    )

    assert outcome.confidence_band == "high"
    assert outcome.simulated_decision == "auto_accept"
    assert outcome.decision == "keep_original"
    assert "shadow_mode" in outcome.reason_codes


def test_confirm_only_requires_confirmation_for_high_confidence() -> None:
    outcome = decide_preprocess_candidate(
        _safe_evidence(),
        _policy("confirm_only"),
        candidate_margin=1.0,
        metadata_complete=True,
    )

    assert outcome.confidence_band == "high"
    assert outcome.decision == "request_confirmation"


def test_calibrated_tiered_policy_auto_accepts_high_confidence() -> None:
    outcome = decide_preprocess_candidate(
        _safe_evidence(),
        _policy("tiered_auto"),
        candidate_margin=1.0,
        metadata_complete=True,
    )

    assert outcome.confidence_band == "high"
    assert outcome.decision == "auto_accept"
    assert outcome.confidence_score >= _policy("tiered_auto").high_threshold


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("run_status", "failed", "run_status"),
        ("evidence_coverage", 0.2, "evidence_coverage"),
        ("negative_fraction", 0.20, "negative_fraction"),
        ("weak_peak_retention", 0.5, "weak_peak_retention"),
        ("physical_parameter_drift", 0.5, "physical_parameter_drift"),
    ],
)
def test_each_hard_guard_keeps_original(field: str, value: object, reason: str) -> None:
    outcome = decide_preprocess_candidate(
        _safe_evidence(**{field: value}),
        _policy("tiered_auto"),
        candidate_margin=1.0,
        metadata_complete=True,
    )

    assert outcome.decision == "keep_original"
    assert reason in outcome.reason_codes


def test_missing_required_metric_fails_closed() -> None:
    outcome = decide_preprocess_candidate(
        _safe_evidence(peak_shift=None),
        _policy("tiered_auto"),
        candidate_margin=1.0,
        metadata_complete=True,
    )

    assert outcome.decision == "keep_original"
    assert "required_evidence_missing:peak_shift" in outcome.reason_codes


def test_no_preprocessing_gain_is_rejected() -> None:
    outcome = decide_preprocess_candidate(
        _safe_evidence(noise_reduction=0.0, baseline_flatness=0.0),
        _policy("tiered_auto"),
        candidate_margin=1.0,
        metadata_complete=True,
    )

    assert outcome.decision == "keep_original"
    assert "no_preprocess_gain" in outcome.reason_codes


def test_outcome_serializes_structured_decision() -> None:
    outcome = decide_preprocess_candidate(
        _safe_evidence(),
        _policy("shadow"),
        candidate_margin=1.0,
        metadata_complete=True,
    )

    payload = outcome.to_dict()
    assert payload["confidence_band"] == "high"
    assert payload["hard_guard_results"]["integrated_area_change"] is True
    assert isinstance(payload["reason_codes"], list)
