from __future__ import annotations

import argparse
import json
from pathlib import Path

from polynexus.cli.parser import parse_args
from polynexus.cli.run_agent_workflow_service import run_agent_workflow
from polynexus.core.agent_workflow import AgentWorkflowService, AnalysisRecipe, RecipeStep
from polynexus.core.agent_workflow.models import AnalysisRun
from polynexus.core.engine import AnalysisResult


def test_agent_workflow_parser_accepts_inspect_operation() -> None:
    args = parse_args(["agent-workflow", "inspect", "--manifest", "tpae.json"])

    assert args.cmd == "agent-workflow"
    assert args.operation == "inspect"
    assert args.manifest == "tpae.json"


def test_agent_workflow_cli_prints_exactly_one_json_envelope(capsys, tmp_path: Path) -> None:
    manifest = tmp_path / "tpae.json"
    manifest.write_text(
        json.dumps(
            {
                "workflow_id": "tpae.characterization.v1",
                "artifacts": {"dsc_isothermal": {"path": str(tmp_path / "missing.csv"), "technique": "dsc"}},
            }
        ),
        encoding="utf-8",
    )
    args = argparse.Namespace(operation="inspect", manifest=str(manifest), output_dir=None)

    code = run_agent_workflow(args)

    lines = capsys.readouterr().out.splitlines()
    assert code == 2
    assert len(lines) == 1
    assert json.loads(lines[0])["status"] == "blocked"


