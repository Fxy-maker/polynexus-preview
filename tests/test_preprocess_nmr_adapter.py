from __future__ import annotations

import pytest

from polynexus.core.preprocess_optimization import AnalysisSnapshot, PreprocessIntent
from polynexus.core.preprocess_optimization.adapters.registry import get_preprocess_adapter


def _intent(target: str, effect: str = "medium") -> PreprocessIntent:
    return PreprocessIntent(
        schema_version="1.0",
        analysis_id="nmr-1",
        technique="NMR",
        target=target,
        direction="strengthen",
        desired_effect=effect,
        protected_features=(
            "weak_peaks",
            "integrated_area",
            "chemical_shift",
            "peak_width",
        ),
        target_symptoms=("noise_dominant",),
        rationale_code="noise",
        human_summary="Reduce FID noise while preserving resonances.",
    )


def _snapshot(output, *, rmse, baseline):
    return AnalysisSnapshot.from_parts(
        config={},
        output_parameters=output,
        residual_pattern={"rmse": rmse, "residual_autocorrelation": 0.04},
        analysis_evidence={
            "baseline_evidence": {"baseline_stability_score": baseline}
        },
    )


def test_processed_spectrum_does_not_generate_fid_apodization_candidates() -> None:
    adapter = get_preprocess_adapter("NMR")

    deltas = adapter.smoothing_deltas(
        _intent("smoothing"),
        {
            "spectrum_mode": "processed",
            "apodization": "exponential",
            "lb_Hz": 10.0,
            "fid_zero_fill_factor": 2,
        },
    )

    assert deltas == []


def test_fid_candidates_never_change_zero_fill() -> None:
    deltas = get_preprocess_adapter("NMR").smoothing_deltas(
        _intent("smoothing"),
        {
            "spectrum_mode": "fid",
            "apodization": "exponential",
            "lb_Hz": 10.0,
            "gb": 0.1,
            "fid_zero_fill_factor": 2,
        },
    )

    assert deltas
    assert all("fid_zero_fill_factor" not in item for item in deltas)
    assert {tuple(item) for item in deltas} >= {("lb_Hz",)}


def test_nmr_evidence_protects_shift_area_linewidth_and_weak_peaks() -> None:
    control = _snapshot(
        {
            "peaks": [
                {"ppm": 30.0, "fwhm_ppm": 0.5, "area": 100.0, "height": 10.0},
                {"ppm": 20.0, "fwhm_ppm": 0.3, "area": 5.0, "height": 0.5},
            ],
            "peak_area_total": 105.0,
            "mean_fwhm_ppm": 0.4,
            "median_snr": 12.0,
            "Xc_pct": 45.0,
            "negative_fraction": 0.0,
        },
        rmse=1.0,
        baseline=0.7,
    )
    candidate = _snapshot(
        {
            "peaks": [
                {"ppm": 30.01, "fwhm_ppm": 0.51, "area": 99.0, "height": 10.0},
                {"ppm": 19.99, "fwhm_ppm": 0.31, "area": 4.95, "height": 0.5},
            ],
            "peak_area_total": 103.95,
            "mean_fwhm_ppm": 0.41,
            "median_snr": 14.0,
            "Xc_pct": 44.8,
            "negative_fraction": 0.0,
        },
        rmse=0.7,
        baseline=0.85,
    )

    evidence = get_preprocess_adapter("NMR").build_evidence(
        "nmr-c1", control, candidate
    )

    assert evidence.peak_shift == pytest.approx(0.01)
    assert evidence.integrated_area_change <= 0.02
    assert evidence.weak_peak_retention == 1.0
    assert evidence.technique_specific["mean_fwhm_ppm_change"] == pytest.approx(0.025)
    assert evidence.technique_specific["median_snr_change"] == pytest.approx(1 / 6)
