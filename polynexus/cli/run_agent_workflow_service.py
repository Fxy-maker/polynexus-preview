"""JSON-only runtime for the agent workflow CLI boundary."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from polynexus.core.agent_workflow import AgentWorkflowService
from polynexus.core.agent_workflow.models import AnalysisRecipe, AnalysisRun
from polynexus.core.project_workflow.validation import (
    ProjectValidationEntry,
    run_project_validation_batch,
)
from polynexus.core.project_workflow.workspace import ProjectWorkspace


def run_agent_workflow(args: Any, *, service: AgentWorkflowService | None = None) -> int:
    """Run one public agent operation and print one JSON-safe envelope."""
    workflow_service = service or AgentWorkflowService()
    manifest_path = Path(args.manifest) if getattr(args, "manifest", None) else None
    payload: dict[str, Any] | None = None
    if manifest_path is not None:
        try:
            loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
            payload = loaded if isinstance(loaded, dict) else None
        except (OSError, ValueError, TypeError):
            payload = None

    if args.operation == "inspect":
        if payload is None:
            return _emit({"operation": "inspect", "status": "blocked", "reason_codes": ["manifest_invalid"]})
        return _emit({"operation": "inspect", **workflow_service.inspect_manifest(payload)})
    if args.operation == "propose":
        workflow_id = payload.get("workflow_id") if payload else None
        if not isinstance(workflow_id, str):
            return _emit({"operation": "propose", "status": "blocked", "reason_codes": ["workflow_id_missing"]})
        proposal = workflow_service.propose_recipe(workflow_id, payload)
        return _emit({"operation": "propose", **proposal.to_dict()})
    if args.operation == "validate-project":
        return _run_project_validation(payload, args)
    if not getattr(args, "output_dir", None):
        return _emit({"operation": args.operation, "status": "blocked", "reason_codes": ["output_dir_required"]})
    run_dir = Path(args.output_dir).resolve()
    run_path = run_dir / "run.json"
    if args.operation == "run":
        recipe = _load_recipe(getattr(args, "recipe", None))
        if recipe is None:
            workflow_id = payload.get("workflow_id") if payload else None
            if not isinstance(workflow_id, str):
                return _emit({"operation": "run", "status": "blocked", "reason_codes": ["recipe_or_manifest_required"]})
            proposal = workflow_service.propose_recipe(workflow_id, payload)
            if proposal.recipe is None:
                return _emit({"operation": "run", **proposal.to_dict()})
            recipe = proposal.recipe
        run = workflow_service.run_recipe(recipe, run_dir)
        try:
            _write_run(run_path, run)
        except OSError:
            return _emit({"operation": "run", "status": "failed", "reason_codes": ["run_persistence_failed"]})
        return _emit({"operation": "run", **run.to_dict(), "run_path": str(run_path)})
    explicit_run_path = Path(args.run) if getattr(args, "run", None) else run_path
    try:
        run = AnalysisRun.from_dict(json.loads(explicit_run_path.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError, KeyError):
        return _emit({"operation": args.operation, "status": "blocked", "reason_codes": ["run_missing"]})
    if args.operation == "validate":
        validated = workflow_service.validate_run(run)
        try:
            _write_run(explicit_run_path, validated)
        except OSError:
            return _emit({"operation": "validate", "status": "failed", "reason_codes": ["run_persistence_failed"]})
        return _emit({"operation": "validate", **validated.to_dict(), "run_path": str(explicit_run_path)})
    if args.operation == "export":
        destination = Path(args.export_dir or run_dir / "bundle")
        try:
            bundle = workflow_service.export_run(run, destination)
        except (OSError, ValueError):
            return _emit({"operation": "export", "status": "blocked", "reason_codes": ["export_destination_invalid"]})
        return _emit({"operation": "export", "status": run.status, "bundle": str(bundle)})
    return _emit({"operation": args.operation, "status": "blocked", "reason_codes": ["operation_unknown"]})


def _emit(payload: dict[str, Any]) -> int:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False))
    return 0 if payload.get("status") in {"ready", "completed", "review_required", "passed"} else 2


def _write_run(path: Path, run: AnalysisRun) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(run.to_dict(), ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _load_recipe(path: str | None) -> AnalysisRecipe | None:
    if not path:
        return None
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return AnalysisRecipe.from_dict(payload)
    except (OSError, ValueError, TypeError, KeyError):
        return None


def _run_project_validation(payload: dict[str, Any] | None, args: Any) -> int:
    """Run a JSON-only project validation manifest through the shared batch runner."""
    try:
        if payload is None:
            raise ValueError("manifest_invalid")
        root_value = getattr(args, "project_root", None)
        if not root_value:
            raise ValueError("project_root_required")
        raw_entries = payload.get("entries")
        if not isinstance(raw_entries, list):
            raise ValueError("entries_required")
        entries = tuple(ProjectValidationEntry.from_dict(item) for item in raw_entries)
        batch = run_project_validation_batch(entries)
        report_path = ProjectWorkspace.open(root_value).write_validation_batch(batch)
        return _emit(
            {
                "operation": "validate-project",
                **batch.to_dict(),
                "report_path": str(report_path),
            }
        )
    except (OSError, TypeError, ValueError, KeyError, StopIteration) as exc:
        reason = str(exc).strip() or type(exc).__name__
        return _emit(
            {
                "operation": "validate-project",
                "status": "failed",
                "reason_codes": ["project_validation_manifest_invalid"],
                "error": reason,
            }
        )
