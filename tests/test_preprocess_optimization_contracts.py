from __future__ import annotations

from dataclasses import asdict

import pytest

from polynexus.core.preprocess_optimization import (
    ContractValidationError,
    DecisionRecord,
    PreprocessCandidate,
    PreprocessEvidence,
    PreprocessIntent,
    SCHEMA_VERSION,
    parse_preprocess_intent,
)


VALID_INTENT = {
    "schema_version": "1.0",
    "analysis_id": "case-1",
    "technique": "DSC",
    "target": "both",
    "direction": "strengthen",
    "desired_effect": "medium",
    "protected_features": ["integrated_area", "weak_peaks"],
    "target_symptoms": ["noise_dominant"],
    "rationale_code": "noise_without_event_loss",
    "human_summary": "Reduce noise while preserving thermal events.",
}


def test_parse_preprocess_intent_is_strict_and_round_trips() -> None:
    intent = parse_preprocess_intent(VALID_INTENT)

    assert isinstance(intent, PreprocessIntent)
    assert intent.technique == "DSC"
    assert intent.to_dict() == VALID_INTENT


def test_parse_preprocess_intent_rejects_unknown_fields() -> None:
    with pytest.raises(ContractValidationError, match="Additional properties"):
        parse_preprocess_intent({**VALID_INTENT, "smooth_window": 99})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("target", "normalization"),
        ("direction", "invent"),
        ("desired_effect", "maximum"),
        ("technique", "JOINT"),
    ],
)
def test_parse_preprocess_intent_rejects_unknown_enums(field: str, value: str) -> None:
    with pytest.raises(ContractValidationError):
        parse_preprocess_intent({**VALID_INTENT, field: value})


@pytest.mark.parametrize("payload", [None, [], "DSC"])
def test_parse_preprocess_intent_rejects_non_objects(payload: object) -> None:
    with pytest.raises(ContractValidationError, match="must be an object"):
        parse_preprocess_intent(payload)


def test_contracts_are_versioned_and_serialize_without_mutating_input() -> None:
    delta = {"smooth_window": 9}
    candidate = PreprocessCandidate(
        schema_version=SCHEMA_VERSION,
        candidate_id="candidate-1",
        parent_intent_id="intent-1",
        technique="DSC",
        generator_name="dsc-preprocess",
        generator_version="1",
        base_config_hash="hash-1",
        config_delta=delta,
        expected_effect="medium",
        protected_features=("integrated_area",),
        generation_reason="smoothing",
    )
    evidence = PreprocessEvidence(
        schema_version=SCHEMA_VERSION,
        candidate_id="candidate-1",
        run_status="ok",
        evidence_coverage=1.0,
        noise_reduction=0.2,
        warnings=("example",),
    )
    decision = DecisionRecord(
        schema_version=SCHEMA_VERSION,
        analysis_id="case-1",
        original_config_hash="hash-1",
        selected_candidate_id="candidate-1",
        decision="request_confirmation",
        confidence_band="medium",
        score_components={"preservation": 0.95},
        hard_guard_results={"coverage": True},
        evidence_refs=("candidate-1",),
        policy_version="dsc-v1",
        core_version="1",
    )

    assert candidate.to_dict()["protected_features"] == ["integrated_area"]
    assert evidence.to_dict()["warnings"] == ["example"]
    assert decision.to_dict()["evidence_refs"] == ["candidate-1"]
    assert asdict(candidate)["config_delta"] == {"smooth_window": 9}
    assert delta == {"smooth_window": 9}
