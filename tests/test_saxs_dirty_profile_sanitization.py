from __future__ import annotations

import json

import numpy as np

from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine import core as saxs_core
from polynexus.core.saxs_engine import saxs_quality_contracts as contracts


def test_sanitizer_drops_invalid_pairs_and_stably_sorts_without_mutating_inputs():
    q = np.array([0.03, np.nan, 0.01, 0.02, 0.02])
    intensity = np.array([3.0, 4.0, -1.0, 2.0, 5.0])
    q_before, intensity_before = q.copy(), intensity.copy()

    sanitizer = getattr(contracts, "sanitize_1d_profile", None)
    assert callable(sanitizer)
    sanitized = sanitizer(q, intensity)

    assert sanitized.q.tolist() == [0.02, 0.02, 0.03]
    assert sanitized.intensity.tolist() == [2.0, 5.0, 3.0]
    assert sanitized.actions == (
        "invalid_pairs_dropped",
        "q_sorted",
        "duplicate_q_retained",
    )
    assert sanitized.q.flags.writeable is False
    assert sanitized.intensity.flags.writeable is False
    assert np.array_equal(q, q_before, equal_nan=True)
    assert np.array_equal(intensity, intensity_before, equal_nan=True)

def test_sanitizer_aligns_length_mismatch_without_padding():
    sanitizer = getattr(contracts, "sanitize_1d_profile", None)
    assert callable(sanitizer)

    sanitized = sanitizer([0.02, 0.03, 0.04], [1.0, 2.0])

    assert sanitized.q.tolist() == [0.02, 0.03]
    assert sanitized.intensity.tolist() == [1.0, 2.0]
    assert sanitized.original_point_count == 3
    assert sanitized.aligned_point_count == 2
    assert sanitized.actions == ("axis_length_aligned",)


def test_sanitizer_preserves_convertible_neighbors_around_malformed_tokens():
    sanitizer = getattr(contracts, "sanitize_1d_profile", None)
    assert callable(sanitizer)

    sanitized = sanitizer(
        [0.02, "not-a-q", 0.04, 0.05],
        [1.0, 2.0, "not-an-intensity", 4.0],
    )

    assert sanitized.q.tolist() == [0.02, 0.05]
    assert sanitized.intensity.tolist() == [1.0, 4.0]
    assert sanitized.original_point_count == 4
    assert sanitized.aligned_point_count == 4
    assert sanitized.actions == ("invalid_pairs_dropped",)


def test_quality_report_keeps_malformed_tokens_as_explicit_invalid_points():
    report = contracts.build_data_quality_report(
        [0.02, "not-a-q", 0.04],
        [1.0, 2.0, "not-an-intensity"],
    ).to_dict()

    assert report["original_point_count"] == 3
    assert report["invalid_point_count"] == 2
    assert report["nonfinite_q_count"] == 1
    assert report["nonfinite_intensity_count"] == 1
    assert "q_nonfinite" in report["reason_codes"]
    assert "intensity_nonfinite" in report["reason_codes"]


def test_quality_actions_are_ordered_and_strict_json_safe():
    report = contracts.build_data_quality_report(
        [0.02, 0.01],
        [2.0, 1.0],
        actions=("q_sorted", "q_sorted", "invalid_pairs_dropped"),
    )

    payload = json.loads(json.dumps(report.to_dict(), allow_nan=False))

    assert payload["actions"] == ["q_sorted", "invalid_pairs_dropped"]


def test_analyze_single_uses_a_finite_positive_analysis_profile():
    q = np.linspace(0.02, 1.8, 80)
    intensity = 180.0 * np.exp(-(q**2) * 2.2) + 8.0
    q[8] = np.nan
    q[12], q[13] = q[13], q[12]
    intensity[20] = np.nan
    intensity[21] = -1.0

    q_before, intensity_before = q.copy(), intensity.copy()
    result = saxs_core.analyze_single(
        q,
        intensity,
        SAXSConfig(savgol_window=5, savgol_order=2),
    )

    assert np.all(np.isfinite(result.q))
    assert np.all(result.q > 0)
    assert np.all(np.isfinite(result.I))
    assert np.all(result.I > 0)
    assert "invalid_pairs_dropped" in result.data_quality_report["actions"]
    assert "q_sorted" in result.data_quality_report["actions"]
    assert np.array_equal(q, q_before, equal_nan=True)
    assert np.array_equal(intensity, intensity_before, equal_nan=True)
