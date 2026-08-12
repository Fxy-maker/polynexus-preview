"""Contract tests for project-local agent workflow models."""

from __future__ import annotations

import json

import pytest

from polynexus.core.project_workflow.models import (
    AnalysisRequest,
    Condition,
    Formulation,
    Measurement,
    PreparationBatch,
    ProjectArtifact,
    ProjectFact,
    ResearchGraph,
    EvidenceItem,
    ProjectPlan,
)


def test_project_artifact_identity_is_stable_and_json_safe(tmp_path):
    artifact = ProjectArtifact.create(
        project_root=tmp_path,
        path=tmp_path / "raw" / "DSC_180.txt",
        technique="dsc",
        sha256="abc123",
        observed_facts={"setpoint_C": 180.0},
    )
    same = ProjectArtifact.create(
        project_root=tmp_path,
        path=tmp_path / "raw" / "DSC_180.txt",
        technique="dsc",
        sha256="abc123",
        observed_facts={"setpoint_C": 180.0},
    )
    assert artifact.artifact_id == same.artifact_id
    assert json.loads(json.dumps(artifact.to_dict()))["technique"] == "dsc"
    assert ProjectArtifact.from_dict(artifact.to_dict()).artifact_id == artifact.artifact_id

    blocked = ProjectArtifact.create(
        project_root=tmp_path,
        path=tmp_path / "raw" / "missing.txt",
        technique="dsc",
        sha256=None,
        inspection_status="blocked",
        reason_codes=("file_missing",),
    )
    assert blocked.sha256 is None
    assert blocked.inspection_status == "blocked"
    assert blocked.reason_codes == ("file_missing",)
    assert ProjectArtifact.from_dict(blocked.to_dict()).artifact_id == blocked.artifact_id

    changed_status = blocked.to_dict()
    changed_status["inspection_status"] = "ready"
    with pytest.raises(ValueError, match="artifact hash"):
        ProjectArtifact.from_dict(changed_status)

    missing_hash = artifact.to_dict()
    missing_hash.pop("artifact_id")
    with pytest.raises(ValueError, match="artifact hash"):
        ProjectArtifact.from_dict(missing_hash)

    changed_hash = artifact.to_dict()
    changed_hash["artifact_id"] = "tampered"
    with pytest.raises(ValueError, match="artifact hash"):
        ProjectArtifact.from_dict(changed_hash)


def test_raw_fact_wins_over_filename_label_and_records_discrepancy():
    fact = ProjectFact.from_sources(
        key="condition.setpoint_C",
        raw_value=185.0,
        filename_value=180.0,
    )
    assert fact.value == 185.0
    assert fact.status == "verified_from_raw"
    assert fact.discrepancies == ("filename_value_disagrees",)


def test_research_graph_supports_multiple_formulations_batches_and_measurements():
    graph = ResearchGraph.create(
        study_id="pa6-study",
        formulations=(Formulation("pa6", "PA6"), Formulation("blend", "PA6+additive")),
        batches=(PreparationBatch("b1", "pa6"), PreparationBatch("b2", "pa6")),
        conditions=(Condition("c180", "b1", {"temperature_C": 180.0}),),
        measurements=(
            Measurement("m-dsc", "c180", "dsc", artifact_ids=("artifact-1", "background-1")),
        ),
    )
    assert len(graph.formulations) == 2
    assert graph.measurements[0].artifact_ids == ("artifact-1", "background-1")
    assert graph.measurements[0].artifact_id == "artifact-1"

    payload = graph.to_dict()
    assert ResearchGraph.from_dict(payload).graph_hash == graph.graph_hash
    payload.pop("graph_hash")
    with pytest.raises(ValueError, match="graph hash"):
        ResearchGraph.from_dict(payload)


def test_analysis_request_round_trips_and_has_content_hash():
    request = AnalysisRequest.create(
        question="Compare 180-185 C kinetics",
        purpose="results_support",
        requested_outputs=("avrami_parameter_table",),
    )
    assert AnalysisRequest.from_dict(request.to_dict()).request_hash == request.request_hash
    missing_hash = request.to_dict()
    missing_hash.pop("request_hash")
    with pytest.raises(ValueError, match="request hash"):
        AnalysisRequest.from_dict(missing_hash)


def test_plan_and_evidence_hashes_are_required_and_verified():
    plan = ProjectPlan.create(request_hash="request-hash", steps=({"technique": "dsc"},))
    assert ProjectPlan.from_dict(plan.to_dict()).plan_hash == plan.plan_hash
    plan_payload = plan.to_dict()
    plan_payload.pop("plan_hash")
    with pytest.raises(ValueError, match="plan hash"):
        ProjectPlan.from_dict(plan_payload)

    item = EvidenceItem.create(
        evidence_id="dsc-1",
        kind="quantitative_result",
        technique="dsc",
        claim_scope="kinetics",
    )
    assert EvidenceItem.from_dict(item.to_dict()).item_hash == item.item_hash
    item_payload = item.to_dict()
    item_payload.pop("item_hash")
    with pytest.raises(ValueError, match="evidence hash"):
        EvidenceItem.from_dict(item_payload)
