from __future__ import annotations

import numpy as np
import pytest

from polynexus.core.saxs_engine import (
    SAXSConfig,
    bragg_long_period,
    correlation_function,
    lorentz_fit_long_period,
)


def _profile() -> tuple[np.ndarray, np.ndarray]:
    q = np.linspace(0.05, 1.8, 80)
    intensity = (1.0 + 6.0 * np.exp(-((q - 0.55) / 0.045) ** 2)) / q**2
    return q, intensity


def _dirty_profile() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    q, intensity = _profile()
    dirty_q = np.asarray(q[::-1], dtype=object)
    dirty_intensity = np.asarray(intensity[::-1], dtype=object)
    dirty_q[5] = "bad-q"
    dirty_q[20] = np.nan
    dirty_intensity[30] = -1.0

    valid_pairs = []
    for q_value, intensity_value in zip(dirty_q, dirty_intensity):
        try:
            q_number = float(q_value)
            intensity_number = float(intensity_value)
        except (TypeError, ValueError):
            continue
        if np.isfinite(q_number) and np.isfinite(intensity_number):
            if q_number > 0 and intensity_number > 0:
                valid_pairs.append((q_number, intensity_number))
    valid_pairs.sort()
    expected_q = np.asarray([pair[0] for pair in valid_pairs])
    expected_intensity = np.asarray([pair[1] for pair in valid_pairs])
    return dirty_q, dirty_intensity, expected_q, expected_intensity


def test_long_period_helpers_sanitize_dirty_profile_like_clean_reference() -> None:
    dirty_q, dirty_intensity, expected_q, expected_intensity = _dirty_profile()
    cfg = SAXSConfig()

    dirty_bragg = bragg_long_period(dirty_q, dirty_intensity)
    clean_bragg = bragg_long_period(expected_q, expected_intensity)
    assert np.isfinite(dirty_bragg[0])
    assert dirty_bragg[0] == pytest.approx(clean_bragg[0])
    assert dirty_bragg[1] == pytest.approx(clean_bragg[1])

    dirty_lorentz = lorentz_fit_long_period(dirty_q, dirty_intensity, cfg)
    clean_lorentz = lorentz_fit_long_period(expected_q, expected_intensity, cfg)
    assert dirty_lorentz[0] == pytest.approx(clean_lorentz[0])
    assert dirty_lorentz[1] == pytest.approx(clean_lorentz[1])

    dirty_correlation = correlation_function(dirty_q, dirty_intensity, cfg)
    clean_correlation = correlation_function(expected_q, expected_intensity, cfg)
    assert dirty_correlation["Q_invariant"] == pytest.approx(
        clean_correlation["Q_invariant"]
    )
    np.testing.assert_allclose(dirty_correlation["q_raw"], expected_q)
    np.testing.assert_allclose(dirty_correlation["I_raw"], expected_intensity)


def test_long_period_helpers_fail_closed_for_empty_survivors() -> None:
    q = ["bad-q", np.nan, -1.0]
    intensity = [0.0, -1.0, np.nan]
    cfg = SAXSConfig()

    bragg = bragg_long_period(q, intensity)
    assert np.isnan(bragg[0])
    assert np.isnan(bragg[1])

    lorentz = lorentz_fit_long_period(q, intensity, cfg)
    assert np.isnan(lorentz[0])
    assert lorentz[1] == 0.0
    assert lorentz[2]["q_corr_max"] == cfg.q_corr_max

    correlation = correlation_function(q, intensity, cfg)
    assert correlation["r"].size == 0
    assert correlation["gamma"].size == 0
    assert np.isnan(correlation["Q_invariant"])
    assert correlation["q_corr_max"] == cfg.q_corr_max


def test_long_period_helpers_do_not_mutate_caller_arrays() -> None:
    dirty_q, dirty_intensity, _expected_q, _expected_intensity = _dirty_profile()
    q_before = dirty_q.copy()
    intensity_before = dirty_intensity.copy()
    cfg = SAXSConfig()

    bragg_long_period(dirty_q, dirty_intensity)
    lorentz_fit_long_period(dirty_q, dirty_intensity, cfg)
    correlation_function(dirty_q, dirty_intensity, cfg)

    for actual, expected in zip(dirty_q, q_before):
        if isinstance(actual, float) and np.isnan(actual):
            assert isinstance(expected, float) and np.isnan(expected)
        else:
            assert actual == expected
    for actual, expected in zip(dirty_intensity, intensity_before):
        if isinstance(actual, float) and np.isnan(actual):
            assert isinstance(expected, float) and np.isnan(expected)
        else:
            assert actual == expected
