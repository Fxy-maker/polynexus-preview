from __future__ import annotations

import json
from pathlib import Path

from polynexus.core.agent_workflow import AgentWorkflowService
from polynexus.core.engine import AnalysisResult


def _write_artifact(tmp_path: Path, name: str) -> Path:
    path = tmp_path / name
    path.write_text(name, encoding="utf-8")
    return path


def _write_manifest(
    tmp_path: Path,
    *,
    dsc: bool = True,
    ftir: bool = True,
    waxs: bool = False,
    saxs: bool = True,
) -> Path:
    artifacts: dict[str, dict[str, str]] = {}
    for step_id, technique, enabled, filename in (
        ("dsc_isothermal", "dsc", dsc, "dsc.csv"),
        ("ftir_temperature", "ir", ftir, "ftir.csv"),
        ("waxs_profile", "waxs", waxs, "waxs.raw"),
        ("saxs_profile", "saxs", saxs, "saxs.dat"),
    ):
        if enabled:
            artifacts[step_id] = {
                "path": str(_write_artifact(tmp_path, filename)),
                "technique": technique,
            }
    manifest = tmp_path / "tpae.json"
    manifest.write_text(
        json.dumps({"workflow_id": "tpae.characterization.v1", "artifacts": artifacts}),
        encoding="utf-8",
    )
    return manifest


def test_tpae_proposal_requires_dsc_and_orders_available_steps(tmp_path: Path) -> None:
    proposal = AgentWorkflowService().propose_recipe(
        "tpae.characterization.v1",
        _write_manifest(tmp_path),
    )

    assert proposal.status == "ready"
    assert proposal.recipe is not None
    assert [step.step_id for step in proposal.recipe.steps] == [
        "dsc_isothermal",
        "ftir_temperature",
        "saxs_profile",
    ]
    assert proposal.recipe.steps[0].evidence_role == "primary"


def test_tpae_proposal_blocks_when_required_dsc_is_missing(tmp_path: Path) -> None:
    proposal = AgentWorkflowService().propose_recipe(
        "tpae.characterization.v1",
        _write_manifest(tmp_path, dsc=False),
    )

    assert proposal.status == "blocked"
    assert proposal.recipe is None
    assert proposal.reason_codes == ("required_artifact_missing:dsc_isothermal",)


def test_run_normalizes_public_result_and_preserves_conclusion_limits(tmp_path: Path) -> None:
    proposal = AgentWorkflowService().propose_recipe(
        "tpae.characterization.v1",
        _write_manifest(tmp_path, ftir=False, saxs=False),
    )
    assert proposal.recipe is not None

    def provider(step, artifact, output_dir):
        assert step.step_id == "dsc_isothermal"
        assert artifact.technique == "dsc"
        assert output_dir.name == "run"
        return AnalysisResult(
            technique="dsc",
            validation_passed=True,
            parameters={"t_half_min": 0.5},
            analysis_evidence={"summary": "qualified DSC output"},
        )

    service = AgentWorkflowService(provider_runner=provider)
    run = service.run_recipe(proposal.recipe, tmp_path / "run")
    validated = service.validate_run(run)

    assert validated.status == "completed"
    assert validated.steps[0].result_summary["technique"] == "dsc"
    assert "unique_hydrogen_bond_species" in validated.evidence.disallowed_conclusions


def test_run_normalizes_nonfinite_public_summary_values_to_null(tmp_path: Path) -> None:
    proposal = AgentWorkflowService().propose_recipe(
        "tpae.characterization.v1",
        _write_manifest(tmp_path, ftir=False, saxs=False),
    )
    assert proposal.recipe is not None
    run = AgentWorkflowService(
        provider_runner=lambda *_: AnalysisResult(technique="dsc", validation_passed=True)
    ).run_recipe(proposal.recipe, tmp_path / "run")

    assert run.status == "completed"
    assert run.steps[0].result_summary["effective_q_min"] is None


def test_export_writes_replay_bundle_without_copying_raw_artifact(tmp_path: Path) -> None:
    proposal = AgentWorkflowService().propose_recipe(
        "tpae.characterization.v1",
        _write_manifest(tmp_path, ftir=False, saxs=False),
    )
    assert proposal.recipe is not None
    service = AgentWorkflowService(
        provider_runner=lambda *_: AnalysisResult(technique="dsc", validation_passed=True)
    )
    run = service.validate_run(service.run_recipe(proposal.recipe, tmp_path / "run"))

    bundle = service.export_run(run, tmp_path / "bundle")

    assert (bundle / "recipe.json").is_file()
    assert (bundle / "artifacts.json").is_file()
    assert (bundle / "evidence.json").is_file()
    assert not any(path.name == "dsc.csv" for path in bundle.rglob("*"))
