import numpy as np

from polynexus.core.dsc_engine.config import DSCConfig
from polynexus.core.dsc_engine.core import analyze_scan
from polynexus.core.dsc_engine.io import DSCScan, split_scan_segments


def _gaussian(x, mu, sigma, amp):
    return amp * np.exp(-0.5 * ((x - mu) / sigma) ** 2)


def test_split_scan_segments_separates_heat_cool_heat_program():
    t1 = np.linspace(50.0, 260.0, 220)
    t2 = np.linspace(260.0, 80.0, 200)
    t3 = np.linspace(80.0, 240.0, 180)
    T = np.concatenate([t1, t2, t3])
    HF = np.zeros_like(T)
    scan = DSCScan(
        label="program",
        T_C=T,
        HF_mW=HF,
        HF_Wg=HF,
        t_min=np.arange(len(T), dtype=float) / 60.0,
    )

    segments = split_scan_segments(scan, min_points=30, min_delta_T=5.0)

    assert len(segments) == 3
    assert segments[0].label.startswith("program/heat")
    assert segments[1].label.startswith("program/cool")
    assert segments[2].label.startswith("program/heat")
    assert segments[0].rate_K_per_min > 0
    assert segments[1].rate_K_per_min < 0
    assert segments[2].rate_K_per_min > 0


def test_analyze_heating_assigns_melting_and_cold_crystallisation():
    T = np.linspace(50.0, 260.0, 1600)
    HF = (
        _gaussian(T, 125.0, 5.0, 0.8)
        - _gaussian(T, 221.0, 6.0, 2.4)
    )

    result = analyze_scan(T, HF, DSCConfig(), label="heating", DHm0_override=230.0)

    assert result.technique == "heating"
    assert abs(result.Tm_peak_C - 221.0) < 1.5
    assert abs(result.Tcc_peak_C - 125.0) < 1.5
    assert result.DHm_Jg > result.DHcc_Jg > 0
    assert 0 < result.Xc_pct < 25


def test_analyze_heating_exports_xc_reliability_inputs():
    T = np.linspace(50.0, 260.0, 1600)
    HF = (
        _gaussian(T, 125.0, 5.0, 0.8)
        - _gaussian(T, 221.0, 6.0, 2.4)
    )

    result = analyze_scan(T, HF, DSCConfig(), label="heating", DHm0_override=230.0)
    params = result.parameters

    assert params["DHm0_source"] == "polymer_reference"
    assert params["baseline_sensitivity_pct"] >= 0.0
    assert params["integration_boundary_sensitivity_pct"] >= 0.0


def test_analyze_cooling_reports_positive_crystallisation_enthalpy():
    T = np.linspace(260.0, 80.0, 1400)
    HF = _gaussian(T, 170.0, 7.0, 1.8)

    result = analyze_scan(T, HF, DSCConfig(), label="cooling", DHm0_override=230.0)

    assert result.technique == "cooling"
    assert abs(result.Tc_peak_C - 170.0) < 1.5
    assert result.DHc_Jg > 0
    assert np.isnan(result.Tm_peak_C)


def test_dsc_engine_validation_records_range_warnings() -> None:
    from polynexus.core.dsc import DSCEngine
    from polynexus.core.dsc_engine.core import DSCResult

    engine = DSCEngine()
    engine._results = [DSCResult(label="scan1", Tg_C=400.0, Tm_peak_C=220.0, Xc_pct=0.0, DHm_Jg=600.0)]

    ok = engine._validate_results()

    assert ok is True
    assert engine.result.quality_flags["scan1/Tg"] == "WARN"
    assert engine.result.quality_flags["scan1/DHm"] == "WARN"
    assert engine.result.quality_flags["scan1/validation"] == "WARN"
    assert engine.result.validation_warnings


def test_dsc_engine_validation_summary_is_exported_in_parameters() -> None:
    from polynexus.core.dsc import DSCEngine
    from polynexus.core.dsc_engine.core import DSCResult

    engine = DSCEngine()
    engine._results = [DSCResult(label="scan1", Tg_C=400.0, Tm_peak_C=220.0, Xc_pct=0.0, DHm_Jg=600.0)]

    engine._validate_results()
    params = engine.get_parameters()

    assert params["validation_summary"].startswith("WARN:")
    assert "scan1/Tg" in params["quality_flags"]
    assert "scan1/DHm" in params["quality_flags"]
    assert "scan1/validation" in params["validation_warnings"]
