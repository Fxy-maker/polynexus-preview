from __future__ import annotations

import numpy as np

from polynexus.core.waxs_residual_analyzer import WAXSResidualAnalyzer


def _gaussian(x: np.ndarray, center: float, sigma: float, amplitude: float = 1.0) -> np.ndarray:
    return amplitude * np.exp(-0.5 * ((x - center) / sigma) ** 2)


def _context(peaks: list[dict[str, float]], two_theta_offset: float = 0.0) -> dict[str, object]:
    return {
        "output_parameters": {
            "peaks": peaks,
            "peak_centers": [item["two_theta"] for item in peaks],
            "peak_widths": [item["fwhm_deg"] for item in peaks],
            "peak_areas": [item.get("area", 1.0) for item in peaks],
            "background_method": "linear",
            "amorphous_subtraction": "polynomial",
            "amorphous_n_peaks": 2,
            "two_theta_offset": two_theta_offset,
            "crystallinity_method": "peak_deconvolution",
        },
        "config_snapshot": {
            "background_method": "linear",
            "amorphous_subtraction": "polynomial",
            "amorphous_n_peaks": 2,
            "two_theta_offset": two_theta_offset,
            "peak_distance": 0.8,
            "max_peaks": 8,
        },
    }


def test_waxs_residual_analyzer_detects_peak_position_bias() -> None:
    two_theta = np.linspace(5.0, 40.0, 1200)
    y_fit = _gaussian(two_theta, 20.0, 0.35)
    y_obs = _gaussian(two_theta, 20.18, 0.35)

    pattern = WAXSResidualAnalyzer.analyze(
        y_obs,
        y_fit,
        two_theta,
        context=_context([{"two_theta": 20.0, "fwhm_deg": 0.35, "area": 1.0}], two_theta_offset=0.08),
    )

    assert pattern.residual_type == "peak_position_bias"
    assert "2theta=" in pattern.max_residual_region
    assert pattern.summary


def test_waxs_residual_analyzer_detects_peak_count_underfit() -> None:
    two_theta = np.linspace(5.0, 40.0, 1200)
    y_fit = _gaussian(two_theta, 20.0, 0.45)
    y_obs = _gaussian(two_theta, 17.9, 0.32) + _gaussian(two_theta, 21.8, 0.32)

    pattern = WAXSResidualAnalyzer.analyze(
        y_obs,
        y_fit,
        two_theta,
        context=_context([{"two_theta": 20.0, "fwhm_deg": 0.45, "area": 1.0}]),
    )

    assert pattern.residual_type == "peak_count_underfit"
    assert pattern.peak_regions
    assert pattern.summary


def test_waxs_residual_analyzer_detects_low_angle_background_drift() -> None:
    two_theta = np.linspace(5.0, 40.0, 1200)
    y_fit = _gaussian(two_theta, 20.0, 0.45)
    y_obs = y_fit.copy()
    y_obs[two_theta < 9.8] += 2.4

    pattern = WAXSResidualAnalyzer.analyze(
        y_obs,
        y_fit,
        two_theta,
        context=_context([{"two_theta": 20.0, "fwhm_deg": 0.45, "area": 1.0}]),
    )

    assert pattern.residual_type == "low_angle_background_drift"
    assert "low-angle" in pattern.summary.lower()
    assert pattern.summary


def test_waxs_residual_analyzer_detects_peak_count_overfit() -> None:
    two_theta = np.linspace(5.0, 40.0, 1200)
    y_obs = _gaussian(two_theta, 20.0, 0.95)
    y_fit = y_obs + 0.015 * np.cos(two_theta * 4.5)
    peaks = [
        {"two_theta": 19.4 + 0.15 * idx, "fwhm_deg": 0.16, "area": 1.0}
        for idx in range(5)
    ]

    pattern = WAXSResidualAnalyzer.analyze(
        y_obs,
        y_fit,
        two_theta,
        context=_context(peaks),
    )

    assert pattern.residual_type == "peak_count_overfit"
    assert pattern.summary


def test_waxs_residual_analyzer_detects_amorphous_background_bias() -> None:
    two_theta = np.linspace(5.0, 40.0, 1200)
    y_fit = _gaussian(two_theta, 17.9, 0.35) + _gaussian(two_theta, 21.8, 0.35)
    halo = 0.8 * np.exp(-0.5 * ((two_theta - 15.0) / 4.8) ** 2)
    y_obs = y_fit + halo

    pattern = WAXSResidualAnalyzer.analyze(
        y_obs,
        y_fit,
        two_theta,
        context=_context(
            [
                {"two_theta": 17.9, "fwhm_deg": 0.35, "area": 1.0},
                {"two_theta": 21.8, "fwhm_deg": 0.35, "area": 0.9},
            ]
        ),
    )

    assert pattern.residual_type == "amorphous_background_bias"
    assert "background" in pattern.summary.lower() or "amorphous" in pattern.summary.lower()


def test_waxs_residual_analyzer_detects_peak_width_mismatch() -> None:
    two_theta = np.linspace(5.0, 40.0, 1200)
    y_fit = _gaussian(two_theta, 20.0, 0.28)
    y_obs = _gaussian(two_theta, 20.0, 0.48, 0.58)

    pattern = WAXSResidualAnalyzer.analyze(
        y_obs,
        y_fit,
        two_theta,
        context=_context([{"two_theta": 20.0, "fwhm_deg": 0.28, "area": 1.0}]),
    )

    assert pattern.residual_type == "peak_width_mismatch"
    assert "width" in pattern.summary.lower()
