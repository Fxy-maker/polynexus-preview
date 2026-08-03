from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from polynexus.core.saxs import SAXSEngine
from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.core import (
    LongPeriodResult,
    SAXSResult,
    StructureParams,
    analyze_single,
)
from polynexus.core.saxs_engine.saxs_quality_contracts import (
    build_data_quality_report,
    build_guinier_evidence,
)
from polynexus.core.saxs_engine.saxs_strain import analyze_strain_series
from polynexus.core.saxs_engine.saxs_temperature import analyze_temperature_series


def _profile() -> tuple[np.ndarray, np.ndarray]:
    q = np.linspace(0.02, 1.8, 80)
    intensity = 180.0 * np.exp(-(q**2) * 2.2) + 8.0
    return q, intensity


def _fake_frame_result(q: np.ndarray, intensity: np.ndarray, **source: str) -> SimpleNamespace:
    quality = build_data_quality_report(
        q,
        intensity,
        source_id=source.get("source_id", ""),
        raw_data_ref=source.get("raw_data_ref", ""),
    )
    evidence = build_guinier_evidence(
        q[:12],
        np.log(intensity[:12]),
        rg_nm=4.0,
        i0=float(intensity[0]),
        quality_report=quality,
        applicability="supported",
    )
    return SimpleNamespace(
        long_period=LongPeriodResult(L_best=10.0, L_confidence=0.8, method_used="bragg"),
        structure=StructureParams(L=10.0, lc=3.0, la=7.0, phi_c=0.3, confidence_lc=0.8),
        guinier_evidence=evidence.to_dict(),
        data_quality_report=quality.to_dict(),
        metric_evidence={},
    )


def test_analyze_single_binds_explicit_source_provenance():
    q, intensity = _profile()
    q[10] = np.nan
    intensity[11] = -1.0

    result = analyze_single(
        q,
        intensity,
        SAXSConfig(savgol_window=5, savgol_order=2),
        source_id="frame-4",
        raw_data_ref="raw/frame-4.edf",
    )

    assert result.data_quality_report["source_id"] == "frame-4"
    assert result.data_quality_report["raw_data_ref"] == "raw/frame-4.edf"
    assert "invalid_pairs_dropped" in result.data_quality_report["actions"]


def test_temperature_binds_sources_by_original_index_after_sort(monkeypatch):
    import polynexus.core.saxs_engine.saxs_temperature as module

    q, intensity = _profile()
    calls: list[dict[str, str]] = []

    def fake_analyze(q_arr, i_arr, cfg, **kwargs):
        calls.append(dict(kwargs))
        return _fake_frame_result(q_arr, i_arr, **kwargs)

    monkeypatch.setattr(module, "analyze_single", fake_analyze)
    monkeypatch.setattr(module, "scattering_invariant", lambda *args, **kwargs: 1.0)
    monkeypatch.setattr(module, "bragg_long_period", lambda *args, **kwargs: (10.0, 0.628, {}))

    result = analyze_temperature_series(
        [180.0, 170.0],
        [q, q],
        [intensity, intensity],
        cfg=SAXSConfig(),
        source_ids=["frame-0", "frame-1"],
        raw_data_refs=["raw/frame-0.edf", "raw/frame-1.edf"],
    )

    assert [call["source_id"] for call in calls] == ["frame-1", "frame-0"]
    assert [point.source_index for point in result.temp_points] == [1, 0]
    assert [point.data_quality_report["raw_data_ref"] for point in result.temp_points] == [
        "raw/frame-1.edf",
        "raw/frame-0.edf",
    ]


def test_strain_binds_sources_positionally(monkeypatch):
    import polynexus.core.saxs_engine.saxs_strain as module

    q, intensity = _profile()
    calls: list[dict[str, str]] = []

    def fake_analyze(q_arr, i_arr, cfg, **kwargs):
        calls.append(dict(kwargs))
        return _fake_frame_result(q_arr, i_arr, **kwargs)

    monkeypatch.setattr(module, "analyze_single", fake_analyze)
    monkeypatch.setattr(module, "scattering_invariant", lambda *args, **kwargs: 1.0)

    result = analyze_strain_series(
        [0.0, 10.0],
        [q, q],
        [intensity, intensity],
        cfg=SAXSConfig(),
        source_ids=["frame-0", "frame-1"],
        raw_data_refs=["raw/frame-0.edf", "raw/frame-1.edf"],
    )

    assert [call["source_id"] for call in calls] == ["frame-0", "frame-1"]
    assert [point.data_quality_report["source_id"] for point in result.strain_points] == [
        "frame-0",
        "frame-1",
    ]


def test_mismatched_series_sources_remain_unbound(monkeypatch):
    import polynexus.core.saxs_engine.saxs_temperature as module

    q, intensity = _profile()
    calls: list[dict[str, str]] = []

    def fake_analyze(q_arr, i_arr, cfg, **kwargs):
        calls.append(dict(kwargs))
        return _fake_frame_result(q_arr, i_arr, **kwargs)

    monkeypatch.setattr(module, "analyze_single", fake_analyze)
    monkeypatch.setattr(module, "scattering_invariant", lambda *args, **kwargs: 1.0)
    monkeypatch.setattr(module, "bragg_long_period", lambda *args, **kwargs: (10.0, 0.628, {}))

    result = analyze_temperature_series(
        [170.0, 180.0],
        [q, q],
        [intensity, intensity],
        cfg=SAXSConfig(),
        source_ids=["only-one"],
        raw_data_refs=["raw/only-one.edf"],
    )

    assert calls == [{}, {}]
    assert all(point.data_quality_report["source_id"] == "" for point in result.temp_points)
    assert all(point.data_quality_report["raw_data_ref"] == "" for point in result.temp_points)


def test_static_engine_forwards_loaded_file_to_single_frame_report(monkeypatch):
    import polynexus.core.saxs as saxs_module

    q, intensity = _profile()
    captured: dict[str, str] = {}

    def fake_analyze(q_arr, i_arr, cfg, **kwargs):
        captured.update(kwargs)
        return SAXSResult(
            q=q_arr,
            I=i_arr,
            long_period=LongPeriodResult(L_best=10.0),
            structure=StructureParams(L=10.0, lc=3.0, la=7.0, phi_c=0.3),
            data_quality_report=build_data_quality_report(
                q_arr, i_arr, **kwargs
            ).to_dict(),
        )

    monkeypatch.setattr(saxs_module, "analyze_single", fake_analyze)
    engine = SAXSEngine(config=SAXSConfig(experiment_type="static"))
    engine._q = q  # type: ignore[attr-defined]
    engine._I = intensity  # type: ignore[attr-defined]
    engine._file_list = ["C:/data/sample.edf"]  # type: ignore[attr-defined]

    assert engine._run_static_pipeline(has_multi=False) is True  # type: ignore[attr-defined]

    assert captured == {"source_id": "frame-0", "raw_data_ref": "C:/data/sample.edf"}
    assert engine._analysis.data_quality_report["raw_data_ref"] == "C:/data/sample.edf"  # type: ignore[attr-defined]
