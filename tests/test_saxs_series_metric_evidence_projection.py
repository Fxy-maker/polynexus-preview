from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from polynexus.core.engine import AnalysisResult
from polynexus.core.figures.pipeline import FigurePipeline
from polynexus.core.saxs_engine.figure_common import SAXSFrameView
from polynexus.core.saxs_engine.figure_evidence import build_saxs_figure_evidence
from polynexus.core.saxs_engine.figure_temperature import build_temperature_figure_definitions
from polynexus.core.saxs_export_bundle import export_saxs_bundle
from polynexus.core.saxs_engine.config import SAXSConfig


def _summary() -> dict[str, object]:
    return {
        "metric_name": "Porod",
        "level": "Diagnostic",
        "frame_count": 2,
        "frame_source_indices": [],
        "duplicate_source_index_indices": [0, 1],
        "invalid_source_index_indices": [],
        "source_index_order_reordered": False,
        "reason_codes": ["series_metric_source_index_duplicate"],
        "source_ref": "saxs_temperature.metric_evidence",
    }


def _frame() -> SAXSFrameView:
    return SAXSFrameView(
        index=0,
        label="frame-0",
        condition=20.0,
        q=np.asarray([0.1, 0.2]),
        intensity=np.asarray([2.0, 1.0]),
        analysis=SimpleNamespace(metric_evidence={}),
        parameters={},
        source_path="frame-0.edf",
    )


def _export_engine(summary: dict[str, object]) -> SimpleNamespace:
    result = AnalysisResult(technique="saxs", parameters={})
    analysis = SimpleNamespace(
        label="frame-0",
        q=np.asarray([0.1, 0.2]),
        I=np.asarray([2.0, 1.0]),
        final_parameters={"quality_flag": "OK"},
    )
    return SimpleNamespace(
        result=result,
        cfg=SAXSConfig(
            experiment_type="temperature",
            condition_label="Temperature",
            condition_unit="C",
        ),
        _analysis=None,
        _batch_results=[analysis],
        _batch_params=[{"quality_flag": "OK"}],
        _temperature_result=SimpleNamespace(metric_evidence={"porod": summary}, temp_points=[]),
        _strain_result=None,
        _conditions=np.asarray([20.0]),
        _q_list=[analysis.q],
        _I_list=[analysis.I],
        _processed_list=[],
        _file_list=["frame-0.edf"],
    )


def test_figure_projection_preserves_source_integrity_fields_and_detaches_values() -> None:
    summary = _summary()
    series = SimpleNamespace(metric_evidence={"porod": summary})

    payload = build_saxs_figure_evidence((_frame(),), mode="temperature", series=series)

    projected = payload["series_record"]["metric_evidence"]["porod"]
    json.dumps(payload, allow_nan=False)
    assert projected["duplicate_source_index_indices"] == [0, 1]
    assert projected["invalid_source_index_indices"] == []
    assert projected["source_index_order_reordered"] is False
    summary["duplicate_source_index_indices"] = [99]
    assert projected["duplicate_source_index_indices"] == [0, 1]


def test_manifest_persists_series_source_integrity_fields(tmp_path: Path) -> None:
    summary = _summary()
    engine = _export_engine(summary)
    definition = build_temperature_figure_definitions(engine)[0]
    FigurePipeline().run(
        output_root=tmp_path,
        run_id="saxs-series-metric-evidence",
        technique="saxs",
        definitions=(definition,),
    )
    output = next(
        (tmp_path / "runs" / "saxs-series-metric-evidence" / "figures").glob(
            "*/figure.pnfig.json"
        )
    )
    persisted = json.loads(output.read_text(encoding="utf-8"))

    assert (
        persisted["recipe"]["evidence"]["quality_provenance"]["series_record"]
        ["metric_evidence"]["porod"]["duplicate_source_index_indices"]
        == [0, 1]
    )


def test_export_preserves_series_source_integrity_fields(tmp_path: Path) -> None:
    summary = _summary()
    bundle = export_saxs_bundle(_export_engine(summary), str(tmp_path / "bundle"))

    assert bundle.status == "ok"
    quality = json.loads(
        (tmp_path / "bundle" / "quality_evidence.json").read_text(encoding="utf-8")
    )
    projected = quality["temperature"]["metric_evidence"]["porod"]
    assert projected["duplicate_source_index_indices"] == [0, 1]
    assert projected["invalid_source_index_indices"] == []
    assert projected["source_index_order_reordered"] is False
