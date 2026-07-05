from __future__ import annotations

import numpy as np

from polynexus.core.dsc_residual_analyzer import DSCResidualAnalyzer


def test_dsc_residual_detects_peak_shift() -> None:
    t = np.linspace(50.0, 320.0, 1200)
    baseline = 0.002 * (t - t.mean())
    y_fit = baseline - np.exp(-0.5 * ((t - 220.0) / 6.0) ** 2)
    y_obs = baseline - np.exp(-0.5 * ((t - 224.0) / 6.0) ** 2)

    pattern = DSCResidualAnalyzer.analyze(t, y_obs, y_fit)

    assert pattern.residual_type == "melting_peak_shift"
    assert "T=2" in pattern.max_residual_region
    assert pattern.summary


def test_dsc_residual_detects_baseline_drift() -> None:
    t = np.linspace(50.0, 320.0, 1200)
    y_fit = np.zeros_like(t)
    y_obs = np.where(t < 130.0, 0.8, 0.0)

    pattern = DSCResidualAnalyzer.analyze(t, y_obs, y_fit)

    assert pattern.residual_type == "baseline_drift_low_t"


def test_dsc_residual_detects_high_temperature_baseline_drift() -> None:
    t = np.linspace(50.0, 320.0, 1200)
    y_fit = np.zeros_like(t)
    y_obs = np.where(t > 270.0, -0.8, 0.0)

    pattern = DSCResidualAnalyzer.analyze(t, y_obs, y_fit)

    assert pattern.residual_type == "baseline_drift_high_t"


def test_dsc_residual_detects_tg_step_missing() -> None:
    t = np.linspace(50.0, 320.0, 1200)
    y_fit = np.zeros_like(t)
    y_obs = np.where((t >= 72.0) & (t <= 110.0), 0.55, 0.0)

    pattern = DSCResidualAnalyzer.analyze(t, y_obs, y_fit)

    assert pattern.residual_type == "tg_step_missing"


def test_dsc_residual_detects_window_too_narrow_and_too_wide() -> None:
    t = np.linspace(50.0, 320.0, 1200)

    narrow_fit = -np.exp(-0.5 * ((t - 220.0) / 1.0) ** 2)
    narrow_obs = -np.exp(-0.5 * ((t - 222.0) / 1.0) ** 2)
    narrow_pattern = DSCResidualAnalyzer.analyze(t, narrow_obs, narrow_fit)
    assert narrow_pattern.residual_type == "event_window_too_narrow"

    wide_fit = -np.exp(-0.5 * ((t - 220.0) / 14.0) ** 2)
    wide_obs = -np.exp(-0.5 * ((t - 230.0) / 14.0) ** 2)
    wide_pattern = DSCResidualAnalyzer.analyze(t, wide_obs, wide_fit)
    assert wide_pattern.residual_type == "event_window_too_wide"


def test_dsc_residual_detects_cold_crystallization_overlap_or_segment_split() -> None:
    t = np.linspace(50.0, 320.0, 1200)
    y_fit = np.zeros_like(t)
    y_obs = np.where((t > 165.0) & (t < 175.0), 0.6, 0.0) + np.where((t > 185.0) & (t < 195.0), 0.55, 0.0)

    pattern = DSCResidualAnalyzer.analyze(t, y_obs, y_fit)

    assert pattern.residual_type in {"cold_crystallization_overlap", "multi_event_underfit", "segment_split_issue"}


def test_dsc_residual_random_noise_is_random() -> None:
    rng = np.random.default_rng(42)
    t = np.linspace(100.0, 300.0, 1200)
    y_fit = np.zeros_like(t)
    y_obs = rng.normal(0.0, 0.01, size=t.size)

    pattern = DSCResidualAnalyzer.analyze(t, y_obs, y_fit)

    assert pattern.residual_type in {"random", "noise_dominant"}
