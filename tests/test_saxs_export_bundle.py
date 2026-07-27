from __future__ import annotations

import csv
import copy
import json
from types import SimpleNamespace

import numpy as np

from polynexus.core.engine import AnalysisResult
from polynexus.core.saxs_engine.config import SAXSConfig
import polynexus.core.saxs_export_bundle as export_module
from polynexus.core.saxs_export_bundle import export_saxs_bundle


def _engine() -> SimpleNamespace:
    result = AnalysisResult(
        technique="saxs",
        parameters={"L_nm": 12.4},
        raw_data={
            "q": np.asarray([0.1, 0.2, 0.3]),
            "I": np.asarray([10.0, 8.0, 5.0]),
            "I_smooth": np.asarray([9.5, 7.5, 4.5]),
        },
    )
    return SimpleNamespace(
        result=result,
        cfg=SAXSConfig(q_min=0.12, q_max=2.2),
        _analysis=None,
        _batch_results=[],
        _temperature_result=None,
        _strain_result=None,
        _q_list=[],
        _I_list=[],
        _processed_list=[],
        _file_list=[],
    )


def test_export_saxs_bundle_writes_reproducible_core_artifacts(tmp_path) -> None:
    bundle = export_saxs_bundle(_engine(), str(tmp_path / "bundle"))

    assert bundle.status == "ok"
    root = tmp_path / "bundle"
    assert (root / "bundle_manifest.json").exists()
    assert (root / "analysis_result.json").exists()
    assert (root / "config_snapshot.json").exists()
    assert (root / "provenance.json").exists()
    assert list((root / "data" / "profiles").glob("*.csv"))
    assert json.loads((root / "config_snapshot.json").read_text())["q_min"] == 0.12


