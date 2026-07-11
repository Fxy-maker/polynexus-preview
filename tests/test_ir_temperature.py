from pathlib import Path

import numpy as np
import pytest

from polynexus.core.ir_engine import (
    IRConfig,
    analyze_temperature_2d_series,
    detect_temperature_2d,
    load_project,
    preprocess_pipeline,
)
from polynexus.core.ir_engine.ir_temperature import (
    generate_temperature_2d_figures,
)


def _temperature_ir_dir() -> Path:
    path = (
        Path(__file__).resolve().parents[1]
        / "测试数据"
        / "IR"
        / "原位变温红外"
    )
    if not path.is_dir():
        pytest.skip("external IR temperature-series fixture is unavailable")
    return path


def test_temperature_2d_detector_recognizes_real_sequence():
    assert detect_temperature_2d(str(_temperature_ir_dir())) == "ir.temperature_2d"


def test_temperature_2d_series_builds_matrix_2dcos_and_exports(tmp_path):
    cfg = IRConfig(
        peak_height_min=0.03,
        peak_prominence_min=0.02,
        peak_distance=18.0,
        polymer_name="PA6",
    )
    spectra = load_project(str(_temperature_ir_dir()), cfg.wavenumber_range)
    processed = [preprocess_pipeline(s, cfg) for s in spectra]

    result = analyze_temperature_2d_series(processed, cfg)

    assert len(result.frames) >= 40
    assert result.absorbance_matrix.shape == (len(result.frames), len(result.wavenumber))
    assert result.sync_corr.shape == (len(result.wavenumber), len(result.wavenumber))
    assert result.async_corr.shape == (len(result.wavenumber), len(result.wavenumber))
    assert result.frames[0].stage == "heating"
    assert result.frames[0].temperature_C == 30
    assert any(f.stage == "hold" and f.time_min == 1 for f in result.frames)
    assert result.frames[-1].stage == "cooling"
    assert result.frames[-1].temperature_C == 30
    assert "PA6_A1200_A1637" in result.band_indices_vs_frame
    assert np.isfinite(result.band_indices_vs_frame["PA6_A1200_A1637"]).sum() >= 10
    assert result.sync_cross_peaks
    assert result.async_cross_peaks

    figures = generate_temperature_2d_figures(result, str(tmp_path), cfg)

    assert "temperature_heatmap" in figures
    assert "temperature_2dcos_sync" in figures
    assert "temperature_2dcos_async" in figures
    for path in figures.values():
        assert Path(path).exists()
    assert (tmp_path / "data" / "ir_temperature_parameters.csv").exists()
    assert (tmp_path / "data" / "ir_temperature_matrix.csv").exists()
    assert (tmp_path / "data" / "ir_temperature_2dcos_cross_peaks.csv").exists()


def test_temperature_2d_real_sequence_freezes_current_baseline_shape_and_risks():
    cfg = IRConfig(
        peak_height_min=0.03,
        peak_prominence_min=0.02,
        peak_distance=18.0,
        polymer_name="PA6",
    )
    spectra = load_project(str(_temperature_ir_dir()), cfg.wavenumber_range)
    processed = [preprocess_pipeline(s, cfg) for s in spectra]

    result = analyze_temperature_2d_series(processed, cfg)

    stage_counts = {}
    for frame in result.frames:
        stage_counts[frame.stage] = stage_counts.get(frame.stage, 0) + 1

    assert len(result.frames) == 48
    assert stage_counts == {"heating": 23, "hold": 3, "cooling": 22}
    assert result.absorbance_matrix.shape == (48, len(result.wavenumber))
    assert result.dynamic_matrix.shape == (48, len(result.wavenumber))
    assert result.sync_corr.shape == (len(result.wavenumber), len(result.wavenumber))
    assert result.async_corr.shape == (len(result.wavenumber), len(result.wavenumber))
    assert result.neg_fraction > 0.30
    assert result.neg_fraction < 0.40
    assert result.parameters["T_range_C"] == "30-250"
    assert result.parameters["n_transitions"] == 1
    assert result.parameters["transition_temperatures_C"] == "140"
    assert result.parameters["band_index_series_count"] == 3
    assert result.parameters["band_index_transition_support_band_count"] >= 2
    assert result.parameters["band_index_transition_reproducible"] is True
    assert result.parameters["band_index_transition_single_frame_only"] is False
    assert result.parameters["band_tracking_missing_key_band"] is False
    assert result.parameters["band_index_transition_consensus_frame"] == 11
    assert result.sync_cross_peaks
    assert result.async_cross_peaks
