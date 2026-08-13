from __future__ import annotations

import pytest

from polynexus.core.project_workflow.analysis_plan_evaluation import (
    AnalysisSymptom,
    CandidateEvaluation,
    evaluate_candidates,
    diagnose_symptoms,
)


def test_diagnose_symptoms_returns_machine_readable_priorities():
    symptoms = diagnose_symptoms({"baseline_drift": 0.8, "peak_shift": 0.1, "trend_gap": 0.7})

    assert [item.code for item in symptoms] == ["baseline_drift", "trend_discontinuity"]
    assert all(isinstance(item, AnalysisSymptom) for item in symptoms)


def test_evaluate_candidates_is_finite_and_protects_scientific_metrics():
    result = evaluate_candidates(
        default_config={"baseline": "rubberband", "smooth_window": 5},
        candidates=(
            {"id": "linear", "config": {"baseline": "linear", "smooth_window": 5}},
            {"id": "too_smooth", "config": {"baseline": "linear", "smooth_window": 99}},
        ),
        observations={"baseline_residual": 0.1, "peak_shift": 0.2, "peak_retention": 0.98, "runtime_s": 1.0},
        thresholds={"max_peak_shift": 1.0, "min_peak_retention": 0.9},
        protected_metrics=("peak_position", "peak_area"),
    )

    assert len(result) == 2
    assert all(isinstance(item, CandidateEvaluation) for item in result)
    assert result[0].status == "stable"
    assert result[1].status == "unusable"
    assert result[0].protected_metrics == ("peak_position", "peak_area")


def test_evaluate_candidates_rejects_unbounded_ai_values():
    with pytest.raises(ValueError, match="candidate config"):
        evaluate_candidates(
            default_config={"smooth_window": 5},
            candidates=({"id": "bad", "config": {"smooth_window": 5000}},),
            observations={},
            thresholds={},
            protected_metrics=(),
        )
