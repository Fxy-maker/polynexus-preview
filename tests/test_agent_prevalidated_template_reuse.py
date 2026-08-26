from __future__ import annotations

from pathlib import Path
import pytest

from polynexus.core.canonical_experiments import default_converter_registry
from polynexus.core.agent_workflow import AgentWorkflowService, AnalysisRecipe, InputArtifact, RecipeStep
from polynexus.core.agent_workflow.registry import WorkflowRegistry
from polynexus.core.compute import ComputeRunService
from polynexus.core.compute.models import RawArtifact
from polynexus.core.engine import AnalysisResult


class _Engine:
    def __init__(self) -> None:
        self.result = AnalysisResult(technique="ir")
        self.calls = 0

    def run_pipeline(self, _path, _output_dir, **_options):
        self.calls += 1
        return self.result


def test_compute_service_reuses_source_bound_template_without_registry_conversion(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "curve.csv"
    source.write_text("Wavenumber,Absorbance\n1700,0.4\n1600,0.8\n", encoding="utf-8")
    artifact = RawArtifact.from_path(source, technique="ir")
    converted = default_converter_registry().convert_path(
        source,
        technique="ir",
        source_artifact_id=artifact.artifact_id,
    )
    assert converted.template is not None
    monkeypatch.setattr(
        "polynexus.core.compute.service.default_converter_registry",
        lambda: pytest.fail("template should be reused without reconversion"),
    )
    engine = _Engine()

    run = ComputeRunService(lambda *args, **kwargs: engine).run_direct(
        technique="ir",
        path=source,
        output_dir=tmp_path / "out",
        engine=engine,
        canonical_template=converted.template,
    )

    assert run.status == "completed"
    assert run.canonical_template is not None
    assert run.canonical_template.content_hash == converted.template.content_hash
    assert len(run.capability_items) == 2
    assert engine.calls == 1


def test_compute_service_rejects_template_bound_to_another_artifact(tmp_path: Path) -> None:
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    first.write_text("Wavenumber,Absorbance\n1700,0.4\n1600,0.8\n", encoding="utf-8")
    second.write_text("Wavenumber,Absorbance\n1700,0.5\n1600,0.9\n", encoding="utf-8")
    first_artifact = RawArtifact.from_path(first, technique="ir")
    converted = default_converter_registry().convert_path(
        first,
        technique="ir",
        source_artifact_id=first_artifact.artifact_id,
    )
    assert converted.template is not None
    engine = _Engine()

    run = ComputeRunService(lambda *args, **kwargs: engine).run_direct(
        technique="ir",
        path=second,
        output_dir=tmp_path / "out",
        engine=engine,
        canonical_template=converted.template,
    )

    assert run.status == "needs_input"
    assert run.reasons == ("canonical_template_mismatch",)
    assert engine.calls == 0


def test_agent_workflow_reuses_replay_validated_template(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "curve.csv"
    source.write_text("Wavenumber,Absorbance\n1700,0.4\n1600,0.8\n", encoding="utf-8")
    artifact = InputArtifact.ready(
        path=str(source),
        technique="ir",
        sha256=RawArtifact.from_path(source, technique="ir").sha256,
    )
    converted = default_converter_registry().convert_path(
        source,
        technique="ir",
        source_artifact_id=artifact.artifact_id,
    )
    assert converted.template is not None

    class Adapter:
        workflow_id = "test.reuse"

        @staticmethod
        def is_valid_recipe(recipe):
            return recipe.workflow_id == "test.reuse"

    recipe = AnalysisRecipe.create(
        workflow_id="test.reuse",
        artifacts=(artifact,),
        steps=(
            RecipeStep(
                step_id="ir",
                technique="ir",
                parameters={
                    "canonical_converter": "generic.one-dimensional.v1",
                    "canonical_template": converted.template.to_dict(),
                },
            ),
        ),
    )
    registry = WorkflowRegistry()
    registry.register(Adapter())
    original_registry = default_converter_registry()
    calls = {"count": 0}

    class RegistryProxy:
        def replay_path(self, *args, **kwargs):
            calls["count"] += 1
            return original_registry.replay_path(*args, **kwargs)

    monkeypatch.setattr("polynexus.core.agent_workflow.service.default_converter_registry", lambda: RegistryProxy())
    engine = _Engine()
    run = AgentWorkflowService(
        registry=registry,
        get_engine_fn=lambda _technique: engine,
    ).run_recipe(recipe, tmp_path.parent.parent / "out")

    assert run.status == "review_required"
    assert calls["count"] == 1
    assert run.steps[0].compute_run["canonical_template"]["template_id"] == "spectrum_1d.v1"
