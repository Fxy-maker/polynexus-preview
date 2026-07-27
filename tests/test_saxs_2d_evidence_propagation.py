from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np

from polynexus.core.saxs_batch_helpers import (
    build_static_batch_2d_quality_evidence,
    copy_saxs_quality_evidence,
)
from polynexus.core.saxs import SAXSEngine
from polynexus.core.engine import AnalysisResult
from polynexus.core.saxs_export_bundle import export_saxs_bundle
from polynexus.core.saxs_engine.core import SAXSResult, StructureParams
from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.saxs_strain import (
    StrainPointResult,
    StrainSeriesResult,
    analyze_strain_series,
)
from polynexus.core.saxs_engine.saxs_temperature import (
    TempSeriesResult,
    TemperaturePointResult,
    analyze_temperature_series,
)
from polynexus.data.sample_db import SampleDB
from polynexus.gui.analysis_run_service import AnalysisRunPersistenceContext, persist_analysis_run
from polynexus.gui.saxs_results_table_service import build_saxs_results_presentation


def _detector(frame_id: str, *, level: str = "Trend") -> dict:
    return {
        "metric_name": "DetectorQuality",
        "level": level,
        "source_kind": "sector_map",
        "source_id": frame_id,
        "reason_codes": [] if level == "Trend" else ["detector_quality_diagnostic"],
    }


def _orientation(frame_id: str, *, level: str = "Trend") -> dict:
    return {
        "metric_name": "Orientation",
        "level": level,
        "applicable": level == "Trend",
        "fit_evidence": {"f_herman": 0.42},
        "source_ref": frame_id,
        "reason_codes": [] if level == "Trend" else ["orientation_applicability_unsupported"],
    }


def _fake_saxs_result(frame_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        long_period=SimpleNamespace(L_best=10.0, L_confidence=0.8, method_used="bragg"),
        structure=SimpleNamespace(L=10.0, lc=3.0, la=7.0, phi_c=0.3, confidence_lc=0.8),
        data_quality_report={"level": "Trend", "source_id": frame_id},
        metric_evidence={"porod": {"level": "Trend", "source": frame_id}},
        detector_quality_report=_detector(frame_id),
        orientation_evidence=_orientation(frame_id),
    )


def test_copy_saxs_quality_evidence_deep_copies_existing_2d_fields():
    source = SimpleNamespace(
        detector_quality_report={"level": "Trend", "nested": {"source": "sector_map"}},
        orientation_evidence={"level": "Trend", "fit_evidence": {"f_herman": 0.4}},
    )

    copied = copy_saxs_quality_evidence(source)

    assert copied["detector_quality_report"] == source.detector_quality_report
    assert copied["orientation_evidence"] == source.orientation_evidence
    assert copied["detector_quality_report"] is not source.detector_quality_report
    assert copied["orientation_evidence"]["fit_evidence"] is not source.orientation_evidence["fit_evidence"]


def test_static_batch_2d_summary_preserves_partial_coverage_and_separate_orientation():
    analyses = [
        _fake_saxs_result("frame-0"),
        SimpleNamespace(),
        SimpleNamespace(
            detector_quality_report=_detector("frame-2", level="Diagnostic"),
            orientation_evidence=_orientation("frame-2", level="Diagnostic"),
        ),
    ]

    summary = build_static_batch_2d_quality_evidence(analyses)

    detector = summary["detector_quality_report"]
    orientation = summary["orientation_evidence"]
    assert detector["frame_count"] == 3
    assert detector["evidence_frame_count"] == 2
    assert detector["missing_frame_count"] == 1
    assert detector["level"] == "Diagnostic"
    assert detector["source_kinds"] == ["sector_map"]
    assert orientation["metric_name"] == "Orientation"
    assert orientation["missing_frame_count"] == 1
    assert orientation["level"] == "Diagnostic"
    assert "series_metric_missing_frames" in orientation["reason_codes"]


def test_static_batch_2d_summary_is_absent_when_no_2d_evidence_is_supplied():
    assert build_static_batch_2d_quality_evidence([SimpleNamespace(), None]) == {}


