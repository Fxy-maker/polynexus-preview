from __future__ import annotations

from pathlib import Path

import pytest

from polynexus.core.agent_workflow import (
    AgentWorkflowService,
    AnalysisRecipe,
    InputArtifact,
    RecipeStep,
)
from polynexus.core.agent_workflow.registry import WorkflowRegistry
from polynexus.core.agent_workflow import inspect_artifact


def test_recipe_hash_is_stable_for_same_json_safe_content() -> None:
    artifact = InputArtifact.ready(
        path="C:/data/sample.csv",
        technique="dsc",
        sha256="a" * 64,
    )
    recipe = AnalysisRecipe.create(
        workflow_id="tpae.characterization.v1",
        artifacts=[artifact],
        steps=[RecipeStep(step_id="dsc_isothermal", technique="dsc")],
    )

    assert recipe.recipe_hash == AnalysisRecipe.from_dict(recipe.to_dict()).recipe_hash
    assert recipe.to_dict()["artifacts"][0]["sha256"] == "a" * 64


def test_recipe_contract_mappings_cannot_mutate_after_hash_creation() -> None:
    recipe = AnalysisRecipe.create(
        workflow_id="tpae.characterization.v1",
        artifacts=[InputArtifact.ready(path="C:/data/sample.csv", technique="dsc", sha256="a" * 64)],
        steps=[
            RecipeStep(
                step_id="dsc_isothermal",
                technique="dsc",
                parameters={"submodule_id": "dsc.isothermal", "nested": {"window": 5}},
            )
        ],
    )

    with pytest.raises(TypeError):
        recipe.steps[0].parameters["submodule_id"] = "dsc.standard"
    with pytest.raises(TypeError):
        recipe.steps[0].parameters["nested"]["window"] = 9


def test_inspect_edf_preserves_geometry_and_background_limit(tmp_path: Path) -> None:
    source = tmp_path / "sample.edf"
    source.write_bytes(
        b"{\n"
        b"Center_1 = 236.99 ;\n"
        b"Center_2 = 361.43 ;\n"
        b"PSize_1 = 0.000172 ;\n"
        b"PSize_2 = 0.000172 ;\n"
        b"SampleDistance = 1.188 ;\n"
        b"WaveLength = 1.54189e-10 ;\n"
        b"}\n"
    )

    artifact = inspect_artifact(source, technique="saxs")

    assert artifact.inspection_status == "review_required"
    assert artifact.header_facts["geometry_calibrated"] is True
    assert "background_unknown" in artifact.reason_codes


def test_inspect_missing_file_returns_blocked_artifact(tmp_path: Path) -> None:
    artifact = inspect_artifact(tmp_path / "missing.csv", technique="dsc")

    assert artifact.inspection_status == "blocked"
    assert artifact.reason_codes == ("file_missing",)


def test_inspect_directory_hashes_a_dsc_series_without_copying_it(tmp_path: Path) -> None:
    series = tmp_path / "isothermal-series"
    series.mkdir()
    (series / "run-1.csv").write_text("time,heat\n0,0\n", encoding="utf-8")
    (series / "run-2.csv").write_text("time,heat\n0,1\n", encoding="utf-8")

    artifact = inspect_artifact(series, technique="dsc")

    assert artifact.inspection_status == "ready"
    assert artifact.format == "directory"
    assert artifact.sha256 is not None

    repeat = inspect_artifact(series, technique="dsc")
    (series / "run-2.csv").write_text("time,heat\n0,2\n", encoding="utf-8")
    changed = inspect_artifact(series, technique="dsc")

    assert repeat.sha256 == artifact.sha256
    assert changed.sha256 != artifact.sha256


def test_run_blocks_before_provider_when_artifact_hash_changes(tmp_path: Path) -> None:
    source = tmp_path / "dsc-series"
    source.mkdir()
    data_file = source / "run-1.csv"
    data_file.write_text("original", encoding="utf-8")
    artifact = inspect_artifact(source, technique="dsc")
    recipe = AnalysisRecipe.create(
        workflow_id="tpae.characterization.v1",
        artifacts=[artifact],
        steps=[
            RecipeStep(
                step_id="dsc_isothermal", technique="dsc", evidence_role="primary",
                parameters={"submodule_id": "dsc.isothermal"},
            )
        ],
    )
    data_file.write_text("changed", encoding="utf-8")

    run = AgentWorkflowService(provider_runner=lambda *_: pytest.fail("provider called")).run_recipe(
        recipe,
        tmp_path.parent / "out",
    )

    assert run.status == "blocked"
    assert run.reason_codes == ("artifact_hash_mismatch",)


def test_run_rejects_a_recipe_whose_hash_does_not_match_its_public_content(tmp_path: Path) -> None:
    source = tmp_path / "dsc-series"
    source.mkdir()
    (source / "run-1.csv").write_text("original", encoding="utf-8")
    artifact = inspect_artifact(source, technique="dsc")
    recipe = AnalysisRecipe(
        workflow_id="tpae.characterization.v1",
        contract_version="1",
        artifacts=(artifact,),
        steps=(
            RecipeStep(
                step_id="dsc_isothermal", technique="dsc", evidence_role="primary",
                parameters={"submodule_id": "dsc.isothermal"},
            ),
        ),
        recipe_hash="not-a-canonical-hash",
    )

    run = AgentWorkflowService(provider_runner=lambda *_: pytest.fail("provider called")).run_recipe(
        recipe,
        tmp_path / "out",
    )

    assert run.status == "blocked"
    assert run.reason_codes == ("recipe_invalid",)


def test_tpae_recipe_rejects_duplicate_artifacts_for_one_technique(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "run.csv").write_text("first", encoding="utf-8")
    (second / "run.csv").write_text("second", encoding="utf-8")
    recipe = AnalysisRecipe.create(
        workflow_id="tpae.characterization.v1",
        artifacts=[inspect_artifact(first, technique="dsc"), inspect_artifact(second, technique="dsc")],
        steps=[
            RecipeStep(
                step_id="dsc_isothermal", technique="dsc", evidence_role="primary",
                parameters={"submodule_id": "dsc.isothermal"},
            )
        ],
    )

    run = AgentWorkflowService(provider_runner=lambda *_: pytest.fail("provider called")).run_recipe(
        recipe,
        tmp_path.parent / "out",
    )

    assert run.status == "blocked"
    assert run.reason_codes == ("recipe_invalid",)


def test_generic_file_mapping_blocks_before_default_provider_runs(tmp_path: Path) -> None:
    source = tmp_path / "ambiguous.csv"
    source.write_text("A,B,C\n1,2,3\n4,5,6\n", encoding="utf-8")
    artifact = inspect_artifact(source, technique="ir")

    class Adapter:
        workflow_id = "test.generic"

        @staticmethod
        def is_valid_recipe(recipe):
            return recipe.workflow_id == "test.generic"

    registry = WorkflowRegistry()
    registry.register(Adapter())
    provider_calls = []

    class Provider:
        def run_pipeline(self, *_args, **_kwargs):
            provider_calls.append(True)
            raise AssertionError("provider must not run before canonical mapping")

    recipe = AnalysisRecipe.create(
        workflow_id="test.generic",
        artifacts=(artifact,),
        steps=(RecipeStep(step_id="ir", technique="ir"),),
    )
    run = AgentWorkflowService(registry=registry, get_engine_fn=lambda _technique: Provider()).run_recipe(
        recipe, tmp_path.parent / "derived"
    )

    assert run.status == "blocked"
    assert run.reason_codes == ("conversion_mapping_ambiguous",)
    assert provider_calls == []
