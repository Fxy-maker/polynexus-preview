from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine import core as saxs_core
from polynexus.core.saxs_engine.core import analyze_single


def test_saxs_peak_region_r_squared_is_distinct_from_quality_score() -> None:
    q = np.linspace(0.05, 2.5, 800)
    baseline = 700.0 * np.exp(-1.1 * q) + 25.0
    lamellar_peak = 180.0 * np.exp(-0.5 * ((q - 0.68) / 0.055) ** 2)
    rng = np.random.default_rng(123)
    intensity = baseline + lamellar_peak + rng.normal(0.0, 1.2, size=q.shape)

    cfg = SAXSConfig(
        q_bragg_min=0.3,
        q_bragg_max=1.1,
        q_corr_min=0.1,
        q_corr_max=2.2,
        savgol_window=7,
        savgol_order=2,
    )

    result = analyze_single(q, intensity, cfg)

    assert result.r_squared_method == "saxs_peak_region_fit_r2"
    assert np.isfinite(result.r_squared)
    assert result.fit_regions
    assert any(region["kind"] == "bragg_peak" for region in result.fit_regions)
    assert result.r_squared != result.quality_score


def test_saxs_savgol_window_three_is_valid() -> None:
    q = np.linspace(0.05, 2.5, 120)
    intensity = 300.0 * np.exp(-q) + 40.0 * np.exp(-0.5 * ((q - 0.7) / 0.04) ** 2)
    cfg = SAXSConfig(savgol_window=3, savgol_order=2, q_bragg_min=0.3, q_bragg_max=1.0)

    result = analyze_single(q, intensity, cfg)

    assert np.isfinite(result.r_squared)


def test_analyze_single_propagates_effective_q_min_to_low_q_sensitive_windows(monkeypatch) -> None:
    q = np.linspace(0.02, 2.5, 240)
    intensity = 180.0 * np.exp(-0.9 * q) + 75.0 * np.exp(-0.5 * ((q - 0.72) / 0.06) ** 2)
    cfg = SAXSConfig(
        q_bragg_min=0.15,
        q_bragg_max=0.9,
        q_corr_min=0.05,
        q_corr_max=2.0,
    )

    captured: dict[str, float] = {}

    monkeypatch.setattr(
        "polynexus.core.saxs_engine.preprocess.smooth_profile",
        lambda q_, I_, cfg_: I_,
    )
    monkeypatch.setattr(
        "polynexus.core.saxs_engine.preprocess.detect_beamstop_edge",
        lambda q_, I_, cfg_: (0.12, True, {}),
    )
    monkeypatch.setattr(
        saxs_core,
        "bragg_long_period",
        lambda q_, I_, q_min, q_max, q_anchor=None: (8.0, 0.72, {"snr": 4.2}),
    )

    def fake_lorentz(q_, I_, cfg_, q_min=None, q_max=None):
        captured["lorentz_q_min"] = float(q_min)
        captured["lorentz_q_max"] = float(q_max)
        return 8.1, 0.88, {"q_peak": 0.78, "q_corr_min": q_min, "q_corr_max": q_max}

    def fake_corr(q_, I_, cfg_, q_min=None, q_max=None, extrapolate_q0=True, extrapolate_qinf=True):
        captured["corr_q_min"] = float(q_min)
        captured["corr_q_max"] = float(q_max)
        return {
            "r": np.array([0.0, 1.0, 2.0, 3.0, 4.0]),
            "gamma": np.array([1.0, 0.7, 0.3, 0.1, 0.0]),
            "Q_invariant": 1.0,
            "L_corr": 7.7,
            "q_corr_min": q_min,
            "q_corr_max": q_max,
        }

    def fake_guinier(q_, I_, q_min=None, q_max_factor=1.3):
        captured["guinier_q_min"] = float(q_min)
        q_sel = q_[q_ >= q_min][:12]
        lnI = np.log(np.clip(np.interp(q_sel, q_, I_), 1e-9, None))
        return 1.2, float(np.exp(lnI[0])), q_sel, lnI

    monkeypatch.setattr(saxs_core, "lorentz_fit_long_period", fake_lorentz)
    monkeypatch.setattr(saxs_core, "correlation_function", fake_corr)
    monkeypatch.setattr(saxs_core, "guinier_analysis", fake_guinier)
    monkeypatch.setattr(
        saxs_core,
        "idf_analysis",
        lambda r, gamma, cfg_, L_estimate=None: {
            "r_idf": np.array([1.0, 2.0, 3.0, 4.0, 5.0]),
            "idf": np.array([0.0, 0.8, 1.2, 0.7, 0.2]),
            "L_idf": 7.9,
            "lc_idf": 3.1,
            "peak_positions": [2.0, 4.0, 6.0],
        },
    )
    monkeypatch.setattr(
        saxs_core,
        "ensemble_long_period",
        lambda **kwargs: SimpleNamespace(
            L_best=8.0,
            L_confidence=0.74,
            L_bragg=kwargs["L_bragg"],
            L_lorentz=kwargs["L_lorentz"],
            L_corr_peak=kwargs["L_corr"],
            L_guinier=np.nan,
            method_used="test",
        ),
    )
    monkeypatch.setattr(
        saxs_core,
        "_saxs_peak_region_fit_quality",
        lambda q_, I_, cfg_, q_bragg_min, q_bragg_max, q_guinier=None, lnI_guinier=None: {
            "r_squared": 0.91,
            "fit_rmse": 0.12,
            "fit_regions": [
                {"kind": "bragg_peak", "q_start": q_bragg_min, "q_end": q_bragg_max},
                {
                    "kind": "guinier",
                    "q_start": float(q_guinier[0]) if q_guinier is not None and len(q_guinier) else np.nan,
                    "q_end": float(q_guinier[-1]) if q_guinier is not None and len(q_guinier) else np.nan,
                },
            ],
            "method": "saxs_peak_region_fit_r2",
        },
    )
    monkeypatch.setattr(
        saxs_core,
        "compute_structure_params",
        lambda corr_result, idf_result, cfg_, L_ensemble=None: SimpleNamespace(
            L=L_ensemble,
            lc=3.0,
            la=5.0,
            phi_c=0.375,
            confidence_lc=0.82,
            Q_invariant=1.0,
            Rg=1.2,
        ),
    )
    monkeypatch.setattr(
        saxs_core,
        "porod_analysis",
        lambda q_, I_, cfg_: {"q_porod": q_[-20:], "Iq4": I_[-20:] * q_[-20:] ** 4, "slope": np.nan, "Kp": np.nan},
    )
    monkeypatch.setattr(
        saxs_core,
        "kratky_analysis",
        lambda q_, I_, cfg_: {"q": q_, "kratky": I_ * q_**2, "kratky_norm": I_ * q_**2, "q_peak_kratky": np.nan},
    )
    monkeypatch.setattr(
        saxs_core,
        "validate_saxs_results",
        lambda result, cfg_, prev_Q_star=None: result,
    )

    result = analyze_single(q, intensity, cfg)

    assert captured["lorentz_q_min"] == pytest.approx(0.12)
    assert captured["corr_q_min"] == pytest.approx(0.12)
    assert captured["guinier_q_min"] == pytest.approx(0.12)
    assert result.correlation["q_corr_min"] == pytest.approx(0.12)
    assert any(region["kind"] == "guinier" and region["q_start"] >= 0.12 for region in result.fit_regions)
