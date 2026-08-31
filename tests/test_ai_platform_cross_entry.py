"""Focused producer/consumer checks for the shared AI-platform projections."""

from __future__ import annotations

import math
from pathlib import Path
from types import MappingProxyType

import pytest

from polynexus.cli.batch_run_service import _persist_batch_run
from polynexus.core.agent_workflow.evidence import build_evidence
from polynexus.core.agent_workflow import AgentWorkflowService
from polynexus.core.agent_workflow.models import WorkflowStepResult
from polynexus.core.ai_platform.contracts import ComputationState
from polynexus.core.compute import ComputeRun
from polynexus.core.compute.models import AnalysisPlan, CanonicalDataset, ComputeResult, RawArtifact
from polynexus.core.joint.dataset import JointRunRecord
from polynexus.core.project_workflow.evidence import ProjectWorkflowRun
from polynexus.core.project_workflow.result_table import build_result_tables_from_runs
from polynexus.core.project_workflow.writing_metrics import extract_writing_metrics
from polynexus.core.agent_workflow.models import AnalysisRecipe, AnalysisRun
from polynexus.data.sample_db import SampleDB
from polynexus.gui.analysis_run_service import (
    AnalysisRunPersistenceContext,
    persist_analysis_run,
)


_HASH = "a" * 64


def _completed_run(tmp_path: Path, *, result: ComputeResult | None = None) -> ComputeRun:
    source = tmp_path / "sample.csv"
    source.write_text("x,y\n1,2\n", encoding="utf-8")

    if result is None:
        result = ComputeResult(metrics={"Xc_pct": 42.0})
    artifact = RawArtifact.from_path(source, technique="ir")
    dataset = CanonicalDataset.direct_envelope(artifact)
    plan = AnalysisPlan.direct(dataset, output_dir=tmp_path / "out")
    return ComputeRun.completed(
        artifact=artifact,
        dataset=dataset,
        plan=plan,
        result=result,
    )


def _state(*, computability: str = "computed") -> ComputationState:
    return ComputationState.create(
        data_availability="canonical",
        computability=computability,
        validity="validated" if computability == "computed" else "not_assessed",
        promotion="results_candidate" if computability == "computed" else "diagnostic_only",
        reason_codes=("explicit_test_state",),
    )


def test_compute_metric_manifest_carries_descriptor_state_provenance_and_uncertainty(
    tmp_path: Path,
) -> None:
    state = _state()
    result = ComputeResult(
        metrics={"Tm_C": 180.0},
        metadata={"units": {"Tm_C": "degC"}, "methods": {"Tm_C": "peak"}},
        descriptor_id="dsc.Tm.v1",
        computation_state=state,
        provenance={"source_artifact_id": "artifact-1", "algorithm": "peak.v2"},
        uncertainty={"Tm_C": {"kind": "std", "value": 1.5}},
    )
    run = _completed_run(tmp_path, result=result)

    row = run.to_dict()["result"]["metric_manifest"][0]

    assert row["descriptor_id"] == "dsc.Tm.v1"
    assert row["computation_state"] == state.to_dict()
    assert row["provenance"]["source_artifact_id"] == "artifact-1"
    assert row["uncertainty"] == {"kind": "std", "value": 1.5}
    assert row["unit"] == "degC"
    assert row["value"] == 180.0


def test_workflow_step_roundtrip_preserves_four_axis_state_and_descriptor() -> None:
    state = _state()
    step = WorkflowStepResult(
        step_id="tm",
        technique="dsc",
        status="completed",
        result_summary={"Tm_C": 180.0},
        computation_state=state,
        descriptor_id="dsc.Tm.v1",
    )

    restored = WorkflowStepResult.from_dict(step.to_dict())

    assert restored.computation_state == state
    assert restored.descriptor_id == "dsc.Tm.v1"
    assert restored.to_dict()["computation_state"] == state.to_dict()


def test_agent_shared_compute_projection_mirrors_state_at_step_summary(tmp_path: Path) -> None:
    run = _completed_run(
        tmp_path,
        result=ComputeResult(
            metrics={"Tm_C": 180.0},
            descriptor_id="dsc.Tm.v1",
            computation_state=_state(),
            provenance={"algorithm": "peak.v2"},
            uncertainty={"Tm_C": {"kind": "std", "value": 1.5}},
        ),
    )

    # The static adapter is intentionally exercised directly: it is the same
    # projection used by run_recipe and does not invoke a provider.
    step = AgentWorkflowService._public_step_result("tm", "dsc", None, compute_run=run)

    assert step.result_summary["descriptor_id"] == "dsc.Tm.v1"
    assert step.to_dict()["computation_state"] == _state().to_dict()
    assert step.result_summary["provenance"] == {"algorithm": "peak.v2"}
    assert step.result_summary["uncertainty"] == {"Tm_C": {"kind": "std", "value": 1.5}}


