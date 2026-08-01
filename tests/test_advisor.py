from __future__ import annotations

import pytest

from llm.llm_client import LLMCancelledError
from rag.advisor import Advisor


def _intent(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "analysis_id": "ir-baseline-1",
        "technique": "IR",
        "target": "baseline",
        "direction": "strengthen",
        "desired_effect": "medium",
        "protected_features": ["weak_peaks", "integrated_area"],
        "target_symptoms": ["baseline_drift"],
        "rationale_code": "baseline_drift",
        "human_summary": "Stabilize the baseline while preserving weak bands.",
    }
    payload.update(overrides)
    return payload


def test_advisor_rejects_malformed_preprocess_intent_without_repair() -> None:
    advisor = Advisor.__new__(Advisor)

    advice = advisor._normalize_advice(
        {
            "preprocess_intent": _intent(desired_effect="maximum"),
            "changes": {"smooth_window": 99, "peak_distance": 8},
        }
    )

    assert advice["preprocess_intent"] is None
    assert advice["changes"] == {"peak_distance": 8}
    assert advice["preprocess_intent_error"]


def test_advisor_accepts_strict_intent_but_strips_numeric_preprocess_changes() -> None:
    advisor = Advisor.__new__(Advisor)

    advice = advisor._normalize_advice(
        {
            "preprocess_intent": _intent(),
            "changes": {
                "baseline_lam": 1e12,
                "smooth_window": 99,
                "peak_distance": 8,
            },
        }
    )

    assert advice["preprocess_intent"] == _intent()
    assert advice["preprocess_intent_error"] == ""
    assert advice["changes"] == {"peak_distance": 8}


def test_preprocess_action_without_intent_still_strips_numeric_preprocess_changes() -> None:
    advisor = Advisor.__new__(Advisor)

    advice = advisor._normalize_advice(
        {
            "recommended_actions": [{"name": "reduce_noise"}],
            "changes": {"smooth_window": 21, "assignment_tolerance_cm1": 3.0},
        }
    )

    assert advice["preprocess_intent"] is None
    assert advice["preprocess_intent_error"] == ""
    assert advice["changes"] == {"assignment_tolerance_cm1": 3.0}


def test_advisor_omits_preprocess_fields_for_ordinary_advice() -> None:
    advisor = Advisor.__new__(Advisor)

    advice = advisor._normalize_advice(
        {
            "assessment": "PASS",
            "diagnosis": "stable",
            "changes": {"peak_distance": 8},
        }
    )

    assert "preprocess_intent" not in advice
    assert "preprocess_intent_error" not in advice


class _ContextRetriever:
    def retrieve(self, *args: object, **kwargs: object) -> list[dict[str, object]]:
        return []


class _ContextLLM:
    last_used_mock = True

    def chat(self, prompt: str, **kwargs: object) -> str:
        del prompt, kwargs
        return '{"assessment":"WARN","confidence":0.0,"changes":{},"converge":true}'


class _CandidateReferenceLLM:
    last_used_mock = True

    def chat(self, prompt: str, **kwargs: object) -> str:
        del prompt, kwargs
        return (
            '{"assessment":"WARN","confidence":0.4,"changes":{},'
            '"saxs_candidate_references":["temperature-frame-0-lc-tangent",'
            '"unknown-candidate","temperature-frame-0-lc-tangent",7]}'
        )


class _MalformedResponseLLM:
    last_used_mock = False
    provider_label = "Test LLM"

    def chat(self, prompt: str, **kwargs: object) -> str:
        del prompt, kwargs
        return '{"assessment":"PASS","confidence":"not-a-number","changes":{}}'


class _CancelledLLM:
    last_used_mock = False

    def chat(self, prompt: str, **kwargs: object) -> str:
        del prompt, kwargs
        raise LLMCancelledError("cancelled by user")


class _NonFiniteConfidenceLLM:
    last_used_mock = False
    provider_label = "Test LLM"

    def chat(self, prompt: str, **kwargs: object) -> str:
        del prompt, kwargs
        return '{"assessment":"PASS","confidence":"NaN","changes":{}}'


def test_advisor_transports_saxs_summary_context_to_the_real_prompt() -> None:
    advisor = Advisor(retriever=_ContextRetriever(), llm_client=_ContextLLM())

    advisor.advise(
        {
            "technique": "SAXS",
            "params": {"Rg_nm": 4.2},
            "saxs_ai_context": {
                "technique": "SAXS",
                "mode": "temperature",
                "status": "available",
                "candidate_only": True,
                "raw_profile_included": False,
                "raw_detector_data_included": False,
                "frames": [],
            },
        }
    )

    assert "## SAXS AI summary context" in advisor.last_prompt
    assert '"candidate_only": true' in advisor.last_prompt


