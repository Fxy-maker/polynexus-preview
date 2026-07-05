"""Tests for PolyNexus v4.0 validation and lmfit infrastructure."""

import numpy as np
import pytest

from polynexus.core.lmfit_wrapper import (
    fit_linear, fit_avrami, fit_multi_peak, fit_guinier,
)
from polynexus.core.joint.validation import (
    validate_triple_phi_c, validate_tm_bidirectional,
    validate_L_consistency, CrossValidationResult,
)


# ══════════════════════════════════════════════════════════════════════
#  lmfit linear regression
# ══════════════════════════════════════════════════════════════════════

def test_fit_linear_perfect():
    x = np.linspace(0, 10, 50)
    y = 2.0 * x + 3.0
    result = fit_linear(x, y)
    assert abs(result["slope"] - 2.0) < 0.01
    assert abs(result["intercept"] - 3.0) < 0.1
    assert result["r_squared"] > 0.999


def test_fit_linear_noisy():
    rng = np.random.default_rng(42)
    x = np.linspace(0, 10, 100)
    y = 1.5 * x + 0.5 + rng.normal(0, 0.2, size=100)
    result = fit_linear(x, y)
    assert abs(result["slope"] - 1.5) < 0.1
    assert result["r_squared"] > 0.9


# ══════════════════════════════════════════════════════════════════════
#  lmfit Avrami
# ══════════════════════════════════════════════════════════════════════

def test_fit_avrami_synthetic():
    # Generate synthetic Avrami data: n=3, k=0.01
    t = np.linspace(1, 100, 100)
    n_true, k_true = 3.0, 0.01
    Xc = 1 - np.exp(-k_true * t ** n_true)
    result = fit_avrami(t, Xc)
    assert abs(result["n"] - n_true) < 0.3
    assert result["r_squared"] > 0.99


def test_fit_avrami_too_few_points():
    t = np.array([1.0, 2.0])
    Xc = np.array([0.1, 0.2])
    result = fit_avrami(t, Xc)
    assert np.isnan(result["n"])


# ══════════════════════════════════════════════════════════════════════
#  lmfit multi-peak fitting
# ══════════════════════════════════════════════════════════════════════

def test_fit_multi_peak_single_gaussian():
    x = np.linspace(0, 100, 500)
    center, sigma, amp = 50.0, 5.0, 10.0
    y = amp * np.exp(-0.5 * ((x - center) / sigma) ** 2)
    result = fit_multi_peak(x, y, n_peaks=1, peak_type="gaussian",
                            baseline="none")
    assert len(result["components"]) == 1
    c = result["components"][0]
    assert abs(c["center"] - center) < 1.0
    assert result["r_squared"] > 0.99


def test_fit_multi_peak_double_gaussian():
    x = np.linspace(0, 100, 500)
    y = (10 * np.exp(-0.5 * ((x - 30) / 4) ** 2) +
         8 * np.exp(-0.5 * ((x - 70) / 5) ** 2))
    result = fit_multi_peak(x, y, n_peaks=2, peak_type="gaussian",
                            baseline="constant")
    assert len(result["components"]) == 2
    centers = [c["center"] for c in result["components"]]
    assert any(abs(c - 30) < 3 for c in centers)
    assert any(abs(c - 70) < 3 for c in centers)
    assert result["r_squared"] > 0.95


# ══════════════════════════════════════════════════════════════════════
#  Guinier
# ══════════════════════════════════════════════════════════════════════

def test_fit_guinier_synthetic():
    Rg_true = 10.0  # nm
    I0 = 100.0
    q = np.linspace(0.01, 0.2, 100)
    I = I0 * np.exp(-q**2 * Rg_true**2 / 3)
    result = fit_guinier(q, I)
    assert abs(result["Rg"] - Rg_true) < 2.0
    assert result["r_squared"] > 0.9


# ══════════════════════════════════════════════════════════════════════
#  phi_c triple verification
# ══════════════════════════════════════════════════════════════════════

def test_triple_phi_c_passed():
    results = validate_triple_phi_c(0.60, 0.59, 0.61, sample_id="test")
    assert all(r.passed for r in results)
    assert all(r.severity == "OK" for r in results)


def test_triple_phi_c_failed():
    results = validate_triple_phi_c(0.60, 0.40, 0.62, sample_id="test")
    assert any(r.severity == "ERROR" for r in results)


def test_triple_phi_c_single_available():
    results = validate_triple_phi_c(0.60, None, None)
    assert len(results) == 1
    assert results[0].severity == "WARN"


# ══════════════════════════════════════════════════════════════════════
#  Tm bidirectional
# ══════════════════════════════════════════════════════════════════════

def test_tm_bidirectional():
    results = validate_tm_bidirectional(
        tm_dsc=135.0, L_saxs=30.0, lc_saxs=15.0,
        polymer_family="PE", tolerance=5.0, sample_id="test",
    )
    assert len(results) >= 1
    # With PE, Tm_inf=146, sigma_e=0.093, delta_Hf=293, rho_c=1.0
    # GT should give Tm near the DSC value for reasonable lc


def test_tm_bidirectional_no_data():
    results = validate_tm_bidirectional(None, 30.0, 15.0)
    assert results[0].severity == "WARN"


# ══════════════════════════════════════════════════════════════════════
#  L self-consistency
# ══════════════════════════════════════════════════════════════════════

def test_L_consistency_passed():
    r = validate_L_consistency(25.0, 25.5, sample_id="test")
    assert r.passed
    assert r.severity == "OK"


def test_L_consistency_failed():
    r = validate_L_consistency(25.0, 30.0, sample_id="test")
    assert not r.passed
    assert r.severity == "WARN"
