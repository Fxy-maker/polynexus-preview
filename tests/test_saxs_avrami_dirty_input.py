from __future__ import annotations

import numpy as np
import pytest

from polynexus.core.saxs_engine.saxs_temperature import avrami_kinetics


def _dirty_avrami_input() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    times = np.asarray(["1", "bad-time", 3.0, np.nan, 5.0, 6.0, 7.0, 8.0], dtype=object)
    xc_values = np.asarray([0.05, 0.1, 0.15, 0.2, "bad-xc", 0.3, 0.4, 0.5], dtype=object)
    survivor_times = np.asarray([1.0, 3.0, 6.0, 7.0, 8.0])
    survivor_xc = np.asarray([0.05, 0.15, 0.3, 0.4, 0.5])
    return times, xc_values, survivor_times, survivor_xc


def _assert_result_equal(actual: dict, expected: dict) -> None:
    assert actual.keys() == expected.keys()
    for key in actual:
        actual_value = actual[key]
        expected_value = expected[key]
        if expected_value is None or isinstance(expected_value, bool):
            assert actual_value == expected_value
        elif isinstance(expected_value, str):
            assert actual_value == expected_value
        elif isinstance(expected_value, tuple):
            assert actual_value == pytest.approx(expected_value)
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


def test_avrami_coerces_dirty_pairs_without_mutating_inputs() -> None:
    times, xc_values, survivor_times, survivor_xc = _dirty_avrami_input()
    times_before = times.copy()
    xc_before = xc_values.copy()

    expected = avrami_kinetics(survivor_times, survivor_xc)
    actual = avrami_kinetics(times, xc_values)

    _assert_result_equal(actual, expected)
    _assert_object_array_unchanged(times, times_before)
    _assert_object_array_unchanged(xc_values, xc_before)


def test_avrami_uses_common_prefix_for_mismatched_arrays() -> None:
    times = np.asarray([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0], dtype=object)
    xc_values = np.asarray([0.05, 0.1, 0.15, 0.2, 0.3, 0.4], dtype=object)

    expected = avrami_kinetics(
        np.asarray([1.0, 2.0, 3.0, 4.0, 5.0, 6.0]),
        np.asarray([0.05, 0.1, 0.15, 0.2, 0.3, 0.4]),
    )
    actual = avrami_kinetics(times, xc_values)

    _assert_result_equal(actual, expected)


def test_avrami_empty_input_keeps_legacy_invalid_result() -> None:
    result = avrami_kinetics(np.asarray([]), np.asarray([]))

    assert result["valid"] is False
    assert np.isnan(result["n"])
    assert np.isnan(result["R2"])
    assert result["fit_range"] is None
