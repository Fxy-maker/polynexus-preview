from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest.mock import patch

from polynexus.cli.run_project_workflow_service import run_project_workflow
from polynexus.core.agent_workflow.service import AgentWorkflowService
from polynexus.core.engine import AnalysisResult
from polynexus.core.project_workflow import (
    AnalysisRequest,
    PortableExportBatchEntry,
    PortableExportBatchManifest,
    ProjectWorkflowService,
    TechniqueSeriesAdapter,
)
from polynexus.gui.main_window_workers import BatchWorker


def _fixture(tmp_path: Path) -> tuple[list[Path], PortableExportBatchManifest]:
    raw_dir = tmp_path / "raw" / "TGA"
    export_dir = tmp_path / "exports"
    raw_dir.mkdir(parents=True)
    export_dir.mkdir()
    raw_paths: list[Path] = []
    entries = []
    for name in ("run-b", "run-a"):
        raw = raw_dir / f"{name}.ngb-ds1"
        raw.write_bytes(f"opaque-{name}".encode("utf-8"))
        exported = export_dir / f"{name}.csv"
        exported.write_text(
            "Temperature (C),Mass (%)\n25,100\n100,98\n200,97\n",
            encoding="utf-8",
        )
        raw_paths.append(raw)
        entries.append(
            PortableExportBatchEntry(
                raw_source=str(raw.relative_to(tmp_path)),
                export_path=str(exported.relative_to(tmp_path)),
                exporter="Proteus portable CSV",
            )
        )
    return raw_paths, PortableExportBatchManifest.create(technique="tga", entries=entries)


def _binding_projection(compute_run: object) -> tuple[str, str, str, str, str]:
    payload = compute_run.to_dict() if hasattr(compute_run, "to_dict") else compute_run
    template = payload["canonical_template"]
    binding = template["payload"]["portable_export_binding"]
    return (
        template["content_hash"],
        template["source_artifact_id"],
        binding["raw_source_sha256"],
        binding["export_sha256"],
        binding["exporter"],
    )


def test_gui_cli_and_agent_share_portable_export_compute_contract(tmp_path: Path, capsys) -> None:
    raw_paths, batch_manifest = _fixture(tmp_path)

    class CanonicalEngine:
        def run_canonical_template(self, _template, _output_dir, **_options):
            return AnalysisResult(technique="tga", validation_passed=True)

    worker = BatchWorker(
        "tga",
        [str(path) for path in raw_paths],
        str(tmp_path / "gui-output"),
        portable_export={
            "raw_source": str(raw_paths[0].parent),
            "export_directory": str(tmp_path / "exports"),
            "exporter": "Proteus portable CSV",
        },
    )
    gui_rows: list[list[dict]] = []
    gui_errors: list[str] = []
    worker.batch_finished.connect(gui_rows.append)
    worker.error_msg.connect(gui_errors.append)
    with patch("polynexus.gui.main_window.get_engine", return_value=CanonicalEngine()):
        worker.run()
    assert gui_errors == []
    gui_runs = {row["file"]: row["compute_run"] for row in gui_rows[0]}

    request = AnalysisRequest.create(
        question="Compare TGA batch",
        data_scope=("raw/TGA",),
    )
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(request.to_dict()), encoding="utf-8")
    manifest_path = tmp_path / "portable-export-batch.json"
    manifest_path.write_text(json.dumps(batch_manifest.to_dict()), encoding="utf-8")
    project_service = ProjectWorkflowService.open(tmp_path)
    project_service.agent_service = AgentWorkflowService(
        provider_runner=lambda step, _artifact, _output_dir: AnalysisResult(
            technique=step.technique,
            validation_passed=True,
        )
    )
    args = argparse.Namespace(
        operation="run",
        project_root=str(tmp_path),
        request=str(request_path),
        portable_export_manifest=str(manifest_path),
    )
    assert run_project_workflow(args, service=project_service) == 0
    cli_payload = json.loads(capsys.readouterr().out)
    cli_run = project_service.resume(cli_payload["run"]["run_id"])
    assert cli_run.analysis_run is not None

    proposal = TechniqueSeriesAdapter().propose_recipe(
        {
            "workflow_id": TechniqueSeriesAdapter.workflow_id,
            "technique": "tga",
            "paths": [str(path) for path in raw_paths],
            "portable_exports": [
                {
                    "raw_source": str(raw),
                    "export_path": str(tmp_path / "exports" / f"{raw.stem}.csv"),
                    "exporter": "Proteus portable CSV",
                }
                for raw in raw_paths
            ],
        }
    )
    assert proposal.recipe is not None
    agent_service = AgentWorkflowService(
        provider_runner=lambda step, _artifact, _output_dir: AnalysisResult(
            technique=step.technique,
            validation_passed=True,
        )
    )
    agent_service.registry.register(TechniqueSeriesAdapter())
    agent_run = agent_service.run_recipe(proposal.recipe, tmp_path / "agent-output")
    assert agent_run.status == "review_required"

    gui_projection = {
        name: _binding_projection(gui_runs[f"{name}.ngb-ds1"])
        for name in ("run-a", "run-b")
    }
    cli_projection = {
        Path(step.compute_run["artifact"]["path"]).stem: _binding_projection(step.compute_run)
        for step in cli_run.analysis_run.steps
    }
    agent_projection = {
        Path(step.compute_run["artifact"]["path"]).stem: _binding_projection(step.compute_run)
        for step in agent_run.steps
    }
    assert gui_projection == cli_projection == agent_projection
