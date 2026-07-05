import numpy as np

from polynexus.core.dsc_engine.dsc_kinetics import (
    analyze_nonisothermal_scans,
    extract_nonisothermal_rate,
    relative_crystallinity_nonisothermal,
)
from polynexus.core.dsc_engine.io import DSCScan


def _cooling_scan(beta, peak_C):
    T = np.linspace(225.0, 25.0, 1600)
    t = (T[0] - T) / beta
    sigma = 11.0
    HF = 0.015 + 1.3 * np.exp(-0.5 * ((T - peak_C) / sigma) ** 2)
    label_beta = f"{beta:g}"
    return DSCScan(
        label=f"FDW-SLM-80%-30-{label_beta}.xls/cool 225-25C",
        T_C=T,
        HF_mW=HF,
        HF_Wg=HF,
        t_min=t,
        rate_K_per_min=-beta,
        metadata={"segment_kind": "cool"},
    )


def test_extract_nonisothermal_rate_uses_filename_suffix():
    assert extract_nonisothermal_rate("FDW-SLM-80%-30-2.5.xls/cool") == 2.5
    assert extract_nonisothermal_rate("FDW-SLM-80%-30-40.xls") == 40.0


def test_relative_crystallinity_nonisothermal_is_monotonic():
    scan = _cooling_scan(10.0, 152.0)

    Xt, T_xt, t_xt, meta = relative_crystallinity_nonisothermal(
        scan.T_C, scan.HF_Wg, 10.0, time_min=scan.t_min
    )

    assert len(Xt) > 50
    assert len(Xt) == len(T_xt) == len(t_xt)
    assert np.nanmin(Xt) >= 0.0
    assert np.nanmax(Xt) <= 1.0
    assert np.all(np.diff(Xt) >= -1e-9)
    assert abs(meta["Tp_C"] - 152.0) < 1.0
    assert meta["crystallisation_enthalpy_Jg"] > 0


def test_analyze_nonisothermal_scans_fits_rate_series():
    rates = [2.5, 5.0, 10.0, 20.0, 40.0]
    scans = [
        _cooling_scan(beta, peak_C=160.0 - 4.0 * np.log2(beta / 2.5))
        for beta in rates
    ]

    series = analyze_nonisothermal_scans(scans)

    assert len(series.curves) == 5
    assert [c.rate_K_per_min for c in series.curves] == rates
    assert np.isfinite(series.kissinger.kissinger_Ea_kJmol)
    assert np.isfinite(series.mo.mo_a)
    assert series.friedman.friedman_Ea