def test_agent_workflow_inspect_returns_artifacts_even_when_required_input_is_missing(
    capsys,
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "tpae.json"
    manifest.write_text(
        json.dumps(
            {
                "workflow_id": "tpae.characterization.v1",
                "artifacts": {"dsc_isothermal": {"path": str(tmp_path / "missing.csv"), "technique": "dsc"}},
            }
        ),
        encoding="utf-8",
    )

    code = run_agent_workflow(
        argparse.Namespace(operation="inspect", manifest=str(manifest), output_dir=None, export_dir=None)
    )

    payload = json.loads(capsys.readouterr().out)
    assert code == 2
    assert payload["artifacts"][0]["reason_codes"] == ["file_missing"]


def test_agent_workflow_cli_persists_and_exports_a_validated_run(capsys, tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    source = data_dir / "dsc-isothermal"
    source.mkdir()
    (source / "run-1.csv").write_text("time,heat\n0,0\n", encoding="utf-8")
    (source / "run-2.csv").write_text("time,heat\n0,1\n", encoding="utf-8")
    ftir_source = data_dir / "ftir-temperature"
    ftir_source.mkdir()
    (ftir_source / "20C.csv").write_text("wavenumber,intensity\n1000,1\n", encoding="utf-8")
    manifest = tmp_path / "tpae.json"
    manifest.write_text(
        json.dumps(
            {
                "workflow_id": "tpae.characterization.v1",
                "artifacts": {
                    "dsc_isothermal": {"path": str(source), "technique": "dsc"},
                    "ftir_temperature": {"path": str(ftir_source), "technique": "ir"},
                },
            }
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "run-output"
    service = AgentWorkflowService(
        provider_runner=lambda step, *_: AnalysisResult(technique=step.technique, validation_passed=True)
    )

    run_args = argparse.Namespace(
        operation="run",
        manifest=str(manifest),
        output_dir=str(output_dir),
        export_dir=None,
    )
    assert run_agent_workflow(run_args, service=service) == 0
    run_path = output_dir / "run.json"
    assert run_path.is_file()
    capsys.readouterr()

    validate_args = argparse.Namespace(
        operation="validate", manifest=str(manifest), output_dir=str(output_dir)
        , export_dir=None
    )
    assert run_agent_workflow(validate_args, service=service) == 0
    assert json.loads(run_path.read_text(encoding="utf-8"))["validated"] is True
    capsys.readouterr()

    export_args = argparse.Namespace(
        operation="export",
        manifest=str(manifest),
        output_dir=str(output_dir),
        export_dir=str(output_dir / "bundle"),
    )
    assert run_agent_workflow(export_args, service=service) == 0
    assert (output_dir / "bundle" / "evidence.json").is_file()
    assert len(capsys.readouterr().out.splitlines()) == 1


def test_agent_workflow_cli_requires_an_explicit_output_directory_for_run(capsys, tmp_path: Path) -> None:
    manifest = tmp_path / "tpae.json"
    manifest.write_text(json.dumps({"workflow_id": "tpae.characterization.v1", "artifacts": {}}), encoding="utf-8")

    code = run_agent_workflow(
        argparse.Namespace(operation="run", manifest=str(manifest), output_dir=None, export_dir=None)
    )

    payload = json.loads(capsys.readouterr().out)
    assert code == 2
    assert payload["reason_codes"] == ["output_dir_required"]


def test_agent_workflow_cli_replays_persisted_recipe_without_manifest(capsys, tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    source = data_dir / "dsc-isothermal"
    source.mkdir()
    (source / "run-1.csv").write_text("time,heat\n0,0\n", encoding="utf-8")
    (source / "run-2.csv").write_text("time,heat\n0,1\n", encoding="utf-8")
    artifact = AgentWorkflowService().inspect_data(source, technique="dsc")
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
    recipe_path = tmp_path / "recipe.json"
    recipe_path.write_text(json.dumps(recipe.to_dict()), encoding="utf-8")
    output_dir = tmp_path / "run-output"

    code = run_agent_workflow(
        argparse.Namespace(
            operation="run",
            manifest=None,
            recipe=str(recipe_path),
            run=None,
            output_dir=str(output_dir),
            export_dir=None,
        ),
        service=AgentWorkflowService(
            provider_runner=lambda *_: AnalysisResult(technique="dsc", validation_passed=True)
        ),
    )

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["status"] == "completed"
    assert (output_dir / "run.json").is_file()


def test_agent_workflow_cli_refuses_to_export_a_fabricated_validated_run(capsys, tmp_path: Path) -> None:
    source = tmp_path / "dsc.csv"
    source.write_text("time,heat\n0,0\n", encoding="utf-8")
    artifact = AgentWorkflowService().inspect_data(source, technique="dsc")
    recipe = AnalysisRecipe.create(
        workflow_id="tpae.characterization.v1",
        artifacts=[artifact],
        steps=[RecipeStep(step_id="dsc_isothermal", technique="dsc")],
    )
    run_path = tmp_path / "forged-run.json"
    run_path.write_text(
        json.dumps(AnalysisRun(recipe=recipe, status="completed", validated=True).to_dict()),
        encoding="utf-8",
    )

    code = run_agent_workflow(
        argparse.Namespace(
            operation="export", manifest=None, recipe=None, run=str(run_path),
            output_dir=str(tmp_path / "run-output"), export_dir=str(tmp_path / "bundle"),
        )
    )

    payload = json.loads(capsys.readouterr().out)
    assert code == 2
    assert payload["reason_codes"] == ["export_destination_invalid"]


def test_agent_workflow_cli_refuses_to_validate_a_structurally_complete_forged_run(capsys, tmp_path: Path) -> None:
    series = tmp_path / "dsc-isothermal"
    series.mkdir()
    (series / "run.csv").write_text("time,heat\n0,0\n", encoding="utf-8")
    artifact = AgentWorkflowService().inspect_data(series, technique="dsc")
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
    forged = AnalysisRun(
        recipe=recipe,
        status="completed",
        steps=(
            __import__("polynexus.core.agent_workflow", fromlist=["WorkflowStepResult"]).WorkflowStepResult(
                step_id="dsc_isothermal", technique="dsc", status="completed", result_summary={"technique": "dsc"}
            ),
        ),
    )
    run_path = tmp_path / "forged-run.json"
    run_path.write_text(json.dumps(forged.to_dict()), encoding="utf-8")

    code = run_agent_workflow(
        argparse.Namespace(
            operation="validate", manifest=None, recipe=None, run=str(run_path),
            output_dir=str(tmp_path / "run-output"), export_dir=None,
        )
    )

    payload = json.loads(capsys.readouterr().out)
    assert code == 2
    assert payload["reason_codes"] == ["run_receipt_invalid"]


def test_agent_workflow_cli_refuses_to_export_a_run_with_tampered_evidence(capsys, tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    series = data_dir / "dsc-isothermal"
    series.mkdir()
    (series / "run.csv").write_text("time,heat\n0,0\n", encoding="utf-8")
    manifest = tmp_path / "tpae.json"
    manifest.write_text(
        json.dumps(
            {
                "workflow_id": "tpae.characterization.v1",
                "artifacts": {"dsc_isothermal": {"path": str(series), "technique": "dsc"}},
            }
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "run-output"
    service = AgentWorkflowService(
        provider_runner=lambda *_: AnalysisResult(technique="dsc", validation_passed=True)
    )
    assert run_agent_workflow(
        argparse.Namespace(operation="run", manifest=str(manifest), output_dir=str(output_dir), export_dir=None),
        service=service,
    ) == 0
    capsys.readouterr()
    assert run_agent_workflow(
        argparse.Namespace(operation="validate", manifest=str(manifest), output_dir=str(output_dir), export_dir=None),
        service=service,
    ) == 0
    capsys.readouterr()
    run_path = output_dir / "run.json"
    payload = json.loads(run_path.read_text(encoding="utf-8"))
    payload["evidence"]["supported_interpretations"] = ["forged scientific claim"]
    run_path.write_text(json.dumps(payload), encoding="utf-8")

    code = run_agent_workflow(
        argparse.Namespace(
            operation="export", manifest=str(manifest), output_dir=str(output_dir),
            export_dir=str(output_dir / "bundle"),
        ),
        service=service,
    )

    exported = json.loads(capsys.readouterr().out)
    assert code == 2
    assert exported["reason_codes"] == ["export_destination_invalid"]
