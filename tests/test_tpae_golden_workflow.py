from __future__ import annotations

import json
from pathlib import Path

import pytest

from polynexus.core.agent_workflow import AgentWorkflowService
from polynexus.core.engine import AnalysisResult


def _write_artifact(tmp_path: Path, name: str) -> Path:
    data_dir = tmp_path / "data"
    data_dir.mkdir(exist_ok=True)
    path = data_dir / name
    path.write_text(name, encoding="utf-8")
    return path


def _write_dsc_series(tmp_path: Path) -> Path:
    data_dir = tmp_path / "data"
    data_dir.mkdir(exist_ok=True)
    series = data_dir / "dsc-isothermal"
    series.mkdir()
    (series / "run-1.csv").write_text("time,heat\n0,0\n", encoding="utf-8")
    (series / "run-2.csv").write_text("time,heat\n0,1\n", encoding="utf-8")
    return series


def _write_dsc_program(tmp_path: Path) -> Path:
    data_dir = tmp_path / "data"
    data_dir.mkdir(exist_ok=True)
    path = data_dir / "dsc-program.txt"
    rows = []
    for index in range(61):
        rows.append(f"{index} {index} 255.02 255.0 1.0")
    for index in range(61, 142):
        rows.append(f"{index} {index} 180.05 180.0 {1.0 + 5.0 / (index - 56):.6f}")
    path.write_text("\n".join(["Sample Weight: 5.95 mg", *rows]), encoding="utf-8")
    return path


def _write_ftir_series(tmp_path: Path) -> Path:
    data_dir = tmp_path / "data"
    data_dir.mkdir(exist_ok=True)
    series = data_dir / "ftir-temperature"
    series.mkdir()
    (series / "20C.csv").write_text("wavenumber,intensity\n1000,1\n", encoding="utf-8")
    (series / "40C.csv").write_text("wavenumber,intensity\n1000,2\n", encoding="utf-8")
    return series


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
                "path": str(
                    _write_dsc_series(tmp_path)
                    if step_id == "dsc_isothermal"
                    else _write_ftir_series(tmp_path)
                    if step_id == "ftir_temperature"
                    else _write_artifact(tmp_path, filename)
                ),
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
    assert proposal.recipe.steps[1].parameters["submodule_id"] == "ir.temperature_2d"


def test_tpae_proposal_blocks_when_required_dsc_is_missing(tmp_path: Path) -> None:
    proposal = AgentWorkflowService().propose_recipe(
        "tpae.characterization.v1",
        _write_manifest(tmp_path, dsc=False),
    )

    assert proposal.status == "blocked"
    assert proposal.recipe is None
    assert proposal.reason_codes == ("required_artifact_missing:dsc_isothermal",)


def test_tpae_proposal_blocks_when_declared_technique_disagrees_with_step(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path, ftir=False, saxs=False)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["artifacts"]["dsc_isothermal"]["technique"] = "ir"
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    proposal = AgentWorkflowService().propose_recipe("tpae.characterization.v1", manifest)

    assert proposal.status == "blocked"
    assert proposal.reason_codes == ("artifact_technique_mismatch:dsc_isothermal",)


def test_tpae_proposal_requires_a_directory_for_isothermal_dsc(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path, ftir=False, saxs=False)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["artifacts"]["dsc_isothermal"]["path"] = str(_write_artifact(tmp_path, "dsc.csv"))
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    proposal = AgentWorkflowService().propose_recipe("tpae.characterization.v1", manifest)

    assert proposal.status == "blocked"
    assert proposal.reason_codes == ("artifact_format_mismatch:dsc_isothermal",)


def test_tpae_accepts_a_single_dsc_file_only_after_canonical_conversion(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path, ftir=False, saxs=False)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["artifacts"]["dsc_isothermal"]["path"] = str(_write_dsc_program(tmp_path))
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    proposal = AgentWorkflowService().propose_recipe("tpae.characterization.v1", manifest)

    assert proposal.status == "ready"
    assert proposal.recipe is not None
    assert proposal.recipe.artifacts[0].format == "txt"
    assert proposal.recipe.steps[0].parameters["canonical_converter"] == "mettler.dsc-isothermal.v1"


