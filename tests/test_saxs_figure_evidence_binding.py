from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np

from polynexus.core.figures.pipeline import FigurePipeline
from polynexus.core.saxs_engine.figure_evidence import (
    build_saxs_figure_evidence,
)
from polynexus.core.saxs_engine.figure_static import (
    build_static_saxs_figure_definitions,
)
from polynexus.core.saxs_engine.figure_strain import build_strain_figure_definitions
from polynexus.core.saxs_engine.figure_temperature import (
    build_temperature_figure_definitions,
)
from polynexus.core.saxs_engine.figure_common import SAXSFrameView
from polynexus.core.saxs_engine.saxs_temperature import TempSeriesResult


def _frame(
    *,
    index: int = 0,
    condition: float = 25.0,
    metric_evidence: dict[str, object] | None = None,
    analysis: object | None = None,
    parameters: dict[str, object] | None = None,
    source_path: str = "sample.dat",
) -> SAXSFrameView:
    return SAXSFrameView(
        index=index,
        label=f"frame-{index}",
        condition=condition,
        q=np.asarray([0.1, 0.2, 0.3], dtype=float),
        intensity=np.asarray([2.0, 4.0, 3.0], dtype=float),
        analysis=analysis
        or SimpleNamespace(
            quality_flag="OK",
            metric_evidence=metric_evidence or {},
        ),
        parameters=parameters or {},
        source_path=source_path,
    )


def _static_engine(*, with_evidence: bool = True) -> SimpleNamespace:
    rows = []
    analyses = []
    for index in range(2):
        metric = (
            {
                "porod": {
                    "metric_name": "Porod",
                    "level": "Trend",
                    "value": float("nan"),
                    "reason_codes": ["observed"],
                    "source_ref": "saxs_engine.porod",
                }
            }
            if with_evidence
            else {}
        )
        rows.append(
            {
                "file": f"sample-{index}.dat",
                "quality_flag": "OK",
                "L_nm": 15.0,
                "lc_nm": 6.0,
                "la_nm": 9.0,
                "Xc": 0.4,
                "Q_rel": 1.0,
                "Q_star_valid": True,
                "lc_confidence": 0.8,
                "metric_evidence": metric,
            }
        )
        analyses.append(
            SimpleNamespace(
                label=f"sample-{index}",
                condition_value=float(index),
                q=np.asarray([0.1, 0.2, 0.3]),
                I=np.asarray([2.0, 4.0, 3.0]),
                I_smooth=np.asarray([2.0, 4.0, 3.0]),
                final_parameters=rows[-1],
                metric_evidence=metric,
            )
        )
    return SimpleNamespace(
        _batch_results=analyses,
        _batch_params=rows,
        _q_list=[item.q for item in analyses],
        _I_list=[item.I for item in analyses],
        _conditions=[0.0, 1.0],
        _file_list=[item["file"] for item in rows],
        _analysis=None,
        _temperature_result=None,
        _strain_result=None,
        _condition_type="static",
        cfg=SimpleNamespace(experiment_type="static"),
    )


def _temperature_engine() -> SimpleNamespace:
    frames = [
        _frame(index=0, condition=20.0, source_path="source-0.dat"),
        _frame(index=1, condition=30.0, source_path="source-1.dat"),
    ]
    analyses = [frame.analysis for frame in frames]
    parameters = [
        {
            "quality_flag": "OK",
            "L_nm": 15.0,
            "lc_nm": 6.0,
            "la_nm": 9.0,
            "Xc_effective": 0.4,
        }
        for _ in frames
    ]
    sequence = {
        "frame_count": 2,
        "frame_source_indices": [1, 0],
        "level": "Trend",
        "reason_codes": [],
        "source_ref": "saxs_temperature.guinier_sequence",
    }
    result = TempSeriesResult(
        temperatures=np.asarray([20.0, 30.0]),
        metric_evidence={
            "guinier": {
                "metric_name": "Rg_sequence",
                "level": "Trend",
                "source_ref": "saxs_temperature.metric_evidence",
            }
        },
        guinier_sequence_evidence=sequence,
    )
    result.temp_points = [
        SimpleNamespace(source_index=1),
        SimpleNamespace(source_index=0),
    ]
    return SimpleNamespace(
        _temperature_result=result,
        _batch_results=analyses,
        _batch_params=parameters,
        _q_list=[frame.q for frame in frames],
        _I_list=[frame.intensity for frame in frames],
        _conditions=np.asarray([20.0, 30.0]),
        _file_list=[frame.source_path for frame in frames],
        _condition_type="temperature",
        _results=[],
        cfg=SimpleNamespace(
            experiment_type="temperature",
            condition_label="Temperature",
            condition_unit="C",
        ),
    )


def _strain_engine() -> SimpleNamespace:
    engine = _static_engine()
    engine._condition_type = "strain"
    engine.cfg.experiment_type = "strain"
    engine._strain_result = SimpleNamespace(
        strains=np.asarray([0.0, 25.0]),
        metric_evidence={
            "porod": {
                "metric_name": "Porod",
                "level": "Trend",
                "source_ref": "saxs_strain.metric_evidence",
            }
        },
        detector_quality_report={
            "metric_name": "DetectorQuality",
            "level": "Diagnostic",
            "source_ref": "saxs_strain.detector_quality_report",
        },
        orientation_evidence={
            "metric_name": "Orientation",
            "level": "Trend",
            "source_ref": "saxs_strain.orientation_evidence",
        },
    )
    return engine