def test_needs_input_state_is_retained_but_not_promoted_to_agent_evidence() -> None:
    artifact = RawArtifact.missing("missing.csv", technique="dsc")
    state = _state(computability="needs_input")
    step = WorkflowStepResult(
        step_id="tm",
        technique="dsc",
        status="blocked",
        result_summary={},
        computation_state=state,
        descriptor_id="dsc.Tm.v1",
        compute_run={
            "status": "needs_input",
            "artifact": {
                "artifact_id": artifact.artifact_id,
                "path": artifact.path,
                "technique": artifact.technique,
                "format": artifact.format,
                "sha256": artifact.sha256,
            },
            "computation_state": state.to_dict(),
        },
    )

    evidence = build_evidence((step,))

    assert step.computation_state.computability == "needs_input"
    assert evidence.observed == ()


def test_agent_needs_input_projection_keeps_compute_reasons_on_step() -> None:
    artifact = RawArtifact.missing("missing.csv", technique="dsc")
    state = _state(computability="needs_input")
    run = ComputeRun(
        status="needs_input",
        artifact=artifact,
        reasons=("calibration_missing", "mapping_required"),
        computation_state=state,
        descriptor_id="dsc.Tm.v1",
    )

    step = AgentWorkflowService._public_step_result(
        "tm", "dsc", None, compute_run=run
    )

    assert step.status == "blocked"
    assert step.reason_codes == ("calibration_missing", "mapping_required")
    assert step.to_dict()["result_summary"]["compute_run"]["reasons"] == [
        "calibration_missing",
        "mapping_required",
    ]
    assert step.to_dict()["computation_state"] == state.to_dict()


def test_gui_persistence_embeds_needs_input_compute_run_without_completed_promotion(
    tmp_path: Path,
) -> None:
    db = SampleDB(tmp_path / "samples.db")
    try:
        artifact = RawArtifact.missing(tmp_path / "missing.csv", technique="dsc")
        state = _state(computability="needs_input")
        run = ComputeRun(
            status="needs_input",
            artifact=artifact,
            reasons=("calibration_missing",),
            computation_state=state,
            descriptor_id="dsc.Tm.v1",
        )
        run_id = persist_analysis_run(
            db,
            None,
            AnalysisRunPersistenceContext(
                technique="dsc",
                data_file=str(tmp_path / "missing.csv"),
                compute_run=run,
            ),
        )

        summary = db.get_analysis_run(run_id)["results_summary"]
        assert summary["compute_run"]["status"] == "needs_input"
        assert summary["compute_run"]["computation_state"] == state.to_dict()
        assert summary["status"] == "needs_input"
        assert db.get_analysis_run(run_id)["analysis_evidence"] == {}
    finally:
        db.close()


def test_cli_batch_persistence_keeps_nested_compute_run_metric_manifest(tmp_path: Path) -> None:
    db_path = tmp_path / "samples.db"
    # _persist_batch_run creates its own default SampleDB.  Patch the class at
    # the module boundary so the test remains isolated and deterministic.
    import polynexus.data.sample_db as sample_db_module

    original = sample_db_module.SampleDB
    sample_db_module.SampleDB = lambda: SampleDB(db_path)
    try:
        run = _completed_run(
            tmp_path,
            result=ComputeResult(
                metrics={"Xc_pct": 42.0},
                descriptor_id="ir.Xc.v1",
                computation_state=_state(),
                provenance={"source": "instrument"},
                uncertainty={"Xc_pct": {"kind": "std", "value": 0.5}},
            ),
        )
        _persist_batch_run(str(tmp_path / "sample.csv"), "ir", run, 0.25)
        db = SampleDB(db_path)
        try:
            samples = db.list_samples(limit=10)
            batch = db.get_batches(samples[0]["id"])[0]
            summary = db.get_analysis_runs(batch["id"])[0]["results_summary"]
        finally:
            db.close()
    finally:
        sample_db_module.SampleDB = original

    manifest = summary["compute_run"]["result"]["metric_manifest"]
    assert manifest[0]["descriptor_id"] == "ir.Xc.v1"
    assert summary["metric_source"] == "shared_compute_run"
    assert summary["compatibility_only"] is False