def test_temperature_points_and_summary_propagate_2d_evidence(monkeypatch):
    import polynexus.core.saxs_engine.saxs_temperature as module

    q = np.linspace(0.02, 0.6, 24)
    intensity = 120.0 * np.exp(-q**2 * 4.0**2 / 3.0)
    calls = {"count": 0}

    def fake_analyze(q_arr, i_arr, cfg):
        calls["count"] += 1
        return _fake_saxs_result(f"temperature-{calls['count']}")

    monkeypatch.setattr(module, "analyze_single", fake_analyze)
    monkeypatch.setattr(module, "scattering_invariant", lambda *args, **kwargs: 1.0)
    monkeypatch.setattr(module, "bragg_long_period", lambda *args, **kwargs: (10.0, 0.628, {}))

    result = analyze_temperature_series(
        [170.0, 180.0], [q, q], [intensity, intensity], cfg=SAXSConfig()
    )

    assert result.temp_points[0].detector_quality_report["source_id"] == "temperature-1"
    assert result.temp_points[1].orientation_evidence["source_ref"] == "temperature-2"
    assert result.detector_quality_report["evidence_frame_count"] == 2
    assert result.orientation_evidence["metric_name"] == "Orientation"


def test_strain_points_and_summary_propagate_2d_evidence(monkeypatch):
    import polynexus.core.saxs_engine.saxs_strain as module

    q = np.linspace(0.02, 0.6, 24)
    intensity = 120.0 * np.exp(-q**2 * 4.0**2 / 3.0)
    calls = {"count": 0}

    def fake_analyze(q_arr, i_arr, cfg):
        calls["count"] += 1
        return _fake_saxs_result(f"strain-{calls['count']}")

    monkeypatch.setattr(module, "analyze_single", fake_analyze)
    monkeypatch.setattr(module, "scattering_invariant", lambda *args, **kwargs: 1.0)
    monkeypatch.setattr(module, "bragg_long_period", lambda *args, **kwargs: (10.0, 0.628, {}))

    result = analyze_strain_series(
        [0.0, 10.0], [q, q], [intensity, intensity], cfg=SAXSConfig()
    )

    assert result.strain_points[0].detector_quality_report["source_id"] == "strain-1"
    assert result.strain_points[1].orientation_evidence["source_ref"] == "strain-2"
    assert result.detector_quality_report["evidence_frame_count"] == 2
    assert result.orientation_evidence["metric_name"] == "Orientation"
    json.dumps(result.detector_quality_report, allow_nan=False)
    json.dumps(result.orientation_evidence, allow_nan=False)


def test_temperature_parameters_align_2d_frame_evidence_by_source_index():
    engine = SAXSEngine(SAXSConfig())
    series = TempSeriesResult(
        temperatures=np.array([170.0, 180.0]),
        temp_points=[
            TemperaturePointResult(
                source_index=1,
                temperature_C=180.0,
                detector_quality_report=_detector("original-180"),
                orientation_evidence=_orientation("original-180"),
            ),
            TemperaturePointResult(
                source_index=0,
                temperature_C=170.0,
                detector_quality_report=_detector("original-170"),
                orientation_evidence=_orientation("original-170"),
            ),
        ],
        detector_quality_report={"metric_name": "DetectorQuality", "level": "Trend"},
        orientation_evidence={"metric_name": "Orientation", "level": "Trend"},
    )
    engine._temperature_result = series
    engine._batch_params = [
        {"temperature_C": 170.0, "L_nm": 12.0},
        {"temperature_C": 180.0, "L_nm": 12.2},
    ]

    params = engine.get_parameters()

    assert params["detector_quality_report"]["metric_name"] == "DetectorQuality"
    assert params["_batch_data"][0]["detector_quality_report"]["source_id"] == "original-170"
    assert params["_batch_data"][1]["orientation_evidence"]["source_ref"] == "original-180"


def test_strain_parameters_transport_point_2d_evidence():
    engine = SAXSEngine(SAXSConfig())
    series = StrainSeriesResult(
        strains=np.array([0.0, 10.0]),
        L_array=np.array([12.0, 12.2]),
        Q_star_array=np.array([1.0, 1.1]),
        Q_star_rel_array=np.array([1.0, 1.1]),
        phi_void_array=np.array([0.0, 0.0]),
        f_herman_array=np.array([0.1, 0.2]),
        strain_points=[
            StrainPointResult(
                strain_pct=0.0,
                detector_quality_report=_detector("strain-0"),
                orientation_evidence=_orientation("strain-0"),
            ),
            StrainPointResult(
                strain_pct=10.0,
                detector_quality_report=_detector("strain-10"),
                orientation_evidence=_orientation("strain-10"),
            ),
        ],
        detector_quality_report={"metric_name": "DetectorQuality", "level": "Trend"},
        orientation_evidence={"metric_name": "Orientation", "level": "Trend"},
    )
    engine._strain_result = series
    engine._batch_params = [
        {"strain_pct": 0.0, "L_nm": 12.0},
        {"strain_pct": 10.0, "L_nm": 12.2},
    ]

    params = engine.get_parameters()

    assert params["_batch_data"][0]["orientation_evidence"]["source_ref"] == "strain-0"
    assert params["_batch_data"][1]["detector_quality_report"]["source_id"] == "strain-10"


