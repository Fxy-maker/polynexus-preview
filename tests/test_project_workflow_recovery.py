from __future__ import annotations

from pathlib import Path

import pytest

from polynexus.core.project_workflow import AnalysisPlan, AnalysisRequest, ProjectWorkflowService
from polynexus.core.agent_workflow import AgentWorkflowService
from polynexus.core.engine import AnalysisResult


def _source(tmp_path: Path) -> Path:
    path = tmp_path / "raw" / "WAXS" / "sample.csv"
    path.parent.mkdir(parents=True)
    path.write_text("q,I\n0.1,1\n0.2,2\n", encoding="utf-8")
    return path


def test_resume_replays_persisted_request_and_plan(tmp_path: Path) -> None:
    source = _source(tmp_path)
    service = ProjectWorkflowService.open(tmp_path)
    service.agent_service = AgentWorkflowService(provider_runner=lambda step, artifact, output: AnalysisResult(technique=step.technique, validation_passed=True))
    request = AnalysisRequest.create(question="Analyze WAXS", data_scope=(source.relative_to(tmp_path).as_posix(),))
    first = service.run(request)
    resumed = service.resume(first.run_id)

    assert resumed.status == "review_required"
    assert resumed.request_hash == first.request_hash
    assert resumed.recipe_hash == first.recipe_hash


def test_resume_blocks_when_source_changed(tmp_path: Path) -> None:
    source = _source(tmp_path)
    service = ProjectWorkflowService.open(tmp_path)
    service.agent_service = AgentWorkflowService(provider_runner=lambda step, artifact, output: AnalysisResult(technique=step.technique, validation_passed=True))
    first = service.run(AnalysisRequest.create(question="Analyze WAXS", data_scope=(source.relative_to(tmp_path).as_posix(),)))
    source.write_text("q,I\n0.1,9\n", encoding="utf-8")

    resumed = service.resume(first.run_id)

    assert resumed.status == "blocked"
    assert "source_hash_changed" in resumed.reason_codes


def test_approved_context_correction_is_new_request_metadata(tmp_path: Path) -> None:
    service = ProjectWorkflowService.open(tmp_path)
    request = AnalysisRequest.create(question="Analyze WAXS")
    corrected = service.approve_context_correction(
        request,
        {"sample_id": "PA6-A", "temperature_C": 180},
        approved=True,
        approver="Codex/user",
    )

    assert corrected.request_hash != request.request_hash
    assert corrected.parameters["approved_context_corrections"]["sample_id"] == "PA6-A"
    assert corrected.parameters["approved_context_approver"] == "Codex/user"
    assert corrected.parameters["approved_context_corrections_status"] == "approved"
    assert "sample_id" not in request.parameters


def test_context_correction_requires_explicit_approval(tmp_path: Path) -> None:
    service = ProjectWorkflowService.open(tmp_path)
    with pytest.raises(ValueError, match="approval"):
        service.approve_context_correction(AnalysisRequest.create(question="x"), {"sample_id": "PA6"})


def test_frozen_analysis_plan_replays_without_ai_and_blocks_changed_source(tmp_path: Path) -> None:
    source = _source(tmp_path)
    service = ProjectWorkflowService.open(tmp_path)
    service.agent_service = AgentWorkflowService(provider_runner=lambda step, artifact, output: AnalysisResult(technique=step.technique, validation_passed=True))
    request = AnalysisRequest.create(question="Analyze WAXS", data_scope=(source.relative_to(tmp_path).as_posix(),))
    service.run(request)
    plan = AnalysisPlan.create(
        request_hash=request.request_hash,
        source_files=({"path": source.relative_to(tmp_path).as_posix(), "sha256": __import__("hashlib").sha256(source.read_bytes()).hexdigest()},),
        scope={"technique": "waxs"},
        canonical_template={"template_id": "waxs.v1", "conversion_version": "conv-1"},
        algorithm={"algorithm_id": "waxs.provider", "algorithm_version": "1"},
    )
    service.freeze_analysis_plan(plan, request=request)
    replayed = service.replay_analysis_plan(plan.plan_id)
    assert replayed.status == "review_required"
    source.write_text("q,I\n0.1,9\n", encoding="utf-8")
    blocked = service.replay_analysis_plan(plan.plan_id)
    assert blocked.status == "blocked"
    assert "analysis_plan_source_hash_changed" in blocked.reason_codes


def test_replan_creates_new_lineage_and_preserves_original_plan(tmp_path: Path) -> None:
    service = ProjectWorkflowService.open(tmp_path)
    plan = AnalysisPlan.create(
        source_files=({"path": "raw/a.csv", "sha256": "a" * 64},),
        canonical_template={"template_id": "waxs.v1", "conversion_version": "conv-1"},
        algorithm={"algorithm_id": "waxs.provider", "algorithm_version": "1"},
    )
    revised = service.replan_analysis(
        plan,
        ai_context={"provider": "codex", "model_version": "test", "input_hash": "i" * 64, "output_hash": "o" * 64, "decision_hash": "d" * 64},
        default_config={"smoothing": "bounded"},
    )
    assert revised.plan_id != plan.plan_id
    assert revised.replan_of == plan.plan_id
    assert plan.default_config == {}
