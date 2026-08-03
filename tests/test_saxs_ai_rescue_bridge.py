from __future__ import annotations

import json
from dataclasses import replace
from types import SimpleNamespace

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
    resolve_saxs_ai_candidate_references,
    validate_saxs_ai_intent,
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


def test_public_validator_returns_a_saxs_intent_without_generating_candidates():
    intent = validate_saxs_ai_intent(_intent())

    assert intent.technique == "SAXS"
    assert intent.protected_features == tuple(PROTECTED)


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


def _sequence_candidate(candidate_id: str = "temperature-frame-0-lc-tangent") -> dict:
    return {
        "candidate_id": candidate_id,
        "kind": "deterministic",
        "parameters": {
            "frame_index": 0,
            "axis_name": "temperature",
            "axis_value": 170.0,
            "metric": "lc_nm",
            "original_value_nm": None,
            "proposed_value_nm": 10.8,
            "proposed_source": "tangent",
            "path_status": "diagnostic_only",
            "preserve_missing_frames": True,
            "apply_mode": "candidate_only",
        },
        "reason_codes": ["sequence_existing_alternative"],
        "source": "saxs_temperature.select_lc_sequence_path",
        "requires_validation": True,
    }


def test_ai_reference_bridge_resolves_current_temperature_candidate_detached() -> None:
    candidate = _sequence_candidate()
    result = SimpleNamespace(
        _temperature_result=SimpleNamespace(sequence_rescue_candidates=[candidate])
    )
    advice = {"saxs_candidate_references": [candidate["candidate_id"]]}

    resolution = resolve_saxs_ai_candidate_references(result, advice, mode="temperature")

    assert resolution["status"] == "available"
    assert resolution["unresolved_ids"] == []
    assert resolution["resolved"][0]["candidate_id"] == candidate["candidate_id"]
    assert resolution["resolved"][0] is not candidate
    candidate["parameters"]["proposed_value_nm"] = 99.0
    assert resolution["resolved"][0]["parameters"]["proposed_value_nm"] == 10.8


@pytest.mark.parametrize(
    ("mode", "advice", "candidate_records", "expected_reason"),
    [
        ("static", {"saxs_candidate_references": ["temperature-frame-0-lc-tangent"]}, [_sequence_candidate()], "unsupported_mode"),
        ("temperature", {"saxs_candidate_references": ["unknown"]}, [_sequence_candidate()], "candidate_not_found"),
        ("temperature", {"saxs_candidate_references": [7]}, [_sequence_candidate()], "candidate_reference_malformed"),
        ("temperature", {"saxs_candidate_references": ["temperature-frame-0-lc-tangent"]}, [_sequence_candidate(), _sequence_candidate()], "duplicate_candidate_id"),
    ],
)
def test_ai_reference_bridge_fails_closed_without_fabricating_candidates(
    mode: str,
    advice: dict,
    candidate_records: list[dict],
    expected_reason: str,
) -> None:
    result = SimpleNamespace(
        _temperature_result=SimpleNamespace(sequence_rescue_candidates=candidate_records)
    )

    resolution = resolve_saxs_ai_candidate_references(result, advice, mode=mode)

    assert resolution["resolved"] == []
    assert expected_reason in resolution["reason_codes"]
    assert resolution["status"] == "unavailable"
