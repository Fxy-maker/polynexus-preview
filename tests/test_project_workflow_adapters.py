from __future__ import annotations

from pathlib import Path

from polynexus.core.agent_workflow import AgentWorkflowService
from polynexus.core.engine import AnalysisResult
from polynexus.core.project_workflow.adapters import SingleInputTechniqueAdapter
from polynexus.core.project_workflow.models import AnalysisRequest
from polynexus.core.project_workflow.service import ProjectWorkflowService


def _source(tmp_path: Path, technique: str, name: str = "sample.csv") -> Path:
    path = tmp_path / "raw" / technique.upper() / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("q,I\n0.1,1\n0.2,2\n", encoding="utf-8")
    return path


def test_single_input_adapter_proposes_registered_static_recipe(tmp_path: Path) -> None:
    source = _source(tmp_path, "waxs")
    proposal = SingleInputTechniqueAdapter().propose_recipe({
        "workflow_id": "project.technique.single.v1",
        "technique": "waxs",
        "path": str(source),
    })

    assert proposal.status == "ready"
    assert proposal.recipe is not None
    assert proposal.recipe.workflow_id == "project.technique.single.v1"
    assert proposal.recipe.steps[0].step_id == "waxs_profile"
    assert proposal.recipe.steps[0].parameters["submodule_id"] == "waxs.static"


def test_single_input_adapter_blocks_unsupported_and_multiple_inputs(tmp_path: Path) -> None:
    adapter = SingleInputTechniqueAdapter()
    unsupported = adapter.propose_recipe({
        "workflow_id": adapter.workflow_id,
        "technique": "nmr",
        "path": str(_source(tmp_path, "nmr", "sample.dat")),
    })
    multiple = adapter.propose_recipe({
        "workflow_id": adapter.workflow_id,
        "technique": "saxs",
        "paths": [str(_source(tmp_path, "saxs", "a.dat")), str(_source(tmp_path, "saxs", "b.dat"))],
    })

    assert unsupported.status == "blocked"
    assert unsupported.reason_codes == ("technique_unsupported",)
    assert multiple.status == "blocked"
    assert multiple.reason_codes == ("multiple_artifacts",)


def test_project_plan_uses_single_input_adapter_for_waxs(tmp_path: Path) -> None:
    source = _source(tmp_path, "waxs")
    service = ProjectWorkflowService.open(tmp_path)
    service.inspect((source,))
    plan = service.plan(AnalysisRequest.create(
        question="Analyze WAXS profile",
        data_scope=(source.relative_to(tmp_path).as_posix(),),
    ))

    assert plan.status == "ready"
    assert plan.reason_codes == ()
    assert plan.steps[0]["provider_id"] == "project.technique.single.v1"
    assert plan.steps[0]["template_id"] == "waxs.static"


def test_project_run_delegates_single_waxs_input_to_existing_service(tmp_path: Path) -> None:
    source = _source(tmp_path, "waxs")
    calls: list[str] = []

    def provider(step, artifact, output_dir):
        calls.append(step.technique)
        return AnalysisResult(technique=step.technique, validation_passed=True)

    agent = AgentWorkflowService(provider_runner=provider)
    service = ProjectWorkflowService.open(tmp_path)
    service.agent_service = agent
    service.inspect((source,))
    result = service.run(AnalysisRequest.create(
        question="Analyze WAXS profile",
        data_scope=(source.relative_to(tmp_path).as_posix(),),
    ))

    assert result.status == "review_required"
    assert calls == ["waxs"]
    assert result.evidence_items[0].technique == "waxs"
    assert result.analysis_run is not None
    assert result.analysis_run.recipe.steps[0].parameters["submodule_id"] == "waxs.static"
