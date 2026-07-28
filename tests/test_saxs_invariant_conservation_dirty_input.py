from __future__ import annotations

import numpy as np
import pytest

from polynexus.core.saxs_engine.saxs_strain import check_invariant_conservation


def _assert_result_equal(actual: dict, expected: dict) -> None:
    assert actual.keys() == expected.keys()
    for key in actual:
        actual_value = actual[key]
        expected_value = expected[key]
        if isinstance(expected_value, bool):
            assert actual_value == expected_value
        elif np.isnan(expected_value):
            assert np.isnan(actual_value)
        else:
            assert actual_value == pytest.approx(expected_value)


def test_invariant_conservation_coerces_dirty_pairs_in_source_order() -> None:
    strains = np.asarray([0.0, "bad-strain", 0.2, 0.3, 0.4], dtype=object)
    q_values = np.asarray([10.0, 10.0, 11.0, 10.0, 9.0], dtype=object)

    expected = check_invariant_conservation(
        np.asarray([0.0, 0.2, 0.3, 0.4]),
        np.asarray([10.0, 11.0, 10.0, 9.0]),
    )
    actual = check_invariant_conservation(strains, q_values)

    _assert_result_equal(actual, expected)


def test_invariant_conservation_excludes_nonfinite_pairs() -> None:
    strains = np.asarray([0.0, np.nan, 0.2, 0.3, 0.4])
    q_values = np.asarray([10.0, 10.0, np.nan, 10.0, 9.0])

    expected = check_invariant_conservation(
        np.asarray([0.0, 0.3, 0.4]),
        np.asarray([10.0, 10.0, 9.0]),
    )
    actual = check_invariant_conservation(strains, q_values)

    _assert_result_equal(actual, expected)


def test_invariant_conservation_uses_common_prefix_for_mismatched_arrays() -> None:
    strains = np.asarray([0.0, 0.1, 0.2, 0.3, 0.4], dtype=object)
    q_values = np.asarray([10.0, 10.5, 10.0, 9.5], dtype=object)

    expected = check_invariant_conservation(
        np.asarray([0.0, 0.1, 0.2, 0.3]),
        np.asarray([10.0, 10.5, 10.0, 9.5]),
    )
    actual = check_invariant_conservation(strains, q_values)

    _assert_result_equal(actual, expected)


def test_invariant_conservation_coerces_tolerance_and_rejects_bad_tolerance() -> None:
    strains = np.asarray([0.0, 0.1, 0.2])
    q_values = np.asarray([10.0, 11.0, 10.0])

    numeric = check_invariant_conservation(strains, q_values, tolerance=0.2)
    numeric_string = check_invariant_conservation(strains, q_values, tolerance="0.2")
    malformed = check_invariant_conservation(strains, q_values, tolerance="bad")

    _assert_result_equal(numeric_string, numeric)
    assert bool(malformed["conserved"]) is False
    assert np.isfinite(malformed["Q_cv"])


def test_invariant_conservation_keeps_legacy_invalid_and_negative_q_behavior() -> None:
    insufficient = check_invariant_conservation(
        np.asarray([0.0, "bad-strain"], dtype=object),
        np.asarray([10.0, 10.0], dtype=object),
    )
    negative = check_invariant_conservation(
        np.asarray([0.0, 0.1, 0.2]),
        np.asarray([-2.0, -2.0, -2.0]),
    )

    assert insufficient["conserved"] is False
    assert np.isnan(insufficient["Q_mean"])
    assert bool(negative["conserved"]) is False
    assert negative["Q_mean"] == pytest.approx(-2.0)
    assert np.isnan(negative["Q_cv"])


def test_invariant_conservation_does_not_mutate_caller_arrays() -> None:
    strains = np.asarray([0.0, "bad-strain", 0.2, 0.3], dtype=object)
    q_values = np.asarray([10.0, 10.0, 11.0, 10.0], dtype=object)
    before = (strains.copy(), q_values.copy())

    check_invariant_conservation(strains, q_values)

    np.testing.assert_array_equal(strains, before[0])
    np.testing.assert_array_equal(q_values, before[1])
