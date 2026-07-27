from __future__ import annotations

import json

from polynexus.core.preprocess_optimization import (
    DecisionOutcome,
    PreprocessCandidate,
    PreprocessEvidence,
    build_preprocess_replay_audit,
    stable_config_hash,
)


def _candidate() -> PreprocessCandidate:
    return PreprocessCandidate(
        schema_version="1.0",
        candidate_id="saxs-candidate-1",
        parent_intent_id="saxs-intent-1",
        technique="SAXS",
        generator_name="test-generator",
        generator_version="1",
        base_config_hash=stable_config_hash({"savgol_window": 7}),
        config_delta={"savgol_window": 9},
        expected_effect="reduce noise",
        protected_features=("weak_peaks", "physical_parameters"),
        generation_reason="test_noise_recovery",
    )


def _evidence(**overrides: object) -> PreprocessEvidence:
    values: dict[str, object] = {
        "schema_version": "1.0",
        "candidate_id": "saxs-candidate-1",
        "run_status": "ok",
        "evidence_coverage": 1.0,
        "noise_reduction": 0.2,
        "baseline_flatness": 0.2,
        "negative_fraction": 0.0,
        "peak_shift": 0.0,
        "fwhm_change": 0.0,
        "integrated_area_change": 0.0,
        "weak_peak_retention": 1.0,
        "physical_parameter_drift": 0.0,
    }
    values.update(overrides)
    return PreprocessEvidence(**values)


def _decision(**overrides: object) -> DecisionOutcome:
    values: dict[str, object] = {
        "decision": "keep_original",
        "simulated_decision": "auto_accept",
        "confidence_band": "high",
        "confidence_score": 0.9,
        "score_components": {"physical_preservation": 1.0},
        "hard_guard_results": {"run_status": True},
        "reason_codes": ("shadow_mode",),
    }
    values.update(overrides)
    return DecisionOutcome(**values)


def test_replay_audit_is_json_safe_and_hashes_configs() -> None:
    audit = build_preprocess_replay_audit(
        candidate=_candidate(),
        source_config={"savgol_window": 7},
        effective_config={"savgol_window": 9},
        mode="temperature",
        source_context={"condition_values": [20.0, float("nan")]},
        evidence=_evidence(),
        decision=_decision(),
        trial_engine_created=True,
        error="",
    )

    payload = audit.to_dict()
    json.dumps(payload, allow_nan=False)
    assert payload["original_config_hash"] == stable_config_hash({"savgol_window": 7})
    assert payload["effective_config_hash"] == stable_config_hash({"savgol_window": 9})
    assert payload["mode"] == "temperature"
    assert payload["original_preserved"] is True
    assert payload["apply_performed"] is False
    assert payload["source_context"]["condition_values"][1] is None


def test_failed_replay_has_no_effective_hash_and_cannot_apply() -> None:
    audit = build_preprocess_replay_audit(
        candidate=_candidate(),
        source_config={"savgol_window": 7},
        effective_config=None,
        mode="strain",
        source_context={},
        evidence=_evidence(run_status="failed"),
        decision=_decision(decision="keep_original"),
        trial_engine_created=False,
        error="candidate_timeout",
    )

    assert audit.effective_config_hash is None
    assert audit.apply_allowed is False
    assert audit.apply_performed is False
    assert audit.error == "candidate_timeout"
