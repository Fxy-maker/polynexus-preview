from __future__ import annotations

import numpy as np

from polynexus.core.saxs_residual_analyzer import SAXSResidualAnalyzer


def _baseline(q: np.ndarray) -> np.ndarray:
    return 1200.0 * np.exp(-1.8 * q) + 25.0


def test_saxs_residual_analyzer_detects_peak_mismatch() -> None:
    q = np.linspace(0.03, 3.0, 500)
    fit = _baseline(q)
    obs = fit.copy()
    obs += 260.0 * np.exp(-0.5 * ((q - 0.52) / 0.035) ** 2)

    pattern = SAXSResidualAnalyzer.analyze(q, obs, fit)

    assert pattern.residual_type == "peak_mismatch"
    assert "q=0.5" in pattern.max_residual_region
    assert pattern.summary
    assert pattern.peak_regions


def test_saxs_residual_analyzer_detects_background_drift() -> None:
    q = np.linspace(0.03, 3.0, 500)
    fit = _baseline(q)
    obs = fit.copy()
    obs[q < 0.12] += 320.0

    pattern = SAXSResidualAnalyzer.analyze(q, obs, fit)

    assert pattern.residual_type == "background_drift"
    assert pattern.summary


def test_saxs_residual_analyzer_detects_random_residuals() -> None:
    rng = np.random.default_rng(42)
    q = np.linspace(0.03, 3.0, 500)
    fit = _baseline(q)
    obs = fit + rng.normal(0.0, 6.0, size=q.shape)

    pattern = SAXSResidualAnalyzer.analyze(q, obs, fit)

    assert pattern.residual_type == "random"
    assert pattern.summary
