"""Contract tests for project-local agent workflow models."""

from __future__ import annotations

import json

from polynexus.core.project_workflow.models import (
    AnalysisRequest,
    Condition,
    Formulation,
    Measurement,
    PreparationBatch,
    ProjectArtifact,
    ProjectFact,
    ResearchGraph,
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
        measurements=(Measurement("m-dsc", "c180", "dsc", "artifact-1"),),
    )
    assert len(graph.formulations) == 2
    assert graph.measurements[0].artifact_id == "artifact-1"


def test_analysis_request_round_trips_and_has_content_hash():
    request = AnalysisRequest.create(
        question="Compare 180-185 C kinetics",
        purpose="results_support",
        requested_outputs=("avrami_parameter_table",),
    )
    assert AnalysisRequest.from_dict(request.to_dict()).request_hash == request.request_hash
