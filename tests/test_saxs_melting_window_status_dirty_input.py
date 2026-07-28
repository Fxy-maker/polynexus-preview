from __future__ import annotations

import numpy as np

from polynexus.core.saxs_engine.saxs_temperature import classify_melting_window_status


def test_melting_window_status_coerces_dirty_scalars_and_sequence() -> None:
    clean = classify_melting_window_status(
        195.0,
        np.nan,
        205.0,
        220.0,
        np.asarray([170.0, 185.0, 195.0, 220.0]),
    )
    dirty = classify_melting_window_status(
        "195",
        "bad-onset",
        "205",
        "220",
        np.asarray([170.0, "bad-temperature", 185.0, 195.0, 220.0], dtype=object),
    )

    assert clean == ("near_onset", "melting_onset_unresolved_peak_only")
    assert dirty == clean


def test_melting_window_status_invalid_temperature_is_undetermined() -> None:
    result = classify_melting_window_status(
        "bad-temperature",
        195.0,
        205.0,
        220.0,
        np.asarray([170.0, 185.0, 205.0]),
    )

    assert result == ("undetermined", "temperature_unresolved")


def test_melting_window_status_coerces_expected_melt_hint() -> None:
    clean = classify_melting_window_status(
        220.0,
        np.nan,
        np.nan,
        np.nan,
        np.asarray([170.0, 180.0, 190.0]),
        expected_melt_C=220.0,
    )
    dirty = classify_melting_window_status(
        "220",
        "bad-onset",
        "bad-peak",
        "bad-end",
        np.asarray([170.0, "bad-temperature", 180.0, 190.0], dtype=object),
        expected_melt_C="220",
    )

    assert clean == ("undetermined", "expected_melt_prior_hint")
    assert dirty == clean


def test_melting_window_status_nonfinite_values_keep_existing_unresolved_reason() -> None:
    result = classify_melting_window_status(
        np.nan,
        np.nan,
        np.nan,
        np.nan,
        np.asarray([np.nan, "bad-temperature"], dtype=object),
        expected_melt_C=np.nan,
    )

    assert result == ("undetermined", "temperature_unresolved")


def test_melting_window_status_does_not_mutate_temperature_sequence() -> None:
    temperatures = np.asarray([170.0, "bad-temperature", 185.0, 195.0], dtype=object)
    before = temperatures.copy()

    classify_melting_window_status(195.0, np.nan, 205.0, 220.0, temperatures)

    np.testing.assert_array_equal(temperatures, before)
