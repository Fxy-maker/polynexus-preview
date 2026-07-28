from __future__ import annotations

import numpy as np
import pytest

from polynexus.core.saxs_engine.saxs_temperature import gibbs_thomson_analysis


def _dirty_gibbs_input() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    temperatures = np.asarray(
        ["100", "bad-temperature", 120.0, np.nan, 140.0, 150.0, 160.0, 170.0],
        dtype=object,
    )
    lc_values = np.asarray(
        [2.0, 2.2, -1.0, 2.6, "bad-lc", 3.0, 3.2, 3.4],
        dtype=object,
    )
    survivor_temperatures = np.asarray([100.0, 150.0, 160.0, 170.0])
    survivor_lc = np.asarray([2.0, 3.0, 3.2, 3.4])
    return temperatures, lc_values, survivor_temperatures, survivor_lc


def _assert_result_equal(actual: dict, expected: dict) -> None:
    assert actual.keys() == expected.keys()
    for key in actual:
        actual_value = actual[key]
        expected_value = expected[key]
        if expected_value is None or isinstance(expected_value, bool):
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


def test_gibbs_thomson_coerces_dirty_pairs_without_mutating_inputs() -> None:
    temperatures, lc_values, survivor_temperatures, survivor_lc = _dirty_gibbs_input()
    temperatures_before = temperatures.copy()
    lc_before = lc_values.copy()

    expected = gibbs_thomson_analysis(survivor_temperatures, survivor_lc)
    actual = gibbs_thomson_analysis(temperatures, lc_values)

    _assert_result_equal(actual, expected)
    _assert_object_array_unchanged(temperatures, temperatures_before)
    _assert_object_array_unchanged(lc_values, lc_before)


def test_gibbs_thomson_uses_common_prefix_for_mismatched_arrays() -> None:
    temperatures = np.asarray([100.0, 110.0, 120.0, 130.0, 140.0, 150.0], dtype=object)
    lc_values = np.asarray([2.0, 2.2, 2.4, 2.6, "bad-lc"], dtype=object)

    expected = gibbs_thomson_analysis(
        np.asarray([100.0, 110.0, 120.0, 130.0]),
        np.asarray([2.0, 2.2, 2.4, 2.6]),
    )
    actual = gibbs_thomson_analysis(temperatures, lc_values)

    _assert_result_equal(actual, expected)


def test_gibbs_thomson_empty_input_keeps_legacy_invalid_result() -> None:
    result = gibbs_thomson_analysis(np.asarray([]), np.asarray([]))

    assert result["valid"] is False
    assert np.isnan(result["Tm_inf_K"])
    assert np.isnan(result["R2"])