def test_projection_is_detached_and_strict_json_safe() -> None:
    metric = {
        "metric_name": "Porod",
        "level": "Trend",
        "value": float("nan"),
        "reason_codes": ["observed"],
    }
    frame = _frame(metric_evidence={"porod": metric})

    payload = build_saxs_figure_evidence((frame,), mode="static")

    json.dumps(payload, allow_nan=False)
    assert payload["frame_records"][0]["metric_evidence"]["porod"]["value"] is None
    metric["level"] = "Unusable"
    assert payload["frame_records"][0]["metric_evidence"]["porod"]["level"] == "Trend"


def test_frame_projection_preserves_condition_axis_and_strict_json() -> None:
    axis = {
        "condition_name": "temperature_C",
        "condition_values": [20.0, float("nan"), 18.0],
        "invalid_condition_indices": [1],
        "duplicate_condition_indices": [0, 2],
        "nonmonotonic_condition_indices": [2],
        "status": "diagnostic",
    }
    metric = {
        "metric_name": "Porod",
        "level": "Diagnostic",
        "condition_axis": axis,
    }
    frame = _frame(metric_evidence={"porod": metric})

    payload = build_saxs_figure_evidence((frame,), mode="temperature")

    json.dumps(payload, allow_nan=False)
    projected = payload["frame_records"][0]["metric_evidence"]["porod"]
    assert projected["condition_axis"] == {
        **axis,
        "condition_values": [20.0, None, 18.0],
    }
    axis["condition_values"][0] = 999.0
    assert projected["condition_axis"]["condition_values"][0] == 20.0


def test_temperature_series_projection_preserves_condition_axis_and_sequence_source():
    engine = _temperature_engine()
    source_axis = {
        "condition_name": "temperature_C",
        "condition_values": [20.0, 30.0],
        "invalid_condition_indices": [],
        "duplicate_condition_indices": [],
        "nonmonotonic_condition_indices": [],
        "status": "ordered",
    }
    engine._temperature_result.metric_evidence["guinier"]["condition_axis"] = source_axis

    definition = build_temperature_figure_definitions(engine)[0]
    provenance = definition.recipe["evidence"]["quality_provenance"]

    json.dumps(provenance, allow_nan=False)
    assert provenance["series_record"]["metric_evidence"]["guinier"][
        "condition_axis"
    ] == source_axis
    assert provenance["series_record"]["guinier_sequence_evidence"][
        "frame_source_indices"
    ] == [1, 0]
    source_axis["condition_values"][0] = 999.0
    assert (
        provenance["series_record"]["metric_evidence"]["guinier"][
            "condition_axis"
        ]["condition_values"][0]
        == 20.0
    )


def test_static_provider_binds_frame_evidence_without_changing_roles() -> None:
    definitions = build_static_saxs_figure_definitions(_static_engine())

    provenance = definitions[0].recipe["evidence"]["quality_provenance"]

    assert provenance["mode"] == "static"
    assert provenance["frame_records"][0]["metric_evidence"]["porod"]["level"] == "Trend"
    assert definitions[0].publication_role == "main"


def test_missing_or_malformed_evidence_is_not_promoted_or_fatal() -> None:
    definitions = build_static_saxs_figure_definitions(
        _static_engine(with_evidence=False)
    )

    assert definitions
    for definition in definitions:
        provenance = definition.recipe.get("evidence", {}).get(
            "quality_provenance", {}
        )
        assert provenance.get("frame_records", [{}])[0].get("metric_evidence", {}) == {}


def test_temperature_binding_keeps_frame_and_original_source_indices() -> None:
    definitions = build_temperature_figure_definitions(_temperature_engine())

    provenance = definitions[0].recipe["evidence"]["quality_provenance"]

    assert [row["source_index"] for row in provenance["frame_records"]] == [0, 1]
    assert provenance["series_record"]["guinier_sequence_evidence"][
        "frame_source_indices"
    ] == [1, 0]


def test_strain_binding_keeps_orientation_separate_and_survives_manifest_document(
    tmp_path,
) -> None:
    definition = build_strain_figure_definitions(_strain_engine())[0]
    provenance = definition.recipe["evidence"]["quality_provenance"]

    assert "orientation_evidence" in provenance["series_record"]
    assert "orientation" not in provenance["series_record"].get(
        "metric_evidence", {}
    )

    FigurePipeline().run(
        output_root=tmp_path,
        run_id="saxs-evidence",
        technique="saxs",
        definitions=(definition,),
    )
    document = next(
        (tmp_path / "runs" / "saxs-evidence" / "figures").glob(
            "*/figure.pnfig.json"
        )
    )
    payload = json.loads(document.read_text(encoding="utf-8"))
    json.dumps(payload, allow_nan=False)
    assert (
        payload["recipe"]["evidence"]["quality_provenance"][
            "quality_evidence_file"
        ]
        == "quality_evidence.json"
    )