def test_export_saxs_bundle_defends_non_mapping_parameter_rows(tmp_path, monkeypatch) -> None:
    engine = _engine()
    engine._analysis = SimpleNamespace(final_parameters={"L_nm": 12.4})
    monkeypatch.setattr(
        export_module,
        "_parameter_payload",
        lambda _engine, mode: {
            "mode": mode, "summary": {}, "rows": [None, {"L_nm": 12.4}],
            "quality_flags": {}, "validation_warnings": [],
        },
    )

    bundle = export_saxs_bundle(engine, str(tmp_path / "mixed_rows"))

    assert bundle.status == "ok"
    with (tmp_path / "mixed_rows" / "data" / "parameters.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        assert list(csv.DictReader(handle)) == [{"L_nm": ""}, {"L_nm": "12.4"}]


def test_export_saxs_bundle_returns_failed_status_if_manifest_fallback_also_fails(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(export_module, "_write_json", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("write failed")))

    bundle = export_saxs_bundle(_engine(), str(tmp_path / "failed"))

    assert bundle.status == "failed"
    assert any(error.startswith("export_failed:") for error in bundle.errors)


def test_export_saxs_bundle_persists_quality_evidence_and_ai_audit(tmp_path) -> None:
    engine = _engine()
    engine._analysis = SimpleNamespace(
        q=np.asarray([0.1, 0.2, 0.3]),
        I=np.asarray([10.0, 8.0, 5.0]),
        I_smooth=np.asarray([9.5, 7.5, 4.5]),
        data_quality_report={"level": "Trend", "source_id": "frame-0"},
        guinier_evidence={"level": "Diagnostic", "reason_codes": ["qrg_gate_failed"]},
        metric_evidence={"porod": {"level": "Trend"}},
        detector_quality_report={"source_kind": "sector_map", "level": "Diagnostic"},
        orientation_evidence={"level": "Diagnostic", "metric_name": "Orientation"},
    )
    engine.saxs_ai_rescue_plan = {
        "candidate_only": True,
        "original_preserved": True,
    }
    engine.saxs_ai_rescue_decision = {
        "decision": "keep_original",
        "apply_allowed": False,
    }

    bundle = export_saxs_bundle(engine, str(tmp_path / "quality"))

    root = tmp_path / "quality"
    payload = json.loads((root / "quality_evidence.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "bundle_manifest.json").read_text(encoding="utf-8"))

    assert bundle.status == "ok"
    assert manifest["files"]["quality_evidence"] == "quality_evidence.json"
    assert payload["static"]["metric_evidence"]["porod"]["level"] == "Trend"
    assert payload["static"]["orientation_evidence"]["level"] == "Diagnostic"
    assert payload["ai_rescue"]["plan"]["candidate_only"] is True
    assert payload["ai_rescue"]["decision"]["apply_allowed"] is False


def test_export_saxs_bundle_preserves_series_and_frame_metric_evidence(tmp_path) -> None:
    engine = _engine()
    summary = {
        "porod": {
            "metric_name": "porod",
            "frame_count": 2,
            "evidence_frame_count": 1,
            "usable_frame_count": 1,
            "diagnostic_frame_count": 0,
            "unusable_frame_count": 0,
            "missing_frame_count": 1,
            "coverage_fraction": 0.5,
            "level": "Diagnostic",
            "applicable": False,
            "level_counts": {"Quantitative": 0, "Trend": 1, "Diagnostic": 0, "Unusable": 0},
            "reason_codes": ["series_metric_missing_frames"],
            "source_ref": "temperature.metric_evidence",
        }
    }
    frame = {"porod": {"metric_name": "Porod", "level": "Trend", "source": "frame-0"}}
    summary_before = copy.deepcopy(summary)
    frame_before = copy.deepcopy(frame)
    engine._temperature_result = SimpleNamespace(
        metric_evidence=summary,
        temp_points=[SimpleNamespace(metric_evidence=frame)],
    )

    bundle = export_saxs_bundle(engine, str(tmp_path / "series_quality"))

    root = tmp_path / "series_quality"
    payload = json.loads((root / "quality_evidence.json").read_text(encoding="utf-8"))
    assert bundle.status == "ok"
    assert payload["temperature"]["metric_evidence"]["porod"]["level"] == "Diagnostic"
    assert payload["temperature"]["frames"][0]["metric_evidence"]["porod"]["level"] == "Trend"
    assert summary == summary_before
    assert frame == frame_before


def test_export_saxs_bundle_preserves_static_batch_frame_and_summary_evidence(tmp_path) -> None:
    engine = _engine()
    engine._batch_results = [
        SimpleNamespace(
            metric_evidence={"porod": {"metric_name": "Porod", "level": "Trend"}},
            data_quality_report={"level": "Trend", "source_id": "frame-0"},
        ),
        None,
        SimpleNamespace(
            metric_evidence={"porod": {"metric_name": "Porod", "level": "Diagnostic"}},
            data_quality_report={"level": "Diagnostic", "source_id": "frame-2"},
        ),
    ]

    bundle = export_saxs_bundle(engine, str(tmp_path / "static_batch_quality"))

    root = tmp_path / "static_batch_quality"
    payload = json.loads((root / "quality_evidence.json").read_text(encoding="utf-8"))
    static = payload["static"]

    assert bundle.status == "ok"
    assert static["metric_evidence_scope"] == "static_batch"
    assert static["metric_evidence"]["porod"]["frame_count"] == 3
    assert static["metric_evidence"]["porod"]["missing_frame_count"] == 1
    assert [frame["frame_index"] for frame in static["frames"]] == [0, 2]
    assert static["frames"][0]["metric_evidence"]["porod"]["level"] == "Trend"
    quality_text = (root / "quality_evidence.json").read_text(encoding="utf-8")
    assert "NaN" not in quality_text
    assert "Infinity" not in quality_text


def test_export_saxs_bundle_marks_missing_temperature_series_as_aligned_batch(tmp_path) -> None:
    engine = _engine()
    engine.cfg.experiment_type = "temperature"
    engine._batch_results = [
        SimpleNamespace(metric_evidence={"porod": {"metric_name": "Porod", "level": "Trend"}}),
        None,
    ]

    bundle = export_saxs_bundle(engine, str(tmp_path / "aligned_batch_quality"))

    payload = json.loads(
        (tmp_path / "aligned_batch_quality" / "quality_evidence.json").read_text(
            encoding="utf-8"
        )
    )
    assert bundle.status == "ok"
    assert payload["static"]["metric_evidence_scope"] == "aligned_batch"