def test_advisor_prompt_retains_all_saxs_1d_method_evidence() -> None:
    advisor = Advisor(retriever=_ContextRetriever(), llm_client=_ContextLLM())
    metric_evidence = {
        name: {
            "metric_name": name.title(),
            "level": "Trend",
            "value": float(index + 1),
            "physical_checks": {"method_gate_passed": True},
        }
        for index, name in enumerate(("guinier", "porod", "kratky", "invariant", "lamellar"))
    }

    advisor.advise(
        {
            "technique": "SAXS",
            "params": {"Rg_nm": 4.2},
            "saxs_ai_context": {
                "technique": "SAXS",
                "mode": "temperature",
                "status": "available",
                "candidate_only": True,
                "physical_validation_required": True,
                "raw_profile_included": False,
                "raw_detector_data_included": False,
                "frames": [],
                "series": {"metric_evidence": metric_evidence},
            },
        }
    )

    assert advisor.last_prompt is not None
    for name in metric_evidence:
        assert f'"{name}"' in advisor.last_prompt
    assert '"candidate_only": true' in advisor.last_prompt
    assert '"physical_validation_required": true' in advisor.last_prompt


def test_advisor_prompt_retains_existing_sequence_rescue_candidate_boundary() -> None:
    advisor = Advisor(retriever=_ContextRetriever(), llm_client=_ContextLLM())

    advisor.advise(
        {
            "technique": "SAXS",
            "params": {},
            "saxs_ai_context": {
                "technique": "SAXS",
                "mode": "temperature",
                "status": "available",
                "candidate_only": True,
                "physical_validation_required": True,
                "series": {
                    "sequence_rescue_candidates": [
                        {
                            "candidate_id": "temperature-frame-0-lc-tangent",
                            "kind": "deterministic",
                            "parameters": {
                                "frame_index": 0,
                                "proposed_value_nm": 10.8,
                                "apply_mode": "candidate_only",
                                "preserve_missing_frames": True,
                                "raw_q": [0.01],
                            },
                            "requires_validation": True,
                        }
                    ]
                },
            },
        }
    )

    assert advisor.last_prompt is not None
    assert "temperature-frame-0-lc-tangent" in advisor.last_prompt
    assert '"apply_mode": "candidate_only"' in advisor.last_prompt
    assert '"requires_validation": true' in advisor.last_prompt
    assert "raw_q" not in advisor.last_prompt


def test_advisor_allowlists_existing_saxs_candidate_references() -> None:
    advisor = Advisor(retriever=_ContextRetriever(), llm_client=_CandidateReferenceLLM())

    advice = advisor.advise(
        {
            "technique": "SAXS",
            "params": {},
            "saxs_ai_context": {
                "technique": "SAXS",
                "mode": "temperature",
                "status": "available",
                "candidate_only": True,
                "physical_validation_required": True,
                "series": {
                    "sequence_rescue_candidates": [
                        {"candidate_id": "temperature-frame-0-lc-tangent"}
                    ]
                },
            },
        }
    )

    assert advice["saxs_candidate_references"] == ["temperature-frame-0-lc-tangent"]
    assert advice["changes"] == {}
    assert "preprocess_intent" not in advice
    assert "candidate_plan" not in advice


def test_advisor_drops_candidate_references_without_temperature_candidates() -> None:
    advisor = Advisor(retriever=_ContextRetriever(), llm_client=_CandidateReferenceLLM())

    advice = advisor.advise(
        {
            "technique": "SAXS",
            "params": {},
            "saxs_ai_context": {
                "technique": "SAXS",
                "mode": "static",
                "status": "available",
                "candidate_only": True,
                "physical_validation_required": True,
                "series": {
                    "sequence_rescue_candidates": [
                        {"candidate_id": "temperature-frame-0-lc-tangent"}
                    ]
                },
            },
        }
    )

    assert advice["saxs_candidate_references"] == []


def test_advisor_drops_saxs_candidate_references_for_non_saxs_cases() -> None:
    advisor = Advisor(retriever=_ContextRetriever(), llm_client=_CandidateReferenceLLM())

    advice = advisor.advise({"technique": "IR", "params": {}})

    assert advice["saxs_candidate_references"] == []


def test_advisor_ignores_non_mapping_saxs_summary_context() -> None:
    advisor = Advisor.__new__(Advisor)

    normalized = advisor._normalize_case(
        {"technique": "SAXS", "saxs_ai_context": ["raw", "payload"]}
    )

    assert normalized["saxs_ai_context"] == {}


def test_advisor_falls_back_when_provider_response_normalization_fails() -> None:
    advisor = Advisor(retriever=_ContextRetriever(), llm_client=_MalformedResponseLLM())

    advice = advisor.advise({"technique": "SAXS", "params": {}})

    assert advice["diagnosis"] == "provider_unavailable"
    assert advice["llm_used"] is False
    assert advice["changes"] == {}
    assert advice["converge"] is True


def test_advisor_preserves_provider_cancellation() -> None:
    advisor = Advisor(retriever=_ContextRetriever(), llm_client=_CancelledLLM())

    with pytest.raises(LLMCancelledError, match="cancelled by user"):
        advisor.advise({"technique": "SAXS", "params": {}})


def test_advisor_falls_back_on_nonfinite_provider_confidence() -> None:
    advisor = Advisor(retriever=_ContextRetriever(), llm_client=_NonFiniteConfidenceLLM())

    advice = advisor.advise({"technique": "SAXS", "params": {}})

    assert advice["diagnosis"] == "provider_unavailable"
    assert advice["llm_used"] is False
    assert advice["changes"] == {}