def test_cli_batch_persistence_accepts_serialized_compute_run_projection(tmp_path: Path) -> None:
    db_path = tmp_path / "serialized-samples.db"
    import polynexus.data.sample_db as sample_db_module

    original = sample_db_module.SampleDB
    sample_db_module.SampleDB = lambda: SampleDB(db_path)
    try:
        run = _completed_run(
            tmp_path,
            result=ComputeResult(
                metrics={"Xc_pct": 37.0},
                descriptor_id="ir.Xc.v1",
                computation_state=_state(),
            ),
        )
        _persist_batch_run(str(tmp_path / "sample.csv"), "ir", run.to_dict(), 0.5)
        db = SampleDB(db_path)
        try:
            samples = db.list_samples(limit=10)
            batch = db.get_batches(samples[0]["id"])[0]
            summary = db.get_analysis_runs(batch["id"])[0]["results_summary"]
        finally:
            db.close()
    finally:
        sample_db_module.SampleDB = original

    assert summary["compute_run"]["status"] == "completed"
    assert summary["compute_run"]["result"]["metric_manifest"][0]["value"] == 37.0
    assert summary["metric_source"] == "shared_compute_run"
    assert summary["compatibility_only"] is False


def test_joint_prefers_shared_metric_manifest_and_labels_legacy_fallback() -> None:
    shared = JointRunRecord(
        run_id="run-shared",
        technique="dsc",
        parameters={},
        results_summary={
            "Xc_pct": 10.0,
            "compute_run": {
                "status": "completed",
                "computation_state": _state().to_dict(),
                "result": {
                    "metric_manifest": [
                        {
                            "path": "Xc_pct",
                            "value": 42.0,
                            "status": "computed",
                            "descriptor_id": "dsc.Xc.v1",
                        }
                    ]
                },
            },
        },
    )
    legacy = JointRunRecord(
        run_id="run-legacy",
        technique="dsc",
        results_summary={"Xc_pct": 10.0},
    )

    assert shared.get_first_number(("Xc_pct",)) == 42.0
    assert shared.metric_source == "shared_compute_run"
    assert shared.compatibility_only is False
    assert legacy.get_first_number(("Xc_pct",)) == 10.0
    assert legacy.metric_source == "legacy_results_summary"
    assert legacy.compatibility_only is True


def test_joint_accepts_mapping_shared_projection_and_metrics_fallback() -> None:
    # A consumer may receive an immutable mapping directly from a frozen
    # contract rather than the JSON dict emitted by ComputeRun.to_dict().
    shared_projection = MappingProxyType(
        {
            "status": "completed",
            "computation_state": MappingProxyType(_state().to_dict()),
            "result": MappingProxyType(
                {
                    "metrics": MappingProxyType({"Xc_pct": 42.0}),
                    "metric_manifest": (
                        MappingProxyType(
                            {
                                "path": "Xc_pct",
                                "value": 42.0,
                                "status": "computed",
                            }
                        ),
                    ),
                }
            ),
        }
    )
    shared = JointRunRecord(
        run_id="run-mapping",
        technique="dsc",
        results_summary={"Xc_pct": 10.0, "compute_run": shared_projection},
    )

    assert shared.metric_source == "shared_compute_run"
    assert shared.compatibility_only is False
    assert shared.get_first_number(("Xc_pct",)) == 42.0

    # If a minimal shared projection has metrics but no manifest, its values
    # are still canonical shared output; legacy summaries must not shadow it.
    metrics_only = JointRunRecord(
        run_id="run-metrics-only",
        technique="dsc",
        results_summary={
            "Xc_pct": 10.0,
            "compute_run": {
                "status": "completed",
                "computation_state": _state().to_dict(),
                "result": {"metrics": {"Xc_pct": 42.0}},
            },
        },
    )
    assert metrics_only.metric_source == "shared_compute_run"
    assert metrics_only.compatibility_only is False
    assert metrics_only.get_first_number(("Xc_pct",)) == 42.0


def test_joint_does_not_read_needs_input_manifest_values() -> None:
    run = JointRunRecord(
        run_id="run-blocked",
        technique="dsc",
        results_summary={
            "compute_run": {
                "status": "needs_input",
                "result": {
                    "metric_manifest": [
                        {
                            "path": "Xc_pct",
                            "value": 99.0,
                            "status": "needs_input",
                            "computation_state": _state(computability="needs_input").to_dict(),
                        }
                    ]
                },
            }
        },
    )

    assert math.isnan(run.get_first_number(("Xc_pct",)))


