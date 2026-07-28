from __future__ import annotations

import numpy as np
import pytest

from polynexus.core.saxs_engine.saxs_temperature import detect_melting_from_saxs


def _assert_result_equal(actual: dict, expected: dict) -> None:
    assert actual.keys() == expected.keys()
    for key in actual:
        actual_value = actual[key]
        expected_value = expected[key]
        if np.isnan(expected_value):
            assert np.isnan(actual_value)
        else:
            assert actual_value == pytest.approx(expected_value)


def test_melting_coerces_dirty_temperature_and_keeps_survivor_order() -> None:
    temperatures = np.asarray(
        [100, "bad-temperature", 100, 100, 100, 150, 160, 170],
        dtype=object,
    )
    q_star = np.asarray([1.0] * 8)
    intensities = np.asarray([100, 100, 100, 100, 100, 40, 1, 0.1], dtype=object)

    expected = detect_melting_from_saxs(
        np.asarray([100.0, 100.0, 100.0, 100.0, 150.0, 160.0, 170.0]),
        np.asarray([1.0] * 7),
        np.asarray([100.0, 100.0, 100.0, 100.0, 40.0, 1.0, 0.1]),
    )
    actual = detect_melting_from_saxs(temperatures, q_star, intensities)

    _assert_result_equal(actual, expected)


def test_melting_excludes_nonfinite_pairs_without_reordering() -> None:
    temperatures = np.asarray([100.0, np.nan, 100.0, 100.0, 150.0, 160.0, 170.0])
    q_star = np.asarray([1.0] * 7)
    intensities = np.asarray([100.0, 100.0, 100.0, 100.0, 40.0, 1.0, 0.1])

    expected = detect_melting_from_saxs(
        np.asarray([100.0, 100.0, 100.0, 150.0, 160.0, 170.0]),
        np.asarray([1.0] * 6),
        np.asarray([100.0, 100.0, 100.0, 40.0, 1.0, 0.1]),
    )
    actual = detect_melting_from_saxs(temperatures, q_star, intensities)

    _assert_result_equal(actual, expected)


def test_melting_uses_common_prefix_for_consumed_arrays() -> None:
    temperatures = np.asarray([100, 100, 100, 100, 150, 160, 170], dtype=object)
    q_star = np.asarray([1.0] * 7)
    intensities = np.asarray([100, 100, 100, 100, 40, 1], dtype=object)

    expected = detect_melting_from_saxs(
        np.asarray([100.0, 100.0, 100.0, 100.0, 150.0, 160.0]),
        np.asarray([1.0] * 6),
        np.asarray([100.0, 100.0, 100.0, 100.0, 40.0, 1.0]),
    )
    actual = detect_melting_from_saxs(temperatures, q_star, intensities)

    _assert_result_equal(actual, expected)


def test_melting_returns_legacy_invalid_result_for_insufficient_pairs() -> None:
    result = detect_melting_from_saxs(
        np.asarray([100, "bad", 100, 100, 100], dtype=object),
        np.asarray([1.0] * 5),
        np.asarray([100, 100, 100, 100, 100], dtype=object),
    )

    assert set(result) == {
        "Tm_onset_C",
        "Tm_50pct_C",
        "Tm_end_C",
        "melting_range_C",
    }
    assert all(np.isnan(value) for value in result.values())


def test_melting_does_not_mutate_caller_arrays() -> None:
    temperatures = np.asarray([100, "bad", 100, 100, 150, 160, 170], dtype=object)
    q_star = np.asarray([1.0] * 7)
    intensities = np.asarray([100, 100, 100, 100, 40, 1, 0.1], dtype=object)
    before = (temperatures.copy(), q_star.copy(), intensities.copy())

    detect_melting_from_saxs(temperatures, q_star, intensities)

    for actual, expected in zip((temperatures, q_star, intensities), before):
        np.testing.assert_array_equal(actual, expected)
