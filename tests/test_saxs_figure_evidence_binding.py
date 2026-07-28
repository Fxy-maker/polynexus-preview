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
                "paper_figure_candidate": True,
                "paper_conclusion_candidate": True,
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


def _ai_rescue_audit() -> dict[str, object]:
    return {
        "saxs_ai_rescue_plan": {
            "intent": {"technique": "SAXS", "raw_curve": [1.0, 2.0]},
            "policy_version": "saxs-v1",
            "automation_state": "shadow",
            "candidate_only": True,
            "original_preserved": True,
            "physical_validation_required": True,
            "reason_codes": ["candidate_only"],
            "candidates": [
                {
                    "candidate_id": "candidate-1",
                    "config": {"q_min": 0.1, "raw_curve": [3.0, 4.0]},
                }
            ],
        },
        "saxs_ai_rescue_decision": {
            "decision": "request_confirmation",
            "simulated_decision": "auto_accept",
            "confidence_band": "medium",
            "apply_allowed": True,
            "original_preserved": True,
            "physical_validation_required": True,
            "hard_guard_results": {"physical": True},
            "reason_codes": ["confirmation_required"],
        },
        "saxs_ai_rescue_replay": [
            {
                "candidate_id": "candidate-1",
                "mode": "static",
                "run_status": "not_run",
                "decision": "request_confirmation",
                "apply_performed": False,
                "raw_curve": [5.0, 6.0],
            }
        ],
        "saxs_confirmed_rerun_audit": {
            "candidate_id": "candidate-1",
            "mode": "static",
            "phase": "rolled_back",
            "apply_performed": False,
            "physical_gate_status": "pass",
            "quality_gate_status": "fail",
            "rollback_reason": "quality_gate_failed",
            "before_config_hash": "before",
            "after_config_hash": "after",
        },
    }


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


def test_ai_rescue_audit_binds_to_static_figure_and_manifest_without_roles(tmp_path) -> None:
    engine = _static_engine()
    audit = _ai_rescue_audit()
    for key, value in audit.items():
        setattr(engine, key, value)

    definitions = build_static_saxs_figure_definitions(engine)
    provenance = definitions[0].recipe["evidence"]["quality_provenance"]
    ai_rescue = provenance["ai_rescue"]

    json.dumps(ai_rescue, allow_nan=False)
    assert ai_rescue["plan"]["candidate_ids"] == ["candidate-1"]
    assert ai_rescue["decision"]["decision"] == "request_confirmation"
    assert ai_rescue["replay"][0]["run_status"] == "not_run"
    assert ai_rescue["confirmed_rerun"]["phase"] == "rolled_back"
    assert "intent" not in ai_rescue["plan"]
    assert "candidates" not in ai_rescue["plan"]
    assert "raw_curve" not in json.dumps(ai_rescue)
    assert definitions[0].publication_role == "main"

    FigurePipeline().run(
        output_root=tmp_path,
        run_id="saxs-ai-evidence",
        technique="saxs",
        definitions=(definitions[0],),
    )
    document = next(
        (tmp_path / "runs" / "saxs-ai-evidence" / "figures").glob(
            "*/figure.pnfig.json"
        )
    )
    persisted = json.loads(document.read_text(encoding="utf-8"))
    assert persisted["recipe"]["evidence"]["quality_provenance"]["ai_rescue"] == ai_rescue
    audit["saxs_ai_rescue_plan"]["candidates"][0]["candidate_id"] = "changed"  # type: ignore[index]
    assert ai_rescue["plan"]["candidate_ids"] == ["candidate-1"]


def test_malformed_ai_rescue_audit_is_ignored_by_figure_projection() -> None:
    payload = build_saxs_figure_evidence(
        (_frame(),),
        mode="static",
        ai_rescue={
            "saxs_ai_rescue_plan": [],
            "saxs_ai_rescue_decision": "request_confirmation",
            "saxs_ai_rescue_replay": [{"run_status": "not_run"}, None],
            "saxs_confirmed_rerun_audit": {"apply_performed": False},
        },
    )

    assert "ai_rescue" not in payload


def test_ai_rescue_audit_reaches_temperature_and_strain_providers() -> None:
    audit = _ai_rescue_audit()
    for engine, builder in (
        (_temperature_engine(), build_temperature_figure_definitions),
        (_strain_engine(), build_strain_figure_definitions),
    ):
        for key, value in audit.items():
            setattr(engine, key, value)

        definitions = builder(engine)

        assert definitions
        assert all(
            "ai_rescue"
            in definition.recipe["evidence"]["quality_provenance"]
            for definition in definitions
        )


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
