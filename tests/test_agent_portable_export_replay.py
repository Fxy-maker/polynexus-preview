from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from polynexus.core.agent_workflow import AgentWorkflowService
from polynexus.core.agent_workflow.models import AnalysisRecipe
from polynexus.core.engine import AnalysisResult
from polynexus.core.project_workflow.service import ProjectWorkflowService
from polynexus.core.project_workflow.adapters import SingleInputTechniqueAdapter
from polynexus.core.project_workflow.adapters import TechniqueSeriesAdapter


def _portable_recipe(tmp_path: Path):
    raw = tmp_path / "sample.ngb-ds1"
    raw.write_bytes(b"Netzsch TA file\x00_db_format_1\x00opaque")
    exported = tmp_path / "sample.csv"
    exported.write_text("Temperature (C),Mass (%)\n25,100\n100,98\n", encoding="utf-8")
    proposal = SingleInputTechniqueAdapter().propose_recipe(
        {
            "workflow_id": "project.technique.single.v1",
            "technique": "tga",
            "path": str(raw),
            "portable_export": {
                "export_path": str(exported),
                "exporter": "Proteus portable CSV",
            },
        }
    )
    assert proposal.recipe is not None
    return raw, exported, proposal.recipe


def _service(tmp_path: Path, *, provider_runner=None) -> AgentWorkflowService:
    project = ProjectWorkflowService.open(tmp_path)
    return AgentWorkflowService(
        registry=project.agent_service.registry,
        provider_runner=provider_runner,
    ) if provider_runner is not None else project.agent_service


def test_agent_replays_opaque_raw_with_portable_export_through_shared_compute(tmp_path: Path) -> None:
    _raw, _exported, recipe = _portable_recipe(tmp_path)

    run = _service(tmp_path).run_recipe(recipe, tmp_path.parent / f"{tmp_path.name}-run")

    assert run.status == "review_required"
    assert run.steps[0].status == "review_required"
    compute_run = run.steps[0].compute_run
    assert compute_run is not None
    assert compute_run["status"] == "completed"
    binding = compute_run["canonical_template"]["payload"]["portable_export_binding"]
    assert binding["raw_source_sha256"] == recipe.artifacts[0].sha256
    assert binding["export_sha256"]


def test_agent_custom_provider_receives_portable_export_path(tmp_path: Path) -> None:
    _raw, exported, recipe = _portable_recipe(tmp_path)
    seen: list[str] = []

    def provider(_step, artifact, _output_dir):
        seen.append(artifact.path)
        return AnalysisResult(technique="tga", validation_passed=True)

    run = _service(tmp_path, provider_runner=provider).run_recipe(
        recipe,
        tmp_path.parent / f"{tmp_path.name}-run",
    )

    assert run.status == "review_required"
    assert seen == [str(exported.resolve())]
    assert run.steps[0].compute_run["canonical_template"]["source_artifact_id"] == recipe.artifacts[0].artifact_id


def test_agent_series_replay_uses_matching_export_for_each_artifact(tmp_path: Path) -> None:
    raw_paths = []
    portable_exports = []
    for index in range(2):
        raw = tmp_path / f"sample-{index}.ngb-ds1"
        raw.write_bytes(f"opaque-{index}".encode("utf-8"))
        exported = tmp_path / f"sample-{index}.csv"
        exported.write_text(
            "Temperature (C),Mass (%)\n25,100\n100,98\n",
            encoding="utf-8",
        )
        raw_paths.append(str(raw))
        portable_exports.append({
            "raw_source": str(raw),
            "export_path": str(exported),
            "exporter": "Proteus portable CSV",
        })
    proposal = TechniqueSeriesAdapter().propose_recipe({
        "workflow_id": TechniqueSeriesAdapter.workflow_id,
        "technique": "tga",
        "paths": raw_paths,
        "portable_exports": portable_exports,
    })
    assert proposal.recipe is not None
    seen: list[str] = []

    def provider(_step, artifact, _output_dir):
        seen.append(artifact.path)
        return AnalysisResult(technique="tga", validation_passed=True)

    run = AgentWorkflowService(
        registry=ProjectWorkflowService.open(tmp_path).agent_service.registry,
        provider_runner=provider,
    ).run_recipe(proposal.recipe, tmp_path.parent / f"{tmp_path.name}-series-run")

    assert run.status == "review_required"
    assert seen == [str(Path(item["export_path"]).resolve()) for item in portable_exports]


