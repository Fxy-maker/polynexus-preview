from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from polynexus.core.agent_workflow import AgentWorkflowService
from polynexus.core.engine import AnalysisResult
from polynexus.core.project_workflow.adapters import SingleInputTechniqueAdapter, TechniqueSeriesAdapter
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
    assert proposal.recipe.steps[0].parameters["canonical_converter"] == "raw-file-envelope.waxs.v1"
    assert proposal.recipe.steps[0].parameters["canonical_template"]["template_id"] == "waxs.profile.v1"
    assert proposal.recipe.steps[0].parameters["canonical_template"]["source_artifact_id"] == proposal.recipe.artifacts[0].artifact_id


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


def test_single_recipe_without_canonical_template_is_invalid(tmp_path: Path) -> None:
    source = _source(tmp_path, "waxs")
    proposal = SingleInputTechniqueAdapter().propose_recipe({
        "workflow_id": "project.technique.single.v1",
        "technique": "waxs",
        "path": str(source),
    })

    assert proposal.recipe is not None
    step = proposal.recipe.steps[0]
    invalid = replace(
        proposal.recipe,
        steps=(replace(step, parameters={"submodule_id": "waxs.static"}),),
    )

    run = AgentWorkflowService().run_recipe(invalid, tmp_path / "derived")

    assert run.status == "blocked"
    assert run.reason_codes == ("recipe_invalid",)


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


def test_ir_directory_alias_is_indexed_as_ir_and_stale_source_blocks_run(tmp_path: Path) -> None:
    source = tmp_path / "raw" / "IR" / "series"
    source.mkdir(parents=True)
    (source / "20C.csv").write_text("wavenumber,intensity\n1000,1\n", encoding="utf-8")
    service = ProjectWorkflowService.open(tmp_path)
    graph = service.inspect((source,))
    assert graph.artifacts[0].technique == "ir"
    plan = service.plan(AnalysisRequest.create(
        question="Analyze IR",
        data_scope=(source.relative_to(tmp_path).as_posix(),),
    ))
    (source / "20C.csv").write_text("wavenumber,intensity\n1000,2\n", encoding="utf-8")
    result = service.run(plan)
    assert result.status == "blocked"
    assert "source_hash_changed" in result.reason_codes


def test_series_adapter_orders_paths_and_binds_each_step(tmp_path: Path) -> None:
    paths = [_source(tmp_path, "waxs", name) for name in ("b.dat", "a.dat")]
    adapter = TechniqueSeriesAdapter()
    proposal = adapter.propose_recipe({
        "workflow_id": adapter.workflow_id,
        "technique": "waxs",
        "paths": [str(path) for path in paths],
    })

    assert proposal.status == "ready"
    assert proposal.recipe is not None
    assert [step.parameters["artifact_index"] for step in proposal.recipe.steps] == [0, 1]
    assert [Path(item.path).name for item in proposal.recipe.artifacts] == ["a.dat", "b.dat"]
    assert all(step.parameters["canonical_converter"] == "raw-file-envelope.waxs.v1" for step in proposal.recipe.steps)
    assert all(step.parameters["canonical_template"]["template_id"] == "waxs.profile.v1" for step in proposal.recipe.steps)
    assert TechniqueSeriesAdapter.is_valid_recipe(proposal.recipe)


def test_series_adapter_requires_at_least_two_same_technique_inputs(tmp_path: Path) -> None:
    adapter = TechniqueSeriesAdapter()
    one = adapter.propose_recipe({
        "workflow_id": adapter.workflow_id,
        "technique": "saxs",
        "paths": [str(_source(tmp_path, "saxs", "a.dat"))],
    })
    mixed = adapter.propose_recipe({
        "workflow_id": adapter.workflow_id,
        "technique": "saxs",
        "paths": [str(_source(tmp_path, "saxs", "a.dat")), str(_source(tmp_path, "ir", "b.dat"))],
    })

    assert one.status == "blocked"
    assert one.reason_codes == ("series_requires_multiple_artifacts",)
    assert mixed.status == "blocked"
    assert mixed.reason_codes == ("series_technique_mismatch",)


def test_project_series_run_binds_each_file_in_stable_order(tmp_path: Path) -> None:
    paths = [_source(tmp_path, "waxs", name) for name in ("b.dat", "a.dat")]
    calls: list[str] = []

    def provider(step, artifact, output_dir):
        calls.append(Path(artifact.path).name)
        return AnalysisResult(technique=step.technique, validation_passed=True)

    service = ProjectWorkflowService.open(tmp_path)
    service.agent_service = AgentWorkflowService(provider_runner=provider)
    service.inspect(paths)
    result = service.run(AnalysisRequest.create(question="Analyze WAXS series", data_scope=("raw/WAXS",)))

    assert result.status == "review_required"
    assert calls == ["a.dat", "b.dat"]
    assert result.analysis_run is not None
    assert [step.parameters["artifact_index"] for step in result.analysis_run.recipe.steps] == [0, 1]
