from __future__ import annotations

import numpy as np

from polynexus.core.residual_analyzer import ResidualAnalyzer


def test_systematic_peak_residual_is_detected() -> None:
    two_theta = np.linspace(2.0, 45.0, 1200)
    y_fit = np.exp(-0.5 * ((two_theta - 20.0) / 0.5) ** 2)
    y_obs = y_fit.copy()
    y_obs[two_theta < 5.0] += 1.0
    y_obs[(two_theta >= 19.8) & (two_theta <= 20.2)] += 0.15

    pattern = ResidualAnalyzer.analyze(y_obs, y_fit, two_theta)

    assert pattern.residual_type == "systematic_peak"
    assert "20" in pattern.max_residual_region
    assert "2." not in pattern.max_residual_region
    assert pattern.summary


def test_background_drift_is_detected() -> None:
    two_theta = np.linspace(2.0, 30.0, 1000)
    y_fit = np.zeros_like(two_theta)
    y_obs = np.zeros_like(two_theta)
    y_obs[(two_theta >= 5.0) & (two_theta < 10.0)] += 0.3
    y_obs[two_theta < 5.0] += 1.0

    pattern = ResidualAnalyzer.analyze(y_obs, y_fit, two_theta)

    assert pattern.residual_type == "background_drift"
    assert pattern.summary


def test_random_residual_is_detected() -> None:
    rng = np.random.default_rng(42)
    two_theta = np.linspace(10.0, 30.0, 1000)
    y_fit = np.sin(two_theta / 5.0)
    y_obs = y_fit + rng.normal(0.0, 0.01, size=len(two_theta))

    pattern = ResidualAnalyzer.analyze(y_obs, y_fit, two_theta)

    assert pattern.residual_type == "random"
    assert pattern.summary
