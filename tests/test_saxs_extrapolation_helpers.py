from __future__ import annotations

import importlib

import numpy as np


def test_extrapolate_guinier_prepends_boundary_points_without_changing_tail() -> None:
    helpers = importlib.import_module("polynexus.core.saxs_engine.saxs_extrapolation_helpers")

    q = np.linspace(0.2, 1.0, 12)
    I = 8.0 * np.exp(-q * 0.5)

    q_full, I_full = helpers._extrapolate_guinier(q, I, dq=q[1] - q[0], n_extra=6)

    assert len(q_full) > len(q)
    assert np.allclose(q_full[-len(q) :], q)
    assert np.allclose(I_full[-len(I) :], I)
    assert q_full[0] == 0.0
    assert np.all(np.diff(q_full) >= 0.0)


def test_extrapolate_porod_appends_tail_with_boundary_match() -> None:
    helpers = importlib.import_module("polynexus.core.saxs_engine.saxs_extrapolation_helpers")

    q = np.linspace(0.2, 1.0, 18)
    Kp = 2.5
    I = Kp / q**4

    q_full, I_full = helpers._extrapolate_porod(q, I, dq=q[1] - q[0], n_extra=8)

    assert len(q_full) > len(q)
    assert np.allclose(q_full[: len(q)], q)
    assert np.allclose(I_full[: len(I)], I)
    assert q_full[-1] > q[-1]
    assert I_full[-1] < I_full[len(I) - 1]


def test_core_reuses_extrapolation_helper_functions() -> None:
    helpers = importlib.import_module("polynexus.core.saxs_engine.saxs_extrapolation_helpers")
    core = importlib.import_module("polynexus.core.saxs_engine.core")

    assert core._extrapolate_guinier is helpers._extrapolate_guinier
    assert core._extrapolate_porod is helpers._extrapolate_porod
