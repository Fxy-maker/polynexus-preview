from __future__ import annotations

import numpy as np
import pytest

from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.saxs_quality_contracts import sanitize_1d_profile
from polynexus.core.saxs_engine.saxs_strain import (
    StrainPhase,
    detect_strain_phase,
    detect_voids,
)


def _dirty_profile() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    clean_q = np.asarray(
        [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.10, 0.12, 0.15, 0.18, 0.22, 0.26, 0.30],
        dtype=float,
    )
    clean_i = np.asarray(clean_q ** -3, dtype=float)
    dirty_q = np.asarray(clean_q[::-1], dtype=object)
    dirty_i = np.asarray(clean_i[::-1], dtype=object)
    dirty_q[3] = "bad-q"
    dirty_q[9] = np.nan
    dirty_i[5] = -1.0
    dirty_i[11] = "bad-intensity"
    return dirty_q, dirty_i, clean_q, clean_i


def _assert_legacy_dict_equal(actual: dict, expected: dict) -> None:
    assert actual.keys() == expected.keys()
    for key in actual:
        actual_value = actual[key]
        expected_value = expected[key]
        if isinstance(expected_value, (bool, str)):
            assert actual_value == expected_value
        elif np.isnan(expected_value):
            assert np.isnan(actual_value)
        else:
            assert actual_value == pytest.approx(expected_value)


def _assert_object_array_unchanged(
    actual: np.ndarray, expected: np.ndarray
) -> None:
    assert actual.shape == expected.shape
    for actual_value, expected_value in zip(actual, expected):
        if (
            isinstance(actual_value, (float, np.floating))
            and isinstance(expected_value, (float, np.floating))
            and np.isnan(actual_value)
            and np.isnan(expected_value)
        ):
            continue
        assert actual_value == expected_value


def test_strain_helpers_match_sanitized_survivors_without_mutating_dirty_input() -> None:
    dirty_q, dirty_i, clean_q, clean_i = _dirty_profile()
    q_before = dirty_q.copy()
    i_before = dirty_i.copy()
    cfg = SAXSConfig()
    sanitized = sanitize_1d_profile(dirty_q, dirty_i)

    expected_phase = detect_strain_phase(
        5.0, 1.0, 1.0, sanitized.q, sanitized.intensity, cfg
    )
    expected_voids = detect_voids(sanitized.q, sanitized.intensity, cfg)

    actual_phase = detect_strain_phase(
        5.0,
        1.0,
        1.0,
        dirty_q,
        dirty_i,
        cfg,
    )
    actual_voids = detect_voids(dirty_q, dirty_i, cfg)

    assert sanitized.q.size == clean_q.size - 4
    assert np.all(np.isfinite(sanitized.q))
    assert np.all(sanitized.q > 0)
    assert np.all(np.diff(sanitized.q) >= 0)
    assert actual_phase is expected_phase
    _assert_legacy_dict_equal(actual_voids, expected_voids)
    _assert_object_array_unchanged(dirty_q, q_before)
    _assert_object_array_unchanged(dirty_i, i_before)


def test_strain_helpers_use_aligned_prefix_for_mismatched_dirty_profiles() -> None:
    dirty_q = np.asarray(
        [0.08, 0.07, "bad-q", 0.06, 0.05, 0.04, 0.03, 0.02, 0.01],
        dtype=object,
    )
    dirty_i = np.asarray([2.0, 3.0, 4.0, -1.0, 5.0, 6.0, 7.0, 8.0], dtype=object)
    cfg = SAXSConfig()
    sanitized = sanitize_1d_profile(dirty_q, dirty_i)
    expected_phase = detect_strain_phase(
        5.0, 1.0, 1.0, sanitized.q, sanitized.intensity, cfg
    )
    expected_voids = detect_voids(sanitized.q, sanitized.intensity, cfg)

    actual_phase = detect_strain_phase(5.0, 1.0, 1.0, dirty_q, dirty_i, cfg)
    actual_voids = detect_voids(dirty_q, dirty_i, cfg)

    assert actual_phase is expected_phase
    _assert_legacy_dict_equal(actual_voids, expected_voids)


def test_empty_strain_helper_inputs_keep_legacy_fail_closed_shapes() -> None:
    cfg = SAXSConfig()

    phase = detect_strain_phase(
        5.0,
        1.1,
        1.0,
        np.asarray([], dtype=float),
        np.asarray([], dtype=float),
        cfg,
    )
    voids = detect_voids(
        np.asarray([], dtype=float), np.asarray([], dtype=float), cfg
    )

    assert phase is StrainPhase.PLASTIC_VOIDING
    assert voids == {
        "has_voids": False,
        "phi_void": np.nan,
        "void_ar": np.nan,
        "void_Rg": np.nan,
        "excess_low_q": np.nan,
        "method": "none",
    }
