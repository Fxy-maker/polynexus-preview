from __future__ import annotations

from pathlib import Path

from polynexus.core.agent_workflow import (
    AgentWorkflowService,
    AnalysisRecipe,
    RecipeStep,
    inspect_artifact,
)
from polynexus.core.agent_workflow.registry import WorkflowRegistry
from polynexus.core.engine import AnalysisResult
from polynexus.core.compute.models import RawArtifact


class _Adapter:
    workflow_id = "test.directory"

    @staticmethod
    def is_valid_recipe(recipe: AnalysisRecipe) -> bool:
        return recipe.workflow_id == "test.directory"


def _recipe(source: Path, technique: str) -> AnalysisRecipe:
    artifact = inspect_artifact(source, technique=technique)
    return AnalysisRecipe.create(
        workflow_id="test.directory",
        artifacts=(artifact,),
        steps=(RecipeStep(step_id=f"{technique}_directory", technique=technique),),
    )


def _service(calls: list[str]) -> AgentWorkflowService:
    registry = _registry()

    def provider(step, _artifact, _output_dir):
        calls.append(step.technique)
        return AnalysisResult(technique=step.technique, validation_passed=True)

    return AgentWorkflowService(registry=registry, provider_runner=provider)


def _registry() -> WorkflowRegistry:
    registry = WorkflowRegistry()
    registry.register(_Adapter())
    return registry


def test_non_dsc_directory_workflow_exposes_shared_compute_run(tmp_path: Path) -> None:
    source = tmp_path / "ir-series"
    source.mkdir()
    (source / "20C.csv").write_text("wavenumber,intensity\n1000,1\n1100,2\n", encoding="utf-8")
    calls: list[str] = []

    run = _service(calls).run_recipe(_recipe(source, "ir"), tmp_path / "derived")

    assert run.status == "review_required"
    assert calls == ["ir"]
    step = run.steps[0]
    assert step.compute_run is not None
    assert step.compute_run["status"] == "completed"
    assert step.compute_run["canonical_template"]["template_id"] == "ir.spectrum.v1"


def test_dsc_directory_workflow_keeps_provider_compatibility_boundary(tmp_path: Path) -> None:
    source = tmp_path / "dsc-series"
    source.mkdir()
    (source / "run-1.csv").write_text("time,heat\n0,0\n1,1\n", encoding="utf-8")
    calls: list[str] = []

    run = _service(calls).run_recipe(_recipe(source, "dsc"), tmp_path / "derived")

    assert run.status == "completed"
    assert calls == ["dsc"]
    assert run.steps[0].compute_run is None


def test_default_directory_engine_uses_shared_compute_run_once(tmp_path: Path) -> None:
    source = tmp_path / "saxs-series"
    source.mkdir()
    (source / "frame-001.edf").write_bytes(b"detector")
    calls: list[tuple[str, str]] = []

    class _Engine:
        def run_pipeline(self, path: str, output_dir: str, **_options):
            calls.append((path, output_dir))
            return AnalysisResult(technique="saxs", validation_passed=True)

    run = AgentWorkflowService(
        registry=_registry(),
        get_engine_fn=lambda _technique: _Engine(),
    ).run_recipe(_recipe(source, "saxs"), tmp_path / "derived")

    assert run.status == "review_required"
    assert len(calls) == 1
    assert run.steps[0].compute_run["canonical_template"]["template_id"] == "saxs.profile.v1"


def test_directory_artifact_identity_matches_compute_run_identity(tmp_path: Path) -> None:
    source = tmp_path / "ir-series"
    source.mkdir()
    (source / "20C.csv").write_text("wavenumber,intensity\n1000,1\n", encoding="utf-8")

    inspected = inspect_artifact(source, technique="ir")
    direct = RawArtifact.from_path(source, technique="ir")

    assert inspected.sha256 == direct.sha256
    assert inspected.artifact_id == direct.artifact_id
