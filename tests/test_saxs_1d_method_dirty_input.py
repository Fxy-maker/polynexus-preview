from __future__ import annotations

import numpy as np
import pytest

from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.core import (
    kratky_analysis,
    porod_analysis,
    scattering_invariant,
)


def _dirty_profile() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    clean_q = np.linspace(0.1, 1.5, 16)
    clean_i = 2.0 / clean_q**4
    order = np.asarray([8, 0, 12, 2, 10, 4, 14, 6, 1, 9, 3, 11, 5, 15, 7, 13])
    q = clean_q[order].copy()
    intensity = clean_i[order].copy()
    q = np.insert(q, 3, np.nan)
    intensity = np.insert(intensity, 3, clean_i[0])
    intensity[6] = -1.0
    return q, intensity, clean_q, clean_i


def test_scattering_invariant_uses_sorted_signed_survivors_without_mutation():
    q, intensity, clean_q, clean_i = _dirty_profile()
    q_before = q.copy()
    intensity_before = intensity.copy()

    value = scattering_invariant(q, intensity, q_min=0.1, q_max=1.5)
    del clean_q, clean_i
    valid = np.isfinite(q_before) & np.isfinite(intensity_before) & (q_before > 0)
    order = np.argsort(q_before[valid], kind="stable")
    expected_q = q_before[valid][order]
    expected_i = intensity_before[valid][order]
    expected = float(np.trapezoid(expected_q**2 * expected_i, expected_q))

    assert value == pytest.approx(expected)
    assert np.array_equal(q, q_before, equal_nan=True)
    assert np.array_equal(intensity, intensity_before, equal_nan=True)


def test_porod_analysis_excludes_dirty_pairs_and_returns_sorted_finite_payload():
    q, intensity, _clean_q, _clean_i = _dirty_profile()
    payload = porod_analysis(
        q,
        intensity,
        SAXSConfig(q_porod_min=0.1, q_porod_max=1.5),
    )

    assert payload["Kp"] == pytest.approx(2.0)
    assert np.isfinite(payload["q_porod"]).all()
    assert np.all(np.diff(payload["q_porod"]) >= 0)
    assert np.isfinite(payload["Iq4"]).all()


def test_kratky_analysis_is_finite_for_dirty_input_and_fail_closed_when_empty():
    q, intensity, _clean_q, _clean_i = _dirty_profile()
    payload = kratky_analysis(q, intensity, SAXSConfig())

    assert np.isfinite(payload["q"]).all()
    assert np.isfinite(payload["kratky"]).all()
    assert np.isfinite(payload["kratky_norm"]).all()
    assert np.all(np.diff(payload["q"]) >= 0)

    empty = kratky_analysis(np.asarray([]), np.asarray([]), SAXSConfig())
    assert empty["q"].size == 0
    assert empty["kratky"].size == 0
    assert empty["kratky_norm"].size == 0
    assert np.isnan(empty["q_peak_kratky"])