def test_tpae_single_dsc_run_signs_canonical_conversion_provenance(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path, ftir=False, saxs=False)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["artifacts"]["dsc_isothermal"]["path"] = str(_write_dsc_program(tmp_path))
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    proposal = AgentWorkflowService().propose_recipe("tpae.characterization.v1", manifest)
    assert proposal.recipe is not None

    def provider(step, artifact, output_dir):
        assert step.parameters["canonical_template"]["template_id"] == "thermal_program.v1"
        assert artifact.format == "txt"
        return AnalysisResult(technique="dsc", validation_passed=True)

    run = AgentWorkflowService(provider_runner=provider).run_recipe(proposal.recipe, tmp_path / "run")

    assert run.status == "review_required"
    assert run.steps[0].status == "review_required"
    assert run.steps[0].result_summary["canonical_template_hash"]
    assert run.steps[0].result_summary["canonical_conversion"]["extracted_segments"][0]["setpoint_C"] == 180.0
    assert run.steps[0].compute_run["canonical_template"]["template_id"] == "thermal_program.v1"
    assert "metrics" in run.steps[0].compute_run["result"]


def test_tpae_proposal_requires_a_directory_for_temperature_ftir(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path, dsc=True, ftir=True, saxs=False)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["artifacts"]["ftir_temperature"]["path"] = str(_write_artifact(tmp_path, "ftir.csv"))
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    proposal = AgentWorkflowService().propose_recipe("tpae.characterization.v1", manifest)

    assert proposal.status == "blocked"
    assert proposal.reason_codes == ("artifact_format_mismatch:ftir_temperature",)


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
    assert (bundle / "figures" / "manifest.json").is_file()
    assert not any(path.name == "run-1.csv" for path in bundle.rglob("*"))


def test_export_records_public_figure_references_without_copying_assets(tmp_path: Path) -> None:
    proposal = AgentWorkflowService().propose_recipe(
        "tpae.characterization.v1",
        _write_manifest(tmp_path, ftir=False, saxs=False),
    )
    assert proposal.recipe is not None
    figure_path = tmp_path / "published" / "dsc.png"
    result = AnalysisResult(technique="dsc", validation_passed=True)
    result.figures = {"dsc": str(figure_path)}
    run = AgentWorkflowService(provider_runner=lambda *_: result).validate_run(
        AgentWorkflowService(provider_runner=lambda *_: result).run_recipe(proposal.recipe, tmp_path / "run")
    )

    bundle = AgentWorkflowService().export_run(run, tmp_path / "bundle")
    manifest = json.loads((bundle / "figures" / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["steps"][0]["assets"]["dsc"] == str(figure_path)
    assert not (bundle / "figures" / "dsc.png").exists()


def test_default_provider_calls_existing_engine_public_pipeline(tmp_path: Path) -> None:
    proposal = AgentWorkflowService().propose_recipe(
        "tpae.characterization.v1",
        _write_manifest(tmp_path, ftir=False, saxs=False),
    )
    assert proposal.recipe is not None

    class Engine:
        active_submodule = None

        def run_pipeline(self, path, output_dir):
            assert Path(path).name == "dsc-isothermal"
            assert Path(output_dir).name == "dsc_isothermal"
            assert self.active_submodule == "dsc.isothermal"
            return AnalysisResult(technique="dsc", validation_passed=True)

    run = AgentWorkflowService(get_engine_fn=lambda technique: Engine()).run_recipe(
        proposal.recipe,
        tmp_path / "run",
    )

    assert run.status == "completed"
    assert run.steps[0].result_summary["technique"] == "dsc"


def test_run_rejects_output_inside_raw_data_directory(tmp_path: Path) -> None:
    proposal = AgentWorkflowService().propose_recipe(
        "tpae.characterization.v1",
        _write_manifest(tmp_path, ftir=False, saxs=False),
    )
    assert proposal.recipe is not None
    raw_directory = Path(proposal.recipe.artifacts[0].path)

    run = AgentWorkflowService(provider_runner=lambda *_: pytest.fail("provider called")).run_recipe(
        proposal.recipe,
        raw_directory / "output",
    )

    assert run.status == "blocked"
    assert run.reason_codes == ("output_inside_input_directory",)


def test_run_marks_engine_error_logs_as_failed_even_when_validation_default_is_true(tmp_path: Path) -> None:
    proposal = AgentWorkflowService().propose_recipe(
        "tpae.characterization.v1",
        _write_manifest(tmp_path, ftir=False, saxs=False),
    )
    assert proposal.recipe is not None
    result = AnalysisResult(technique="dsc", validation_passed=True, logs=["ERROR: Preprocessing failed"])

    run = AgentWorkflowService(provider_runner=lambda *_: result).run_recipe(proposal.recipe, tmp_path / "run")

    assert run.status == "failed"
    assert run.steps[0].status == "failed"
