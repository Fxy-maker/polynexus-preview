from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np

from polynexus.core.figures.pipeline import FigurePipeline
from polynexus.core.figures.v2_capabilities import build_v2_definition_artifact
from polynexus.core.saxs import SAXSEngine
from polynexus.core.saxs_engine.figure_evidence import (
    build_saxs_figure_evidence,
    sync_saxs_review_evidence_to_existing_figures,
)
import polynexus.core.saxs_engine.figure_strain as figure_strain_module
from polynexus.core.saxs_engine.figure_static import (
    build_static_saxs_figure_definitions,
)
from polynexus.core.saxs_engine.figure_strain import build_strain_figure_definitions
from polynexus.core.saxs_engine.figure_temperature import (
    build_temperature_figure_definitions,
)
from polynexus.core.saxs_engine.figure_common import (
    SAXSFrameView,
    frame_views_from_engine,
)
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


def _accepted_saxs_1d_review(*source_refs: str) -> dict[str, object]:
    return {
        "record_id": "review-saxs-1d-downstream",
        "scope": "saxs.1d",
        "reviewer": "reviewer-saxs",
        "reviewed_at": "2026-07-31",
        "policy_version": "saxs-1d-v1",
        "source_refs": list(source_refs),
        "decisions": {
            "sequence_axis_policy": "existing temperature/source order",
            "frame_identity_policy": "source-linked frame identity",
            "missing_repeat_policy": "retain missing repeats",
            "metric_claim_scope": "diagnostic evidence only",
            "promotion_rule": "existing gates and source-matched review",
        },
        "status": "accepted",
        "conditions": [],
    }


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


def test_workbench_result_review_reaches_new_figure_and_manifest(tmp_path) -> None:
    engine = _static_engine()
    review = _accepted_saxs_1d_review("sample-0.dat", "sample-1.dat")
    engine.result = SimpleNamespace(
        metadata={"scientific_review": review},
        parameters={},
    )

    definitions = build_static_saxs_figure_definitions(engine)
    provenance = definitions[0].recipe["evidence"]["quality_provenance"]

    assert provenance["scientific_review"]["reason"] == "review_accepted"
    assert definitions[0].publication_role == "main"

    FigurePipeline().run(
        output_root=tmp_path,
        run_id="saxs-workbench-review",
        technique="saxs",
        definitions=(definitions[0],),
    )
    document = next(
        (tmp_path / "runs" / "saxs-workbench-review" / "figures").glob(
            "*/figure.pnfig.json"
        )
    )
    persisted = json.loads(document.read_text(encoding="utf-8"))
    persisted_review = persisted["recipe"]["evidence"]["quality_provenance"][
        "scientific_review"
    ]
    assert persisted_review["record_id"] == review["record_id"]
    assert persisted_review["reason"] == "review_accepted"


def test_workbench_result_review_source_mismatch_remains_fail_closed() -> None:
    engine = _static_engine()
    engine.result = SimpleNamespace(
        metadata={"scientific_review": _accepted_saxs_1d_review("other.dat")},
        parameters={},
    )

    definitions = build_static_saxs_figure_definitions(engine)
    review = definitions[0].recipe["evidence"]["quality_provenance"][
        "scientific_review"
    ]

    assert review["allowed"] is False
    assert review["reason"] == "source_mismatch"


