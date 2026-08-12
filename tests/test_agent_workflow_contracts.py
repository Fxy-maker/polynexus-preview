from __future__ import annotations

from pathlib import Path

from polynexus.core.agent_workflow import AnalysisRecipe, InputArtifact, RecipeStep
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
