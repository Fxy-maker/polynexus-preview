from __future__ import annotations

import pytest

from polynexus.core.preprocess_optimization import AnalysisSnapshot, PreprocessIntent
from polynexus.core.preprocess_optimization.adapters.registry import get_preprocess_adapter


def _intent(target: str, effect: str = "medium") -> PreprocessIntent:
    return PreprocessIntent(
        schema_version="1.0",
        analysis_id="saxs-1",
        technique="SAXS",
        target=target,
        direction="strengthen",
        desired_effect=effect,
        protected_features=(
            "weak_peaks",
            "integrated_area",
            "guinier_region",
            "beamstop_boundaries",
        ),
        target_symptoms=("noise_dominant",),
        rationale_code="noise",
        human_summary="Reduce noise without crossing masked q boundaries.",
    )


def _snapshot(output, *, rmse, baseline):
    return AnalysisSnapshot.from_parts(
        config={},
        output_parameters=output,
        residual_pattern={"rmse": rmse, "residual_autocorrelation": 0.05},
        analysis_evidence={
            "background_evidence": {"baseline_stability_score": baseline}
        },
    )


def test_saxs_background_action_requires_real_manual_background() -> None:
    adapter = get_preprocess_adapter("SAXS")

    assert adapter.baseline_deltas(
        _intent("baseline"),
        {"background_file": "", "bg_scale_method": "manual"},
    ) == []
    deltas = adapter.baseline_deltas(
        _intent("baseline"),
        {
            "background_file": "bg.csv",
            "bg_scale_method": "manual",
            "bg_scale_value": 1.0,
            "transmission_sample": 0.7,
            "sample_thickness_m": 0.001,
        },
    )

    assert deltas == [{"bg_scale_value": 0.95}, {"bg_scale_value": 1.05}]
    assert all("transmission_sample" not in item for item in deltas)
    assert all("sample_thickness_m" not in item for item in deltas)


def test_saxs_smoothing_candidates_are_bounded_and_do_not_change_metadata() -> None:
    deltas = get_preprocess_adapter("SAXS").smoothing_deltas(
        _intent("smoothing"),
        {
            "smooth_method": "savgol",
            "savgol_window": 7,
            "savgol_order": 2,
            "transmission_sample": 0.7,
        },
    )

    assert deltas == [{"savgol_window": 3}, {"savgol_window": 11}]
    assert all("transmission_sample" not in item for item in deltas)


def test_saxs_evidence_protects_q_lengths_guinier_and_invariant() -> None:
    control = _snapshot(
        {
            "q_peak": 0.50,
            "q_peak_fwhm": 0.04,
            "q_peak_area": 10.0,
            "L_bragg": 12.57,
            "L_corr_peak": 12.2,
            "Rg": 4.0,
            "Q_invariant": 20.0,
            "negative_fraction": 0.0,
        },
        rmse=1.0,
        baseline=0.7,
    )
    candidate = _snapshot(
        {
            "q_peak": 0.505,
            "q_peak_fwhm": 0.041,
            "q_peak_area": 9.9,
            "L_bragg": 12.45,
            "L_corr_peak": 12.1,
            "Rg": 4.02,
            "Q_invariant": 19.8,
            "negative_fraction": 0.0,
        },
        rmse=0.7,
        baseline=0.85,
    )

    evidence = get_preprocess_adapter("SAXS").build_evidence(
        "saxs-c1", control, candidate
    )

    assert evidence.peak_shift == pytest.approx(0.005)
    assert evidence.integrated_area_change == pytest.approx(0.01)
    assert evidence.physical_parameter_drift < 0.02
    assert evidence.technique_specific["cross_boundary_smoothing"] is False
    assert evidence.technique_specific["Rg_change"] == pytest.approx(0.005)


def test_saxs_action_registry_exposes_background_and_smoothing_without_metadata() -> None:
    from polynexus.core.saxs_action_registry import (
        actions_for_symptoms,
        allowed_changes_for_actions,
    )

    actions = actions_for_symptoms(
        [
            {"name": "background_drift"},
            {"name": "noise_dominant"},
        ],
        technique="SAXS",
    )
    names = {item["name"] for item in actions}
    allowed = allowed_changes_for_actions(actions, technique="SAXS")

    assert {"rebalance_background_scale", "reduce_profile_noise"} <= names
    assert "bg_scale_value" in allowed
    assert "smooth_method" in allowed
    assert "transmission_sample" not in allowed
    assert "sample_thickness_m" not in allowed