def test_existing_figure_review_sync_updates_only_review_provenance(tmp_path) -> None:
    engine = _static_engine()
    definitions = build_static_saxs_figure_definitions(engine)
    FigurePipeline().run(
        output_root=tmp_path,
        run_id="saxs-existing-review-sync",
        technique="saxs",
        definitions=(definitions[0],),
    )
    manifest_path = (
        tmp_path / "runs" / "saxs-existing-review-sync" / "figure_manifest.json"
    )
    manifest_before = json.loads(manifest_path.read_text(encoding="utf-8"))
    document_path = tmp_path / "runs" / "saxs-existing-review-sync" / manifest_before[
        "figures"
    ][0]["document"]
    document_before = json.loads(document_path.read_text(encoding="utf-8"))
    review = _accepted_saxs_1d_review("sample-0.dat", "sample-1.dat")

    report = sync_saxs_review_evidence_to_existing_figures(
        manifest_path,
        frame_views_from_engine(engine),
        review,
    )

    document_after = json.loads(document_path.read_text(encoding="utf-8"))
    manifest_after = json.loads(manifest_path.read_text(encoding="utf-8"))
    before_provenance = document_before["recipe"]["evidence"]["quality_provenance"]
    after_provenance = document_after["recipe"]["evidence"]["quality_provenance"]

    assert report["status"] == "ok"
    assert report["updated_count"] == 1
    assert after_provenance["scientific_review"]["reason"] == "review_accepted"
    assert before_provenance.get("scientific_review") is None
    document_before["recipe"]["evidence"]["quality_provenance"].pop(
        "scientific_review", None
    )
    document_after["recipe"]["evidence"]["quality_provenance"].pop(
        "scientific_review", None
    )
    assert document_after == document_before
    assert manifest_after == manifest_before


def test_existing_figure_review_sync_is_fail_closed_for_bad_review(tmp_path) -> None:
    engine = _static_engine()
    definitions = build_static_saxs_figure_definitions(engine)
    FigurePipeline().run(
        output_root=tmp_path,
        run_id="saxs-existing-review-fail-closed",
        technique="saxs",
        definitions=(definitions[0],),
    )
    manifest_path = (
        tmp_path / "runs" / "saxs-existing-review-fail-closed" / "figure_manifest.json"
    )
    document_path = tmp_path / "runs" / "saxs-existing-review-fail-closed" / "figures" / "saxs.static.comparison" / "figure.pnfig.json"
    before = json.loads(document_path.read_text(encoding="utf-8"))
    cancelled = _accepted_saxs_1d_review("sample-0.dat", "sample-1.dat")
    cancelled["status"] = "cancelled"

    report = sync_saxs_review_evidence_to_existing_figures(
        manifest_path,
        frame_views_from_engine(engine),
        cancelled,
    )

    after = json.loads(document_path.read_text(encoding="utf-8"))
    review = after["recipe"]["evidence"]["quality_provenance"]["scientific_review"]
    assert report["status"] == "ok"
    assert review["allowed"] is False
    assert review["reason"] != "review_accepted"
    before["recipe"]["evidence"]["quality_provenance"].pop(
        "scientific_review", None
    )
    after["recipe"]["evidence"]["quality_provenance"].pop(
        "scientific_review", None
    )
    assert after == before