def test_static_batch_parameters_include_separate_2d_summaries_and_frame_fields():
    engine = SAXSEngine(SAXSConfig())
    first = SAXSResult(
        structure=StructureParams(L=12.0),
        detector_quality_report=_detector("static-0"),
        orientation_evidence=_orientation("static-0"),
    )
    third = SAXSResult(
        structure=StructureParams(L=13.0),
        detector_quality_report=_detector("static-2", level="Diagnostic"),
        orientation_evidence=_orientation("static-2", level="Diagnostic"),
    )
    engine._batch_results = [first, None, third]
    engine._batch_params = [
        {"file": "frame-0.dat", "L_nm": 12.0},
        {"file": "frame-1.dat", "L_nm": None},
        {"file": "frame-2.dat", "L_nm": 13.0},
    ]

    params = engine.get_parameters()

    assert params["detector_quality_report"]["missing_frame_count"] == 1
    assert params["orientation_evidence"]["metric_name"] == "Orientation"
    assert params["_batch_data"][0]["detector_quality_report"]["source_id"] == "static-0"
    assert "detector_quality_report" not in params["_batch_data"][1]


def test_workbench_keeps_2d_evidence_in_diagnostics_only():
    params = {
        "batch_frames": 2,
        "_batch_data": [
            {"temperature_C": 170.0, "detector_quality_report": _detector("frame-0")},
            {"temperature_C": 180.0, "orientation_evidence": _orientation("frame-1")},
        ],
        "detector_quality_report": {"metric_name": "DetectorQuality", "level": "Diagnostic"},
        "orientation_evidence": {"metric_name": "Orientation", "level": "Diagnostic"},
        "metric_evidence": {},
    }

    presentation = build_saxs_results_presentation(
        params,
        submodule="saxs.temperature",
        language="en",
    )
    diagnostic_text = " ".join(
        cell.display
        for row in presentation.diagnostics.rows
        for cell in row
    )

    assert "sector_map" in diagnostic_text
    assert "Orientation" in diagnostic_text
    assert "Orientation" not in (presentation.risk_text + presentation.next_text)


def test_history_keeps_mode_and_frame_2d_evidence(tmp_path):
    db = SampleDB(tmp_path / "samples.db")
    data_file = tmp_path / "temperature.csv"
    data_file.write_text("temperature_C,L_nm\n170,12\n", encoding="utf-8")
    params = {
        "batch_frames": 2,
        "_batch_data": [
            {"temperature_C": 170.0, "detector_quality_report": _detector("frame-0")},
            {"temperature_C": 180.0, "orientation_evidence": _orientation("frame-1")},
        ],
        "detector_quality_report": {"metric_name": "DetectorQuality", "level": "Diagnostic"},
        "orientation_evidence": {"metric_name": "Orientation", "level": "Diagnostic"},
    }
    context = AnalysisRunPersistenceContext(
        technique="saxs",
        submodule="saxs.temperature",
        data_file=str(data_file),
        output_dir=str(tmp_path / "output"),
        project_label="PA6",
    )

    run_id = persist_analysis_run(db, {"technique": "saxs", "parameters": params}, context)

    run = db.get_analysis_run(run_id)
    assert run["parameters"]["_batch_data"][0]["detector_quality_report"]["source_id"] == "frame-0"
    assert run["results_summary"]["result"]["parameters"]["orientation_evidence"]["metric_name"] == "Orientation"
    db.close()


def test_static_batch_export_keeps_2d_summary_and_strict_json(tmp_path):
    result = AnalysisResult(
        technique="saxs",
        parameters={},
        raw_data={"q": np.array([0.1]), "I": np.array([1.0])},
    )
    engine = SimpleNamespace(
        result=result,
        cfg=SAXSConfig(),
        _analysis=None,
        _batch_results=[
            SimpleNamespace(
                detector_quality_report=_detector("frame-0"),
                orientation_evidence=_orientation("frame-0"),
            ),
            None,
        ],
        _temperature_result=None,
        _strain_result=None,
        _q_list=[],
        _I_list=[],
        _processed_list=[],
        _file_list=[],
    )

    bundle = export_saxs_bundle(engine, str(tmp_path / "bundle"))

    payload_path = tmp_path / "bundle" / "quality_evidence.json"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    assert bundle.status == "ok"
    assert payload["static"]["detector_quality_report"]["missing_frame_count"] == 1
    assert payload["static"]["orientation_evidence"]["metric_name"] == "Orientation"
    text = payload_path.read_text(encoding="utf-8")
    assert "NaN" not in text
    assert "Infinity" not in text
