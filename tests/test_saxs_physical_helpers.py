from __future__ import annotations

import importlib

import numpy as np
import pytest

from polynexus.core.saxs_engine.config import SAXSConfig


def test_tangent_lc_returns_finite_value_for_reasonable_gamma_profile() -> None:
    helpers = importlib.import_module("polynexus.core.saxs_engine.saxs_physical_helpers")

    r = np.arange(0.0, 15.0, 1.0)
    gamma = np.array([1.0, 0.95, 0.9, 0.85, 0.8, 0.4, 0.2, 0.05, -0.1, -0.2, -0.15, -0.1, -0.05, -0.02, 0.0])
    cfg = SAXSConfig(tangent_lc_min_nm=2.0, idf_first_peak_is_la=False)

    lc = helpers._tangent_lc({"r": r, "gamma": gamma}, L=12.0, cfg=cfg)

    assert np.isfinite(lc)
    assert 0.0 < lc < 12.0 * 0.7


def test_crystallinity_invariant_recovers_expected_fraction() -> None:
    helpers = importlib.import_module("polynexus.core.saxs_engine.saxs_physical_helpers")

    phi_c = 0.35
    L = 10.0
    Kp = 2.5
    Q_invariant = 4.0 * np.pi**4 * Kp * L * phi_c * (1.0 - phi_c)

    recovered = helpers._crystallinity_invariant(L, Q_invariant, Kp)

    assert recovered == pytest.approx(phi_c, rel=1e-6)


def test_porod_constant_prefers_raw_data_plateau() -> None:
    helpers = importlib.import_module("polynexus.core.saxs_engine.saxs_physical_helpers")

    q = np.linspace(0.2, 0.6, 24)
    Kp = 1.8
    intensity = Kp / q**4

    recovered = helpers._porod_constant(q, intensity)

    assert recovered == pytest.approx(Kp, rel=1e-6)


def test_guinier_analysis_estimates_radius_of_gyration() -> None:
    helpers = importlib.import_module("polynexus.core.saxs_engine.saxs_physical_helpers")

    q = np.linspace(0.02, 0.18, 60)
    rg = 4.5
    intensity = 120.0 * np.exp(-(q**2) * rg**2 / 3.0)

    recovered_rg, i0, q_sel, lnI = helpers.guinier_analysis(q, intensity)

    assert recovered_rg == pytest.approx(rg, rel=0.05)
    assert i0 > 0
    assert len(q_sel) == len(lnI) > 0


def test_core_reuses_saxs_physical_helper_functions() -> None:
    helpers = importlib.import_module("polynexus.core.saxs_engine.saxs_physical_helpers")
    core = importlib.import_module("polynexus.core.saxs_engine.core")

    assert core._tangent_lc is helpers._tangent_lc
    assert core._crystallinity_invariant is helpers._crystallinity_invariant
    assert core._porod_constant is helpers._porod_constant
    assert core.guinier_analysis is helpers.guinier_analysis
    assert core.porod_analysis is helpers.porod_analysis
