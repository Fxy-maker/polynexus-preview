from __future__ import annotations

import pytest

from polynexus.core.preprocess_optimization import AnalysisSnapshot, PreprocessIntent
from polynexus.core.preprocess_optimization.adapters.registry import get_preprocess_adapter


def _intent(technique: str, target: str) -> PreprocessIntent:
    protected = {
        "DSC": ("weak_peaks", "integrated_area", "thermal_events"),
        "IR": ("weak_peaks", "integrated_area"),
        "WAXS": ("weak_peaks", "integrated_area", "broad_halo"),
    }[technique]
    return PreprocessIntent(
        schema_version="1.0",
        analysis_id=f"{technique.lower()}-1",
        technique=technique,
        target=target,
        direction="strengthen",
        desired_effect="medium",
        protected_features=protected,
        target_symptoms=("noise_dominant",),
        rationale_code="noise",
        human_summary="Improve preprocessing while preserving scientific features.",
    )


def _snapshot(output, *, rmse: float, evidence=None) -> AnalysisSnapshot:
    return AnalysisSnapshot.from_parts(
        config={},
        output_parameters=output,
        residual_pattern={"rmse": rmse, "residual_autocorrelation": 0.05},
        analysis_evidence=evidence or {},
    )


def test_dsc_medium_smoothing_uses_bounded_odd_windows() -> None:
    adapter = get_preprocess_adapter("DSC")

    deltas = adapter.smoothing_deltas(
        _intent("DSC", "smoothing"),
        {"smooth_method": "savgol", "smooth_window": 11, "smooth_order": 3},
    )

    assert deltas == [{"smooth_window": 7}, {"smooth_window": 15}]
    assert all(item["smooth_window"] % 2 == 1 for item in deltas)


def test_ir_baseline_candidates_include_real_als_strength_not_normalization() -> None:
    adapter = get_preprocess_adapter("IR")

    deltas = adapter.baseline_deltas(
        _intent("IR", "baseline"),
        {"baseline_method": "als", "baseline_lam": 1e6, "baseline_p": 0.001},
    )

    assert {tuple(sorted(item)) for item in deltas} >= {
        ("baseline_lam",),
        ("baseline_p",),
    }
    assert all("normalization_method" not in item for item in deltas)


def test_waxs_background_recipe_never_changes_amorphous_partition() -> None:
    adapter = get_preprocess_adapter("WAXS")

    deltas = adapter.baseline_deltas(
        _intent("WAXS", "baseline"),
        {
            "instrument_background_method": "arpls",
            "arpls_lam": 1e5,
            "arpls_diff_order": 2,
        },
    )

    assert deltas
    assert any("arpls_lam" in item for item in deltas)
    assert all("amorphous_subtraction" not in item for item in deltas)
    assert all("background_method" not in item for item in deltas)


def test_dsc_evidence_protects_enthalpy_events_and_peak_shape() -> None:
    control = _snapshot(
        {
            "peak_components": [
                {"temperature": 180.0, "fwhm_C": 8.0, "area": 100.0, "height": 10.0},
                {"temperature": 215.0, "fwhm_C": 5.0, "area": 12.0, "height": 1.0},
            ],
            "DHm_Jg": 100.0,
            "Tg_C": 55.0,
            "Tm_peak_C": 215.0,
            "Xc_pct": 43.0,
            "negative_fraction": 0.0,
        },
        rmse=1.0,
        evidence={"baseline_evidence": {"baseline_stability_score": 0.70}},
    )
    candidate = _snapshot(
        {
            "peak_components": [
                {"temperature": 180.2, "fwhm_C": 8.2, "area": 98.0, "height": 10.2},
                {"temperature": 215.1, "fwhm_C": 5.1, "area": 11.8, "height": 0.95},
            ],
            "DHm_Jg": 98.0,
            "Tg_C": 55.1,
            "Tm_peak_C": 215.1,
            "Xc_pct": 42.5,
            "negative_fraction": 0.0,
        },
        rmse=0.7,
        evidence={"baseline_evidence": {"baseline_stability_score": 0.90}},
    )

    result = get_preprocess_adapter("DSC").build_evidence("dsc-1", control, candidate)

    assert result.noise_reduction == pytest.approx(0.30)
    assert result.baseline_flatness == pytest.approx(0.20)
    assert result.peak_shift == pytest.approx(0.20)
    assert result.integrated_area_change == pytest.approx(0.02)
    assert result.weak_peak_retention == 1.0
    assert result.evidence_coverage == 1.0
    assert result.technique_specific["DHm_Jg_change"] == pytest.approx(0.02)


def test_ir_evidence_detects_weak_band_loss() -> None:
    control = _snapshot(
        {
            "peaks": [
                {"wavenumber": 1715.0, "fwhm_cm1": 12.0, "area": 100.0, "height": 1.0},
                {"wavenumber": 1340.0, "fwhm_cm1": 8.0, "area": 4.0, "height": 0.05},
            ],
            "polymer_score": 0.9,
            "negative_fraction": 0.0,
        },
        rmse=0.10,
        evidence={"background_evidence": {"baseline_stability_score": 0.7}},
    )
    candidate = _snapshot(
        {
            "peaks": [
                {"wavenumber": 1715.2, "fwhm_cm1": 12.2, "area": 99.0, "height": 1.0},
            ],
            "polymer_score": 0.9,
            "negative_fraction": 0.0,
        },
        rmse=0.06,
        evidence={"background_evidence": {"baseline_stability_score": 0.9}},
    )

    result = get_preprocess_adapter("IR").build_evidence("ir-1", control, candidate)

    assert result.weak_peak_retention == 0.0
    assert result.integrated_area_change > 0.0


def test_waxs_evidence_tracks_peak_halo_and_crystallinity_drift() -> None:
    control = _snapshot(
        {
            "peaks": [
                {"center": 20.0, "fwhm": 0.8, "area": 100.0, "height": 10.0},
                {"center": 24.0, "fwhm": 1.0, "area": 20.0, "height": 2.0},
            ],
            "Xc_pct": 50.0,
            "D_Scherrer_nm": 8.0,
            "instrument_background_method": "arpls",
            "negative_fraction": 0.0,
        },
        rmse=0.5,
        evidence={"background_evidence": {"instrument_background_stability_score": 0.75}},
    )
    candidate = _snapshot(
        {
            "peaks": [
                {"center": 20.03, "fwhm": 0.82, "area": 99.0, "height": 10.0},
                {"center": 24.04, "fwhm": 1.02, "area": 19.8, "height": 2.0},
            ],
            "Xc_pct": 49.5,
            "D_Scherrer_nm": 7.9,
            "instrument_background_method": "polynomial",
            "negative_fraction": 0.0,
        },
        rmse=0.35,
        evidence={"background_evidence": {"instrument_background_stability_score": 0.90}},
    )

    result = get_preprocess_adapter("WAXS").build_evidence("waxs-1", control, candidate)

    assert result.peak_shift == pytest.approx(0.04)
    assert result.weak_peak_retention == 1.0
    assert result.physical_parameter_drift < 0.02
    assert result.technique_specific["Xc_pct_change"] == pytest.approx(0.01)


def test_missing_peak_and_physical_metrics_lower_evidence_coverage() -> None:
    empty = _snapshot({}, rmse=0.0)

    result = get_preprocess_adapter("DSC").build_evidence("missing", empty, empty)

    assert result.evidence_coverage < 0.5
    assert result.peak_shift is None
    assert result.physical_parameter_drift is None
