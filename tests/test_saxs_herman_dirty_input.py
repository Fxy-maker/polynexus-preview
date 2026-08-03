from __future__ import annotations

import numpy as np
import pytest

from polynexus.core.saxs_engine.saxs_strain import herman_orientation_factor


def _profile() -> tuple[np.ndarray, np.ndarray]:
    chi = np.linspace(-np.pi / 12, np.pi / 12, 12)
    intensity = 2.0 + 4.0 * np.cos(chi) ** 2
    return chi, intensity


def _assert_object_arrays_unchanged(actual: np.ndarray, expected: np.ndarray) -> None:
    for left, right in zip(actual, expected):
        if isinstance(left, float) and np.isnan(left):
            assert isinstance(right, float) and np.isnan(right)
        else:
            assert left == right


def test_herman_discards_nonfinite_pairs_and_matches_clean_survivors() -> None:
    chi, intensity = _profile()
    dirty_chi = np.asarray(chi[::-1], dtype=object)
    dirty_intensity = np.asarray(intensity[::-1], dtype=object)
    dirty_chi[2] = "bad-angle"
    dirty_intensity[7] = np.nan

    valid = []
    for chi_value, intensity_value in zip(dirty_chi, dirty_intensity):
        try:
            chi_number = float(chi_value)
            intensity_number = float(intensity_value)
        except (TypeError, ValueError):
            continue
        if np.isfinite(chi_number) and np.isfinite(intensity_number):
            valid.append((chi_number, intensity_number))
    valid.sort()
    expected_chi = np.asarray([pair[0] for pair in valid])
    expected_intensity = np.asarray([pair[1] for pair in valid])

    dirty = herman_orientation_factor(
        dirty_intensity, np.ones_like(dirty_intensity), dirty_chi, None
    )
    clean = herman_orientation_factor(
        expected_intensity, np.ones_like(expected_intensity), expected_chi, None
    )

    assert dirty["f"] == pytest.approx(clean["f"])
    assert dirty["f_sub"] == pytest.approx(clean["f_sub"])


def test_herman_mismatch_and_empty_survivors_fail_closed() -> None:
    chi, intensity = _profile()
    mismatched = herman_orientation_factor(intensity, np.ones(3), chi[:3], None)
    assert np.isnan(mismatched["f"])
    assert mismatched["method"] == "none"

    empty = herman_orientation_factor(
        ["bad", np.nan], [1.0, 2.0], ["bad", np.inf], None
    )
    assert np.isnan(empty["f"])
    assert np.isnan(empty["f_sub"])
    assert np.isnan(empty["f_eq"])
    assert empty["method"] == "none"


def test_herman_keeps_finite_negative_intensity_and_caller_arrays() -> None:
    chi, intensity = _profile()
    dirty_chi = np.asarray(chi[::-1], dtype=object)
    dirty_intensity = np.asarray(intensity[::-1], dtype=object)
    dirty_intensity[4] = -0.5
    chi_before = dirty_chi.copy()
    intensity_before = dirty_intensity.copy()

    result = herman_orientation_factor(dirty_intensity, None, dirty_chi, None)

    assert result["method"] == "azimuthal_integral"
    assert np.isfinite(result["f"])
    _assert_object_arrays_unchanged(dirty_chi, chi_before)
    _assert_object_arrays_unchanged(dirty_intensity, intensity_before)
