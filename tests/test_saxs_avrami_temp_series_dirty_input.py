from __future__ import annotations

import numpy as np

from polynexus.core.saxs_engine.saxs_temperature import (
    avrami_from_temp_series,
    avrami_kinetics,
)


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
            assert actual_value == expected_value
        elif np.isnan(expected_value):
            assert np.isnan(actual_value)
        else:
            assert actual_value == expected_value


def test_temp_series_coerces_dirty_temperature_and_keeps_selected_order() -> None:
    time_array = np.asarray([1, 2, 3, 4, 5, 6, 7, 8], dtype=object)
    temp_array = np.asarray([100, "bad-temperature", 100, 100, 100, 100, 100, 100], dtype=object)
    xc_array = np.asarray([0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5], dtype=object)

    expected = avrami_kinetics(
        np.asarray([0.0, 2.0, 3.0, 4.0, 5.0, 6.0]),
        np.asarray([0.05, 0.15, 0.2, 0.3, 0.4, 0.5]),
    )
    actual = avrami_from_temp_series(time_array, temp_array, xc_array, 100)

    _assert_result_equal(actual, expected)


def test_temp_series_excludes_nonfinite_time_and_xc_without_reordering() -> None:
    time_array = np.asarray([1.0, np.nan, 3.0, 4.0, 5.0, 6.0, 7.0])
    temp_array = np.asarray([100.0] * 7)
    xc_array = np.asarray([0.05, 0.1, "bad-xc", 0.2, 0.3, 0.4, 0.5], dtype=object)

    expected = avrami_kinetics(
        np.asarray([0.0, 3.0, 4.0, 5.0, 6.0]),
        np.asarray([0.05, 0.2, 0.3, 0.4, 0.5]),
    )
    actual = avrami_from_temp_series(time_array, temp_array, xc_array, 100)

    _assert_result_equal(actual, expected)


def test_temp_series_uses_common_prefix_for_mismatched_arrays() -> None:
    time_array = np.asarray([1, 2, 3, 4, 5, 6, 7], dtype=object)
    temp_array = np.asarray([100, 100, 100, 100, 100, 100, 100], dtype=object)
    xc_array = np.asarray([0.05, 0.1, 0.15, 0.2, 0.3, 0.4], dtype=object)

    expected = avrami_kinetics(
        np.asarray([0.0, 1.0, 2.0, 3.0, 4.0, 5.0]),
        np.asarray([0.05, 0.1, 0.15, 0.2, 0.3, 0.4]),
    )
    actual = avrami_from_temp_series(time_array, temp_array, xc_array, 100)

    _assert_result_equal(actual, expected)


def test_temp_series_returns_invalid_when_fewer_than_five_clean_survivors() -> None:
    result = avrami_from_temp_series(
        np.asarray([1, 2, 3, 4, 5], dtype=object),
        np.asarray([100, "bad", 100, 100, 100], dtype=object),
        np.asarray([0.05, 0.1, 0.15, 0.2, 0.3], dtype=object),
        100,
    )

    assert result["valid"] is False
    assert np.isnan(result["n"])
    assert np.isnan(result["k_sn"])


def test_temp_series_does_not_mutate_caller_arrays() -> None:
    time_array = np.asarray([1, 2, 3, 4, 5, 6], dtype=object)
    temp_array = np.asarray([100, "bad", 100, 100, 100, 100], dtype=object)
    xc_array = np.asarray([0.05, 0.1, 0.15, 0.2, 0.3, 0.4], dtype=object)
    before = (time_array.copy(), temp_array.copy(), xc_array.copy())

    avrami_from_temp_series(time_array, temp_array, xc_array, 100)

    for actual, expected in zip((time_array, temp_array, xc_array), before):
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
