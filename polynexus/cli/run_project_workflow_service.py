"""JSON-only CLI adapter for the project-local evidence workflow."""

from __future__ import annotations

import json
from contextlib import redirect_stdout
from pathlib import Path
import sys
from typing import Any, Mapping

from polynexus.core.project_workflow import (
    AnalysisRequest,
    EvidenceItem,
    ProjectPlan,
    ProjectWorkflowRun,
    ProjectWorkflowService,
    FigureSelectionRequest,
    AnalysisPlan,
    AnalysisPlanEvaluation,
    PaperBrief,
    build_manuscript_plan,
    project_analysis_plan_evaluation,
)
from polynexus.core.agent_workflow.models import AnalysisRun


_SUCCESS_STATUSES = frozenset({"ready", "completed", "review_required"})


def run_analysis_plan_evaluation(args: Any) -> int:
    """Emit the shared plan/evaluation projection for CLI and ARS callers."""
    try:
        plan_payload = json.loads(Path(args.plan).expanduser().read_text(encoding="utf-8"))
        evaluation_payload = json.loads(Path(args.evaluation).expanduser().read_text(encoding="utf-8"))
        plan = AnalysisPlan.from_dict(plan_payload)
        evaluation = AnalysisPlanEvaluation.from_dict(evaluation_payload)
        projection = project_analysis_plan_evaluation(plan, evaluation)
    except (OSError, UnicodeError, TypeError, ValueError, KeyError, json.JSONDecodeError):
        return _emit("evaluate-analysis-plans", "blocked", ["analysis_plan_evaluation_invalid"])
    return _emit("evaluate-analysis-plans", "completed", analysis_plan_evaluation=projection)


def run_project_workflow(args: Any, *, service: ProjectWorkflowService | None = None) -> int:
    """Execute one project operation and emit exactly one JSON envelope."""
    operation = str(getattr(args, "operation", ""))
    if operation == "manuscript-plan":
        return _run_manuscript_plan(args)
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

    if operation == "attach-quick-run":
        try:
            attachment = workflow.attach_quick_run(
                quick_run_id=str(getattr(args, "quick_run_id", "") or ""),
                technique=str(getattr(args, "technique", "") or ""),
                source_file=str(getattr(args, "source_file", "") or ""),
                output_dir=str(getattr(args, "output_dir", "") or ""),
            )
        except (OSError, TypeError, ValueError, UnicodeError):
            return _emit(operation, "blocked", ["quick_run_attachment_invalid"])
        return _emit(
            operation,
            "completed",
            attachment={
                "quick_run_id": attachment.quick_run_id,
                "technique": attachment.technique,
                "source_file": attachment.source_file,
                "source_sha256": attachment.source_sha256,
                "output_dir": attachment.output_dir,
                "manifest_path": str(attachment.manifest_path),
                "attachment_kind": "reference_only",
            },
        )

    if operation == "analyze-project":
        selection_path = getattr(args, "figure_selection", None)
        figure_selection = _load_figure_selection(selection_path)
        if selection_path and figure_selection is None:
            return _emit(operation, "blocked", ["figure_selection_invalid"])
        try:
            with redirect_stdout(sys.stderr):
                summary = workflow.analyze_project(
                    question=str(getattr(args, "question", "Analyze this research project.")),
                    data_scope=tuple(getattr(args, "paths", ()) or ()),
                    package_id=str(getattr(args, "package_id", "research-evidence")),
                    figure_selection=figure_selection,
                )
        except (OSError, TypeError, ValueError, UnicodeError):
            return _emit(operation, "blocked", ["analysis_failed"])
        payload = summary.to_dict()
        status = "completed" if payload["computation"] == "passed" else "blocked"
        return _emit(operation, status, payload["reason_codes"], analysis=payload)

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


def _run_manuscript_plan(args: Any) -> int:
    brief_payload = _read_object(getattr(args, "brief", None))
    if brief_payload is None:
        return _emit("manuscript-plan", "blocked", ["paper_brief_invalid"])
    try:
        brief = PaperBrief.from_dict(brief_payload)
    except (TypeError, ValueError):
        return _emit("manuscript-plan", "blocked", ["paper_brief_invalid"])
    package_value = str(getattr(args, "package", "") or "").strip()
    if not package_value:
        return _emit("manuscript-plan", "blocked", ["evidence_package_invalid"])
    output_value = str(getattr(args, "output", "") or "").strip()
    if not output_value:
        return _emit("manuscript-plan", "blocked", ["manuscript_plan_output_invalid"])
    package_path = Path(package_value).expanduser().resolve()
    output_path = Path(output_value).expanduser().resolve()
    try:
        output_path.relative_to(package_path)
    except ValueError:
        pass
    else:
        return _emit("manuscript-plan", "blocked", ["manuscript_plan_output_invalid"])
    try:
        plan = build_manuscript_plan(package_path, brief)
    except (OSError, TypeError, ValueError, UnicodeError):
        return _emit("manuscript-plan", "blocked", ["evidence_package_invalid"])
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = output_path.with_name(f".{output_path.name}.tmp")
        temporary.write_text(
            json.dumps(plan.to_dict(), ensure_ascii=False, sort_keys=True, allow_nan=False),
            encoding="utf-8",
        )
        temporary.replace(output_path)
    except (OSError, TypeError, ValueError, UnicodeError):
        return _emit("manuscript-plan", "blocked", ["manuscript_plan_output_invalid"])
    return _emit("manuscript-plan", "completed", manuscript_plan={"path": str(output_path), **plan.to_dict()})


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


def _load_figure_selection(path: str | None) -> FigureSelectionRequest | None:
    payload = _read_object(path)
    if payload is None:
        return None
    groups = payload.get("selected_groups")
    if not isinstance(groups, (list, tuple)):
        return None
    try:
        return FigureSelectionRequest.create(
            question=str(payload.get("question", "")),
            selected_groups=tuple(str(value) for value in groups),
            figure_intent=str(payload.get("figure_intent", "describe_group")),
            main_figure_limit=int(payload.get("main_figure_limit", 2)),
        )
    except (TypeError, ValueError):
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


__all__ = ["run_project_workflow", "run_analysis_plan_evaluation"]