def test_existing_figure_review_sync_uses_detector_scope_boundary(tmp_path) -> None:
    engine = _static_engine()
    definitions = build_static_saxs_figure_definitions(engine)
    FigurePipeline().run(
        output_root=tmp_path,
        run_id="saxs-existing-review-2d-scope",
        technique="saxs",
        definitions=(definitions[0],),
    )
    manifest_path = (
        tmp_path / "runs" / "saxs-existing-review-2d-scope" / "figure_manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["figures"][0]["figure_id"] = "saxs.static.detector.2d"
    document_path = tmp_path / "runs" / "saxs-existing-review-2d-scope" / manifest[
        "figures"
    ][0]["document"]
    document = json.loads(document_path.read_text(encoding="utf-8"))
    document["recipe"]["source_capability"] = "detector_2d"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    document_path.write_text(json.dumps(document), encoding="utf-8")

    report = sync_saxs_review_evidence_to_existing_figures(
        manifest_path,
        frame_views_from_engine(engine),
        _accepted_saxs_1d_review("sample-0.dat", "sample-1.dat"),
    )

    updated = json.loads(document_path.read_text(encoding="utf-8"))
    review = updated["recipe"]["evidence"]["quality_provenance"]["scientific_review"]
    assert report["updated_count"] == 1
    assert review["allowed"] is False
    assert review["reason"] == "scope_mismatch"


def test_existing_figure_review_sync_missing_manifest_is_nonfatal(tmp_path) -> None:
    report = sync_saxs_review_evidence_to_existing_figures(
        tmp_path / "missing" / "figure_manifest.json",
        (),
        {},
    )

    assert report["status"] == "skipped"
    assert report["updated_count"] == 0


def test_saxs_engine_review_sync_uses_current_result_manifest(tmp_path) -> None:
    source_engine = _static_engine()
    definitions = build_static_saxs_figure_definitions(source_engine)
    FigurePipeline().run(
        output_root=tmp_path,
        run_id="saxs-engine-review-sync",
        technique="saxs",
        definitions=(definitions[0],),
    )
    manifest_path = tmp_path / "runs" / "saxs-engine-review-sync" / "figure_manifest.json"
    engine = SAXSEngine.__new__(SAXSEngine)
    engine.__dict__.update(vars(source_engine))
    engine.result = SimpleNamespace(metadata={"figure_manifest": str(manifest_path)})

    report = engine.sync_scientific_review_to_figures(
        _accepted_saxs_1d_review("sample-0.dat", "sample-1.dat")
    )

    assert report["status"] == "ok"
    assert report["updated_count"] == 1


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


def test_scientific_acceptance_audit_reaches_all_production_providers() -> None:
    audit = {
        "status": "diagnostic_only",
        "reason_codes": ["existing_evidence_not_quantitative"],
        "audit_scope": "existing_gates_only",
    }
    for engine, builder in (
        (_static_engine(), build_static_saxs_figure_definitions),
        (_temperature_engine(), build_temperature_figure_definitions),
        (_strain_engine(), build_strain_figure_definitions),
    ):
        engine.result = SimpleNamespace(parameters={"scientific_acceptance_audit": audit})

        definitions = builder(engine)

        assert definitions
        assert all(
            definition.recipe["evidence"]["quality_provenance"][
                "scientific_acceptance_audit"
            ]
            == audit
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


def test_advanced_v2_static_figures_are_v2_ready() -> None:
    definitions = build_static_saxs_figure_definitions(_static_engine())

    assert definitions
    assert all(item.recipe["v2_adapter"] == "saxs_static" for item in definitions)
    assert all(
        build_v2_definition_artifact(item).capability["v2_runtime"] == "ready"
        for item in definitions
    )


def test_advanced_v2_temperature_figures_are_v2_ready() -> None:
    definitions = build_temperature_figure_definitions(_temperature_engine())

    assert definitions
    assert all(
        item.recipe["v2_adapter"] == "temperature_saxs" for item in definitions
    )
    assert all(
        build_v2_definition_artifact(item).capability["v2_runtime"] == "ready"
        for item in definitions
    )


def test_advanced_v2_pipeline_writes_manifest_sidecars(tmp_path) -> None:
    provider_cases = (
        (
            "static",
            build_static_saxs_figure_definitions(_static_engine()),
        ),
        (
            "temperature",
            build_temperature_figure_definitions(_temperature_engine()),
        ),
    )

    for mode, definitions in provider_cases:
        run_id = f"saxs-advanced-v2-{mode}"
        manifest = FigurePipeline().run(
            output_root=tmp_path,
            run_id=run_id,
            technique="saxs",
            definitions=(definitions[0],),
        )
        entry = manifest.figures[0]
        assert entry.status == "ready"
        assert entry.capability_report["v2_runtime"] == "ready"
        sidecar = (
            tmp_path
            / "runs"
            / run_id
            / entry.capability_report["v2_sidecar"]
        )
        assert sidecar.is_file()


def test_strain_v2_figures_are_v2_ready() -> None:
    definitions = build_strain_figure_definitions(_strain_engine())

    assert definitions
    assert all(item.recipe["v2_adapter"] == "saxs_strain" for item in definitions)
    assert all(
        build_v2_definition_artifact(item).capability["v2_runtime"] == "ready"
        for item in definitions
    )


def test_strain_v2_pipeline_writes_manifest_sidecar(tmp_path) -> None:
    definition = build_strain_figure_definitions(_strain_engine())[0]

    manifest = FigurePipeline().run(
        output_root=tmp_path,
        run_id="saxs-strain-v2",
        technique="saxs",
        definitions=(definition,),
    )

    entry = manifest.figures[0]
    assert entry.status == "ready"
    assert entry.capability_report["v2_runtime"] == "ready"
    sidecar = (
        tmp_path
        / "runs"
        / "saxs-strain-v2"
        / entry.capability_report["v2_sidecar"]
    )
    assert sidecar.is_file()


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


def test_dirty_projection_strain_keeps_profile_and_q_strain_sources() -> None:
    engine = _strain_engine()
    engine._q_list[0] = np.asarray(
        ["0.1", "bad-q", "0.3", "0.4"],
        dtype=object,
    )
    engine._I_list[0] = np.asarray(
        ["2.0", "3.0", "4.0", "bad-intensity"],
        dtype=object,
    )

    definitions = build_strain_figure_definitions(engine)
    evolution = next(
        item
        for item in definitions
        if item.figure_id == "saxs.strain.evolution.1d"
    )
    profile = next(
        item
        for item in evolution.data_sources
        if item.source_id == "representative-profile-000"
    )
    heatmap = next(
        item
        for item in evolution.data_sources
        if item.source_id == "q-strain-heatmap"
    )

    assert profile.values["q_nm_inv"] == (0.1, 0.3)
    assert profile.values["intensity"] == (2.0, 4.0)
    assert len(heatmap.values["q_nm_inv"]) >= 2


def test_strain_profile_provenance_records_dirty_pairs_in_main_and_sequence() -> None:
    engine = _strain_engine()
    engine._q_list[0] = np.asarray([0.1, 0.0, np.nan, 0.4], dtype=float)
    engine._I_list[0] = np.asarray([2.0, 3.0, 4.0, -1.0], dtype=float)

    definitions = build_strain_figure_definitions(engine)
    expected = {
        "input_pair_count": 4,
        "retained_pair_count": 1,
        "nonfinite_pair_count": 1,
        "nonpositive_pair_count": 2,
        "status": "partial_invalid",
    }

    for figure_id in ("saxs.strain.evolution.1d", "saxs.strain.sequence.1d"):
        definition = next(item for item in definitions if item.figure_id == figure_id)
        assert definition.recipe["parameters"]["profile_projection_quality"]["0"] == expected
        json.dumps(definition.recipe, allow_nan=False)


def test_strain_profile_provenance_records_complete_pairs_in_main_and_sequence() -> None:
    definitions = build_strain_figure_definitions(_strain_engine())
    expected = {
        "input_pair_count": 3,
        "retained_pair_count": 3,
        "nonfinite_pair_count": 0,
        "nonpositive_pair_count": 0,
        "status": "complete",
    }

    for figure_id in ("saxs.strain.evolution.1d", "saxs.strain.sequence.1d"):
        definition = next(item for item in definitions if item.figure_id == figure_id)
        assert definition.recipe["parameters"]["profile_projection_quality"]["0"] == expected
        json.dumps(definition.recipe, allow_nan=False)


def test_strain_auxiliary_provenance_records_dirty_low_q_and_traces() -> None:
    engine = _strain_engine()
    engine._q_list[0] = np.asarray([0.1, 0.2, 0.3, np.nan], dtype=float)
    engine._I_list[0] = np.asarray([2.0, 4.0, 3.0, 5.0], dtype=float)
    engine._batch_results[0].correlation = {
        "r": np.asarray(["1.0", "bad-r", "3.0", "4.0"], dtype=object),
        "gamma": np.asarray(["0.8", "0.5", "0.2", "bad-gamma"], dtype=object),
    }
    engine._batch_results[0].idf = {
        "r_idf": np.asarray(["1.0", "bad-r", "3.0", "4.0"], dtype=object),
        "idf": np.asarray(["0.2", "0.4", "0.3", "bad-idf"], dtype=object),
    }

    definitions = build_strain_figure_definitions(engine)
    low_q = next(item for item in definitions if item.figure_id == "saxs.strain.low-q.diagnostic")
    correlation = next(item for item in definitions if item.figure_id == "saxs.strain.correlation")
    idf = next(item for item in definitions if item.figure_id == "saxs.strain.idf")

    assert low_q.recipe["parameters"]["profile_projection_quality"]["0"] == {
        "input_pair_count": 4,
        "retained_pair_count": 3,
        "nonfinite_pair_count": 1,
        "nonpositive_pair_count": 0,
        "status": "partial_invalid",
    }
    expected_trace = {
        "input_pair_count": 4,
        "retained_pair_count": 2,
        "nonfinite_pair_count": 2,
        "status": "partial_nonfinite",
    }
    assert correlation.recipe["parameters"]["trace_projection_quality"]["0"] == expected_trace
    assert idf.recipe["parameters"]["trace_projection_quality"]["0"] == expected_trace
    for definition in (low_q, correlation, idf):
        json.dumps(definition.recipe, allow_nan=False)


def test_strain_auxiliary_provenance_records_complete_low_q_and_traces() -> None:
    engine = _strain_engine()
    engine._q_list[0] = np.asarray([0.1, 0.2, 0.3, 0.4], dtype=float)
    engine._I_list[0] = np.asarray([2.0, 4.0, 3.0, 1.0], dtype=float)
    engine._batch_results[0].correlation = {
        "r": np.asarray([1.0, 2.0, 3.0]),
        "gamma": np.asarray([0.8, 0.5, 0.2]),
    }
    engine._batch_results[0].idf = {
        "r_idf": np.asarray([1.0, 2.0, 3.0]),
        "idf": np.asarray([0.2, 0.4, 0.3]),
    }

    definitions = build_strain_figure_definitions(engine)
    low_q = next(item for item in definitions if item.figure_id == "saxs.strain.low-q.diagnostic")
    expected_profile = {
        "input_pair_count": 4,
        "retained_pair_count": 4,
        "nonfinite_pair_count": 0,
        "nonpositive_pair_count": 0,
        "status": "complete",
    }
    expected_trace = {
        "input_pair_count": 3,
        "retained_pair_count": 3,
        "nonfinite_pair_count": 0,
        "status": "complete",
    }
    assert low_q.recipe["parameters"]["profile_projection_quality"]["0"] == expected_profile
    for figure_id in ("saxs.strain.correlation", "saxs.strain.idf"):
        definition = next(item for item in definitions if item.figure_id == figure_id)
        assert definition.recipe["parameters"]["trace_projection_quality"]["0"] == expected_trace
        json.dumps(definition.recipe, allow_nan=False)
    json.dumps(low_q.recipe, allow_nan=False)


def test_dirty_static_profile_records_pair_provenance() -> None:
    engine = _static_engine()
    engine._q_list[0] = np.asarray([0.1, np.nan, 0.3, 0.4], dtype=float)
    engine._I_list[0] = np.asarray([2.0, 4.0, np.inf, 5.0], dtype=float)

    definition = next(
        item
        for item in build_static_saxs_figure_definitions(engine)
        if item.figure_id == "saxs.static.comparison"
    )

    assert definition.recipe["parameters"]["profile_projection_quality"]["0"] == {
        "input_pair_count": 4,
        "retained_pair_count": 2,
        "nonfinite_pair_count": 2,
        "nonpositive_pair_count": 0,
        "status": "partial_invalid",
    }
    json.dumps(definition.recipe, allow_nan=False)


def test_clean_static_profile_records_complete_provenance() -> None:
    definition = next(
        item
        for item in build_static_saxs_figure_definitions(_static_engine())
        if item.figure_id == "saxs.static.comparison"
    )

    assert definition.recipe["parameters"]["profile_projection_quality"]["0"] == {
        "input_pair_count": 3,
        "retained_pair_count": 3,
        "nonfinite_pair_count": 0,
        "nonpositive_pair_count": 0,
        "status": "complete",
    }
    json.dumps(definition.recipe, allow_nan=False)


def test_dirty_projection_strain_trace_keeps_valid_pairs() -> None:
    engine = _strain_engine()
    engine._batch_results[0].correlation = {
        "r": np.asarray(["1.0", "bad-r", "3.0", "4.0"], dtype=object),
        "gamma": np.asarray(["0.8", "0.5", "0.2", "bad-gamma"], dtype=object),
    }

    definitions = build_strain_figure_definitions(engine)
    correlation = next(
        item for item in definitions if item.figure_id == "saxs.strain.correlation"
    )
    source = next(
        item
        for item in correlation.data_sources
        if item.source_id == "correlation-trace-000"
    )

    assert source.values["x"] == (1.0, 3.0)
    assert source.values["y"] == (0.8, 0.2)


def test_dirty_detector_projection_keeps_finite_sampled_pixels(monkeypatch) -> None:
    engine = _strain_engine()
    engine._file_list = ["sample-0.edf", "sample-1.edf"]
    image = np.asarray(
        [[1.0, np.nan, 10.0], [np.inf, 5.0, -2.0]],
        dtype=float,
    )
    monkeypatch.setattr(
        figure_strain_module,
        "read_image",
        lambda _path: (image, {}),
    )

    definitions = build_strain_figure_definitions(engine)
    evolution = next(
        item
        for item in definitions
        if item.figure_id == "saxs.strain.evolution.2d"
    )
    detector = next(
        item
        for item in evolution.data_sources
        if item.source_id == "detector-image-000"
    )

    assert detector.values["pixel_x"] == (0, 2, 1, 2)
    assert detector.values["pixel_y"] == (0, 0, 1, 1)
    assert all(np.isfinite(detector.values["log_intensity"]))
    assert len(detector.values["log_intensity"]) == 4


def test_dirty_detector_projection_records_sampled_pixel_provenance(monkeypatch) -> None:
    engine = _strain_engine()
    engine._file_list = ["sample-0.edf", "sample-1.edf"]
    image = np.asarray(
        [[1.0, np.nan, 10.0], [np.inf, 5.0, -2.0]],
        dtype=float,
    )
    monkeypatch.setattr(
        figure_strain_module,
        "read_image",
        lambda _path: (image, {}),
    )

    definition = next(
        item
        for item in build_strain_figure_definitions(engine)
        if item.figure_id == "saxs.strain.evolution.2d"
    )

    assert definition.recipe["parameters"]["detector_projection_quality"]["0"] == {
        "sampled_pixel_count": 6,
        "retained_pixel_count": 4,
        "nonfinite_pixel_count": 2,
        "status": "partial_nonfinite",
    }
    json.dumps(definition.recipe, allow_nan=False)


def test_clean_detector_projection_records_complete_provenance(monkeypatch) -> None:
    engine = _strain_engine()
    engine._file_list = ["sample-0.edf", "sample-1.edf"]
    monkeypatch.setattr(
        figure_strain_module,
        "read_image",
        lambda _path: (np.ones((2, 3), dtype=float), {}),
    )

    definition = next(
        item
        for item in build_strain_figure_definitions(engine)
        if item.figure_id == "saxs.strain.evolution.2d"
    )

    assert definition.recipe["parameters"]["detector_projection_quality"]["0"] == {
        "sampled_pixel_count": 6,
        "retained_pixel_count": 6,
        "nonfinite_pixel_count": 0,
        "status": "complete",
    }


def test_malformed_detector_projection_keeps_finite_sampled_pixels(monkeypatch) -> None:
    engine = _strain_engine()
    engine._file_list = ["sample-0.edf", "sample-1.edf"]
    image = np.asarray(
        [[1.0, "bad-pixel", 10.0], [np.inf, 5.0, -2.0]],
        dtype=object,
    )
    monkeypatch.setattr(
        figure_strain_module,
        "read_image",
        lambda _path: (image, {}),
    )

    definition = next(
        item
        for item in build_strain_figure_definitions(engine)
        if item.figure_id == "saxs.strain.evolution.2d"
    )
    detector = next(
        item
        for item in definition.data_sources
        if item.source_id == "detector-image-000"
    )

    assert detector.values["pixel_x"] == (0, 2, 1, 2)
    assert detector.values["pixel_y"] == (0, 0, 1, 1)
    assert definition.recipe["parameters"]["detector_projection_quality"]["0"] == {
        "sampled_pixel_count": 6,
        "retained_pixel_count": 4,
        "nonfinite_pixel_count": 2,
        "status": "partial_nonfinite",
    }


def test_dirty_azimuthal_projection_records_pair_provenance() -> None:
    engine = _strain_engine()
    engine._file_list = ["sample-0.edf", "sample-1.edf"]
    engine._batch_results[0].anisotropy = SimpleNamespace(
        azimuthal_chi=np.asarray([0.0, np.nan, 2.0]),
        azimuthal_I=np.asarray([1.0, 2.0, np.inf]),
    )

    definition = next(
        item
        for item in build_strain_figure_definitions(engine)
        if item.figure_id == "saxs.strain.azimuthal"
    )

    assert definition.recipe["parameters"]["azimuthal_projection_quality"]["0"] == {
        "input_pair_count": 3,
        "retained_pair_count": 1,
        "nonfinite_pair_count": 2,
        "status": "partial_nonfinite",
    }
    json.dumps(definition.recipe, allow_nan=False)


def test_malformed_azimuthal_projection_keeps_finite_pairs() -> None:
    engine = _strain_engine()
    engine._file_list = ["sample-0.edf", "sample-1.edf"]
    engine._batch_results[0].anisotropy = SimpleNamespace(
        azimuthal_chi=np.asarray([0.0, "bad-chi", 2.0], dtype=object),
        azimuthal_I=np.asarray([1.0, 2.0, "bad-intensity"], dtype=object),
    )

    definition = next(
        item
        for item in build_strain_figure_definitions(engine)
        if item.figure_id == "saxs.strain.azimuthal"
    )
    source = definition.data_sources[0]

    assert source.values["chi_rad"] == (0.0,)
    assert source.values["intensity"] == (1.0,)
    assert definition.recipe["parameters"]["azimuthal_projection_quality"]["0"] == {
        "input_pair_count": 3,
        "retained_pair_count": 1,
        "nonfinite_pair_count": 2,
        "status": "partial_nonfinite",
    }
    json.dumps(definition.recipe, allow_nan=False)


def test_clean_azimuthal_projection_records_complete_provenance() -> None:
    engine = _strain_engine()
    engine._file_list = ["sample-0.edf", "sample-1.edf"]
    engine._batch_results[0].anisotropy = SimpleNamespace(
        azimuthal_chi=np.asarray([0.0, 1.0, 2.0]),
        azimuthal_I=np.asarray([1.0, 2.0, 3.0]),
    )

    definition = next(
        item
        for item in build_strain_figure_definitions(engine)
        if item.figure_id == "saxs.strain.azimuthal"
    )

    assert definition.recipe["parameters"]["azimuthal_projection_quality"]["0"] == {
        "input_pair_count": 3,
        "retained_pair_count": 3,
        "nonfinite_pair_count": 0,
        "status": "complete",
    }
    json.dumps(definition.recipe, allow_nan=False)
