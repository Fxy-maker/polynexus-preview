import numpy as np

from polynexus.core.dsc import DSCEngine
from polynexus.core.dsc_engine.core import DSCResult
from polynexus.core.dsc_engine.dsc_kinetics import (
    AvramiResult,
    analyze_isothermal_scans,
    avrami_from_dsc,
    detect_isothermal_segments,
)
from polynexus.core.dsc_engine.io import DSCScan


def _avrami_heat_flow(t, n=3.0, k=0.025, scale=1.0, baseline=0.02):
    tt = np.maximum(t, 1e-9)
    dXdt = n * k * tt ** (n - 1) * np.exp(-k * tt ** n)
    return baseline + scale * dXdt


def test_avrami_from_dsc_recovers_synthetic_parameters():
    t = np.linspace(0.0, 30.0, 1500)
    HF = _avrami_heat_flow(t, n=3.0, k=0.025)

    result = avrami_from_dsc(t, HF)

    assert abs(result.n - 3.0) < 0.08
    assert abs(result.k - 0.025) < 0.003
    assert result.r_squared > 0.999
    assert result.crystallisation_enthalpy_Jg > 0


def test_detect_isothermal_hold_inside_cooling_scan():
    t_ramp = np.linspace(0.0, 6.0, 300)
    T_ramp = np.linspace(255.0, 180.0, len(t_ramp))
    t_hold = np.linspace(6.02, 18.0, 700)
    T_hold = np.full_like(t_hold, 180.05)
    T = np.concatenate([T_ramp, T_hold])
    t = np.concatenate([t_ramp, t_hold])
    HF = np.concatenate([
        np.zeros_like(t_ramp),
        _avrami_heat_flow(t_hold - t_hold[0], n=2.2, k=0.08, scale=1.5),
    ])
    scan = DSCScan(
        label="cooling_program",
        T_C=T,
        HF_Wg=HF,
        HF_mW=HF,
        t_min=t,
        rate_K_per_min=-10.0,
    )

    segments = detect_isothermal_segments(scan)

    assert len(segments) == 1
    assert abs(segments[0].temperature_C - 180.05) < 0.1
    assert segments[0].duration_min > 10


def test_analyze_isothermal_scans_uses_cooling_holds():
    hold_t = np.linspace(0.0, 12.0, 900)
    heat_scan = DSCScan(
        label="program/heat 80-255C",
        T_C=np.full_like(hold_t, 255.0),
        HF_Wg=np.full_like(hold_t, 0.01),
        HF_mW=np.full_like(hold_t, 0.01),
        t_min=hold_t,
        rate_K_per_min=10.0,
    )
    cool_scan = DSCScan(
        label="program/cool 255-180C",
        T_C=np.full_like(hold_t, 180.0),
        HF_Wg=_avrami_heat_flow(hold_t, n=2.0, k=0.12, scale=1.2),
        HF_mW=_avrami_heat_flow(hold_t, n=2.0, k=0.12, scale=1.2),
        t_min=hold_t,
        rate_K_per_min=-10.0,
    )

    result = analyze_isothermal_scans([heat_scan, cool_scan])

    assert len(result.avrami_results) == 1
    assert abs(result.best.temperature_C - 180.0) < 0.1
    assert abs(result.best.n - 2.0) < 0.1


def test_dsc_isothermal_parameters_show_avrami_rows_first():
    engine = DSCEngine()
    engine.active_submodule = "dsc.isothermal"
    engine._results = [DSCResult(label="standard_scan")]
    av = AvramiResult(
        n=2.5,
        k=0.03,
        log_k=-1.52,
        t_half_min=3.4,
        temperature_C=183.0,
        crystallisation_enthalpy_Jg=120.0,
        r_squared=0.99,
        label="program/cool/iso 183C",
    )
    engine._kinetics_data = {"avrami": av, "avrami_series": [av]}

    params = engine.get_parameters()

    assert list(params)[0] == "best_avrami"
    assert params["best_avrami"]["Avrami_n"] == 2.5
    assert params["best_avrami"]["Avrami_k"] == 0.03
    assert params["best_avrami"]["Avrami_R2"] == 0.99
