from __future__ import annotations

import json
from dataclasses import replace

import pytest

from polynexus.core.preprocess_optimization import (
    PreprocessEvidence,
    get_preprocess_policy,
)
from polynexus.core.preprocess_optimization.policy import PolicyValidationError
from polynexus.core.preprocess_optimization.intent_schema import ContractValidationError
from polynexus.core.saxs_engine.saxs_ai_rescue import (
    build_saxs_ai_rescue_plan,
    assess_saxs_ai_candidate,
)


PROTECTED = [
    "weak_peaks",
    "integrated_area",
    "guinier_region",
    "beamstop_boundaries",
    "peak_position",
    "peak_width",
    "physical_parameters",
]


def _intent(**overrides):
    payload = {
        "schema_version": "1.0",
        "analysis_id": "saxs-ai-1",
        "technique": "SAXS",
        "target": "smoothing",
        "direction": "strengthen",
        "desired_effect": "light",
        "protected_features": list(PROTECTED),
        "target_symptoms": ["noise_dominant"],
        "rationale_code": "quality_report_noise",
        "human_summary": "Reduce profile noise while preserving SAXS features.",
    }
    payload.update(overrides)
    return payload


def _evidence(**overrides):
    values = {
        "schema_version": "1.0",
        "candidate_id": "candidate-1",
        "run_status": "ok",
        "evidence_coverage": 1.0,
        "noise_reduction": 0.30,
        "baseline_flatness": 0.20,
        "negative_fraction": 0.0,
        "peak_shift": 0.002,
        "fwhm_change": 0.02,
        "integrated_area_change": 0.01,
        "weak_peak_retention": 1.0,
        "physical_parameter_drift": 0.01,
        "technique_specific": {"sensitivity_stability": 0.95},
    }
    values.update(overrides)
    return PreprocessEvidence(**values)


def test_ai_intent_must_be_saxs_and_protect_physical_features():
    with pytest.raises(ContractValidationError):
        build_saxs_ai_rescue_plan(_intent(technique="IR"), {})
    with pytest.raises(ContractValidationError):
        build_saxs_ai_rescue_plan(_intent(protected_features=PROTECTED[:-1]), {})


def test_valid_intent_generates_bounded_candidate_only_plan():
    plan = build_saxs_ai_rescue_plan(
        _intent(),
        {"smooth_method": "savgol", "savgol_window": 7, "savgol_order": 2},
    )

    assert plan.automation_state == "shadow"
    assert plan.original_preserved is True
    assert plan.physical_validation_required is True
    assert plan.candidates
    assert all(candidate.technique == "SAXS" for candidate in plan.candidates)
    assert json.loads(plan.to_json())["candidate_only"] is True


def test_shadow_and_confirm_keep_original_until_user_or_policy_allows_it():
    shadow = assess_saxs_ai_candidate(_evidence(), candidate_margin=1.0, metadata_complete=True)
    confirm = assess_saxs_ai_candidate(
        _evidence(),
        candidate_margin=1.0,
        metadata_complete=True,
        policy=get_preprocess_policy("SAXS").with_automation_state("confirm_only"),
    )

    assert shadow.decision == "keep_original"
    assert shadow.simulated_decision == "auto_accept"
    assert shadow.apply_allowed is False
    assert "shadow_mode" in shadow.reason_codes
    assert confirm.decision == "request_confirmation"
    assert confirm.apply_allowed is False


def test_tiered_auto_requires_calibration_and_all_hard_guards():
    with pytest.raises(PolicyValidationError):
        assess_saxs_ai_candidate(
            _evidence(),
            candidate_margin=1.0,
            metadata_complete=True,
            automation_state="tiered_auto",
        )

    calibrated = replace(
        get_preprocess_policy("SAXS"),
        automation_state="tiered_auto",
        calibrated=True,
    )
    accepted = assess_saxs_ai_candidate(
        _evidence(),
        candidate_margin=1.0,
        metadata_complete=True,
        policy=calibrated,
    )
    fallback = assess_saxs_ai_candidate(
        _evidence(fallback_active=True, fallback_reason="fallback"),
        candidate_margin=1.0,
        metadata_complete=True,
        policy=calibrated,
    )

    assert accepted.decision == "auto_accept"
    assert accepted.apply_allowed is True
    assert fallback.decision == "keep_original"
    assert fallback.apply_allowed is False