def test_agent_portable_replay_rejects_raw_mutation_before_provider(tmp_path: Path) -> None:
    raw, _exported, recipe = _portable_recipe(tmp_path)
    raw.write_bytes(raw.read_bytes() + b"changed")

    run = _service(
        tmp_path,
        provider_runner=lambda *_: (_ for _ in ()).throw(AssertionError("provider called"))
    ).run_recipe(recipe, tmp_path.parent / f"{tmp_path.name}-run")

    assert run.status == "blocked"
    assert run.reason_codes == ("artifact_hash_mismatch",)


def test_agent_portable_replay_rejects_export_mutation_before_provider(tmp_path: Path) -> None:
    _raw, exported, recipe = _portable_recipe(tmp_path)
    exported.write_text("Temperature (C),Mass (%)\n25,100\n100,97\n", encoding="utf-8")

    run = _service(
        tmp_path,
        provider_runner=lambda *_: (_ for _ in ()).throw(AssertionError("provider called"))
    ).run_recipe(recipe, tmp_path.parent / f"{tmp_path.name}-run")

    assert run.status == "blocked"
    assert run.reason_codes == ("canonical_conversion_mismatch",)


def test_agent_portable_replay_rejects_missing_export_before_provider(tmp_path: Path) -> None:
    _raw, exported, recipe = _portable_recipe(tmp_path)
    exported.unlink()

    run = _service(
        tmp_path,
        provider_runner=lambda *_: (_ for _ in ()).throw(AssertionError("provider called"))
    ).run_recipe(recipe, tmp_path.parent / f"{tmp_path.name}-run")

    assert run.status == "blocked"
    assert run.reason_codes == ("portable_export_missing",)


def test_agent_portable_replay_rejects_invalid_exporter_before_provider(tmp_path: Path) -> None:
    _raw, _exported, recipe = _portable_recipe(tmp_path)
    step = recipe.steps[0]
    portable = dict(step.parameters["portable_export"])
    portable["exporter"] = ""
    invalid = AnalysisRecipe.create(
        workflow_id=recipe.workflow_id,
        artifacts=recipe.artifacts,
        steps=(replace(step, parameters={**dict(step.parameters), "portable_export": portable}),),
    )

    run = _service(
        tmp_path,
        provider_runner=lambda *_: (_ for _ in ()).throw(AssertionError("provider called")),
    ).run_recipe(invalid, tmp_path.parent / f"{tmp_path.name}-run")

    assert run.status == "blocked"
    assert run.reason_codes == ("recipe_invalid",)


def test_agent_portable_replay_rejects_foreign_raw_source_before_provider(tmp_path: Path) -> None:
    _raw, _exported, recipe = _portable_recipe(tmp_path)
    step = recipe.steps[0]
    portable = dict(step.parameters["portable_export"])
    portable["raw_source"] = str(tmp_path.parent / "foreign.ngb-ds1")
    invalid = AnalysisRecipe.create(
        workflow_id=recipe.workflow_id,
        artifacts=recipe.artifacts,
        steps=(replace(step, parameters={**dict(step.parameters), "portable_export": portable}),),
    )

    run = _service(
        tmp_path,
        provider_runner=lambda *_: (_ for _ in ()).throw(AssertionError("provider called")),
    ).run_recipe(invalid, tmp_path.parent / f"{tmp_path.name}-run")

    assert run.status == "blocked"
    assert run.reason_codes == ("recipe_invalid",)
