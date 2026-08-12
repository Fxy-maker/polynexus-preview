"""JSON-only CLI adapter for the project-local evidence workflow."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from polynexus.core.project_workflow import (
    AnalysisRequest,
    EvidenceItem,
    ProjectPlan,
    ProjectWorkflowRun,
    ProjectWorkflowService,
)
from polynexus.core.agent_workflow.models import AnalysisRun


_SUCCESS_STATUSES = frozenset({"ready", "completed", "review_required"})


def run_project_workflow(args: Any, *, service: ProjectWorkflowService | None = None) -> int:
    """Execute one project operation and emit exactly one JSON envelope."""
    operation = str(getattr(args, "operation", ""))
    try:
        workflow = service or ProjectWorkflowService.open(args.project_root)
    except (OSError, TypeError, ValueError):
        return _emit(operation, "blocked", ["project_root_invalid"])

    if operation == "inspect":
        paths = tuple(getattr(args, "paths", ()) or ("raw",))
        try:
            graph = workflow.inspect(paths)
        except (OSError, TypeError, ValueError, UnicodeError):
            return _emit(operation, "blocked", ["inspection_invalid"])
        return _emit(operation, "completed", graph=graph.to_dict())

    if operation == "plan":
        request = _load_request(getattr(args, "request", None))
        if request is None:
            return _emit(operation, "blocked", ["request_invalid"])
        try:
            plan = workflow.plan(request)
        except (OSError, TypeError, ValueError, UnicodeError):
            return _emit(operation, "blocked", ["planning_failed"])
        return _emit(operation, plan.status, plan=plan.to_dict())

    if operation == "run":
        plan = _load_plan(getattr(args, "plan", None))
        request = _load_request(getattr(args, "request", None))
        if plan is None and request is None:
            return _emit(operation, "blocked", ["request_or_plan_required"])
        try:
            result = workflow.run(plan if plan is not None else request)  # type: ignore[arg-type]
        except (OSError, TypeError, ValueError, UnicodeError):
            return _emit(operation, "blocked", ["run_failed"])
        return _emit(operation, result.status, run=result.to_dict())

    if operation == "package":
        runs = _load_runs(getattr(args, "runs", ()))
        if runs is None:
            return _emit(operation, "blocked", ["runs_invalid"])
        relations = _load_relations(getattr(args, "relations", None))
        if relations is None:
            return _emit(operation, "blocked", ["relations_invalid"])
        try:
            package = workflow.package(
                runs,
                relations=relations,
                package_id=str(getattr(args, "package_id", "pa6-crystallization")),
            )
        except (OSError, TypeError, ValueError, UnicodeError):
            return _emit(operation, "blocked", ["package_failed"])
        return _emit(operation, package.status, package=package.to_dict())

    return _emit(operation, "blocked", ["operation_unknown"])


def _emit(operation: str, status: str, reason_codes: list[str] | tuple[str, ...] = (), **payload: Any) -> int:
    envelope: dict[str, Any] = {
        "operation": operation,
        "status": status,
        "reason_codes": list(dict.fromkeys(str(value) for value in reason_codes)),
    }
    envelope.update(payload)
    print(json.dumps(envelope, ensure_ascii=False, sort_keys=True, allow_nan=False))
    return 0 if status in _SUCCESS_STATUSES else 2


def _read_object(path: str | None) -> Mapping[str, Any] | None:
    if not path:
        return None
    try:
        value = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, TypeError):
        return None
    return value if isinstance(value, Mapping) else None


def _load_request(path: str | None) -> AnalysisRequest | None:
    value = _read_object(path)
    if value is None:
        return None
    try:
        return AnalysisRequest.from_dict(value)
    except (KeyError, TypeError, ValueError):
        return None


def _load_plan(path: str | None) -> ProjectPlan | None:
    value = _read_object(path)
    if value is None:
        return None
    try:
        return ProjectPlan.from_dict(value)
    except (KeyError, TypeError, ValueError):
        return None


def _load_runs(paths: Any) -> tuple[ProjectWorkflowRun, ...] | None:
    values = tuple(paths or ())
    if not values:
        return None
    runs: list[ProjectWorkflowRun] = []
    for path in values:
        value = _read_object(str(path))
        if value is None:
            return None
        try:
            analysis_payload = value.get("analysis_run")
            analysis_run = AnalysisRun.from_dict(analysis_payload) if isinstance(analysis_payload, Mapping) else None
            evidence_values = tuple(EvidenceItem.from_dict(item) for item in value.get("evidence_items", ()))
            runs.append(
                ProjectWorkflowRun(
                    run_id=str(value["run_id"]),
                    request_hash=str(value["request_hash"]),
                    plan_hash=str(value["plan_hash"]),
                    recipe_hash=value.get("recipe_hash"),
                    status=str(value["status"]),
                    outputs=tuple(str(item) for item in value.get("outputs", ())),
                    evidence_items=evidence_values,
                    manifest_path=str(value.get("manifest_path") or path),
                    analysis_run=analysis_run,
                    reason_codes=tuple(str(item) for item in value.get("reason_codes", ())),
                )
            )
        except (KeyError, TypeError, ValueError):
            return None
    return tuple(runs)


def _load_relations(path: str | None) -> tuple[Mapping[str, Any], ...] | None:
    if not path:
        return ()
    value = _read_object(path)
    if value is None:
        return None
    raw = value.get("relations", value)
    if not isinstance(raw, list):
        return None
    return tuple(item for item in raw if isinstance(item, Mapping)) if len(raw) == sum(isinstance(item, Mapping) for item in raw) else None


__all__ = ["run_project_workflow"]