def test_malformed_shared_manifest_row_is_not_promoted_to_joint_or_agent_evidence() -> None:
    compute_run = {
        "status": "completed",
        "computation_state": _state().to_dict(),
        "result": {
            "metric_manifest": [
                {"path": "forged", "kind": "scalar", "value": 999.0}
            ]
        },
    }
    joint = JointRunRecord(
        run_id="run-forged",
        technique="dsc",
        results_summary={"compute_run": compute_run},
    )
    step = WorkflowStepResult(
        step_id="forged-step",
        technique="dsc",
        status="completed",
        result_summary={"compute_run": compute_run},
    )

    assert joint.values == {}
    assert build_evidence((step,)).observed == ()


def test_manifest_metrics_mismatch_is_not_consumed_by_joint_or_writing() -> None:
    compute_run = {
        "status": "completed",
        "computation_state": _state().to_dict(),
        "result": {
            "metrics": {"forged": 1.0},
            "metric_manifest": [
                {
                    "path": "forged",
                    "kind": "scalar",
                    "status": "computed",
                    "value": 999.0,
                }
            ],
        },
    }
    joint = JointRunRecord(
        run_id="run-mismatch",
        technique="dsc",
        results_summary={"compute_run": compute_run},
    )
    writing = extract_writing_metrics(
        {
            "technique": "dsc",
            "result_summary": {"compute_run": compute_run},
        }
    )

    assert joint.values == {}
    assert writing == ()


def test_joint_does_not_fallback_to_legacy_values_when_shared_run_is_blocked() -> None:
    run = JointRunRecord(
        run_id="run-blocked-legacy",
        technique="dsc",
        results_summary={
            "Xc_pct": 77.0,
            "compute_run": {
                "status": "needs_input",
                "artifact": {"artifact_id": "a"},
            },
        },
    )

    assert run.metric_source == "shared_compute_run"
    assert run.compatibility_only is False
    assert math.isnan(run.get_first_number(("Xc_pct",)))


def test_agent_evidence_rejects_nested_noncomputed_run_without_top_level_state() -> None:
    """A serialized step may carry state only inside its shared run envelope."""

    step = WorkflowStepResult(
        step_id="blocked-step",
        technique="dsc",
        status="review_required",
        result_summary={
            "compute_run": {
                "status": "needs_input",
                "artifact": {"artifact_id": "a"},
            }
        },
        compute_run={
            "status": "needs_input",
            "artifact": {"artifact_id": "a"},
        },
    )

    evidence = build_evidence((step,))

    assert evidence.observed == ()


def test_result_tables_reject_noncompleted_shared_run_even_when_manifest_row_looks_computed() -> None:
    """Run status is an independent gate and cannot be replaced by row status."""

    step = WorkflowStepResult(
        step_id="blocked-step",
        technique="dsc",
        status="blocked",
        result_summary={},
        compute_run={
            "status": "needs_input",
            "artifact": {"path": "missing.csv"},
            "result": {
                "metric_manifest": [
                    {
                        "path": "Xc_pct",
                        "kind": "scalar",
                        "status": "computed",
                        "value": 99.0,
                    }
                ]
            },
        },
    )
    analysis = AnalysisRun(
        recipe=AnalysisRecipe.create(workflow_id="recipe", artifacts=(), steps=()),
        status="blocked",
        steps=(step,),
    )
    run = ProjectWorkflowRun(
        run_id="run-blocked",
        request_hash="a" * 64,
        plan_hash="b" * 64,
        recipe_hash=None,
        status="blocked",
        analysis_run=analysis,
    )

    assert build_result_tables_from_runs((run,)) == ()


def test_completed_compute_run_rejects_noncomputed_shared_state(tmp_path: Path) -> None:
    """The run envelope and four-axis state must not advertise contradictions."""

    source = tmp_path / "sample.csv"
    source.write_text("x,y\n1,2\n", encoding="utf-8")
    artifact = RawArtifact.from_path(source, technique="ir")
    dataset = CanonicalDataset.direct_envelope(artifact)
    plan = AnalysisPlan.direct(dataset, output_dir=tmp_path / "out")
    result = ComputeResult(metrics={"Xc_pct": 42.0})

    with pytest.raises(ValueError, match="status.*computation_state|completed.*computed"):
        ComputeRun.completed(
            artifact=artifact,
            dataset=dataset,
            plan=plan,
            result=result,
            computation_state=_state(computability="needs_input"),
        )
