from pathlib import Path

import numpy as np

from polynexus.core.ir_engine import (
    IRConfig,
    analyze_spectrum,
    load_spectrum,
    preprocess_pipeline,
)
from polynexus.core.ir_residual_analyzer import IRResidualAnalyzer


def _ordinary_ir_file(name: str) -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "测试数据"
        / "IR"
        / "普通红外"
        / name
    )


def test_thermo_spa_reader_uses_real_axis_and_data_block():
    spec = load_spectrum(str(_ordinary_ir_file("TXT.SPA")))

    assert spec.has_data
    assert len(spec.wavenumber) == 7157
    assert 3990.0 < spec.wavenumber[0] < 4010.0
    assert 540.0 < spec.wavenumber[-1] < 560.0
    assert spec.metadata["format"] == "thermo_spa"
    assert spec.metadata["spa_data_offset"] < 2048
    assert -0.1 < float(np.nanmin(spec.absorbance)) < 0.1
    assert 0.2 < float(np.nanmax(spec.absorbance)) < 2.0


def test_common_ir_analysis_identifies_pa6_bands():
    cfg = IRConfig(
        peak_height_min=0.03,
        peak_prominence_min=0.02,
        peak_distance=18.0,
    )
    spec = load_spectrum(str(_ordinary_ir_file("YL.SPA")))
    processed = preprocess_pipeline(spec, cfg)
    result = analyze_spectrum(processed, cfg, label=spec.label)

    assert result.polymer_name == "PA6"
    assert result.n_peaks >= 8
    assert np.isfinite(result.Xc_pct)
    assert any(abs(p["wavenumber"] - 1637.0) < 12.0 for p in result.peaks)
    assert any(abs(p["wavenumber"] - 1541.0) < 12.0 for p in result.peaks)
    assert any("amide I" in p.get("assignment", "") for p in result.peaks)


def test_real_ir_pa6_yl_sample_keeps_core_peak_and_residual_signals():
    cfg = IRConfig(
        peak_height_min=0.03,
        peak_prominence_min=0.02,
        peak_distance=18.0,
        baseline_method="rubberband",
        smooth_window=7,
        normalization_method="minmax",
        lineshape="lorentzian",
        polymer_name="PA6",
    )
    source_file = (
        Path(__file__).resolve().parents[1]
        / "测试数据"
        / "IR"
        / "普通红外"
        / "YL.SPA"
    )

    spec = load_spectrum(str(source_file))
    processed = preprocess_pipeline(spec, cfg)
    result = analyze_spectrum(processed, cfg, label=spec.label, polymer_name="PA6")
    residual = IRResidualAnalyzer.analyze(result.wavenumber, result.absorbance, result.absorbance_fit)

    peak_positions = [float(peak["wavenumber"]) for peak in result.peaks]

    assert result.polymer_name == "PA6"
    assert result.n_peaks >= 15
    assert np.isfinite(result.r_squared)
    assert result.r_squared > 0.99
    assert np.isfinite(result.Xc_pct)
    assert abs(result.Xc_pct - 13.7) < 1.5
    assert any(abs(value - 3289.0) < 6.0 for value in peak_positions)
    assert any(abs(value - 2916.6) < 6.0 for value in peak_positions)
    assert any(abs(value - 1632.3) < 6.0 for value in peak_positions)
    assert any(abs(value - 1548.4) < 8.0 for value in peak_positions)
    assert residual.residual_type == "crowded_band_underfit"
    assert "peak_fit_window_cm1" in residual.summary
    assert "RMSE=" in residual.summary
