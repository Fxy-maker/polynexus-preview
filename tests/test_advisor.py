from __future__ import annotations

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
