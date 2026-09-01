"""JSON-only CLI adapter for the recoverable Codex/ARS research loop."""

from __future__ import annotations

import json
from contextlib import redirect_stdout
from pathlib import Path
import sys
from typing import Any, Mapping

from polynexus.core.project_workflow.research_loop import ResearchLoopService


_SUCCESS_STATUSES = frozenset(
    {"completed", "draft", "awaiting_mapping_confirmation", "ready", "checkpointed", "ars_in_progress", "awaiting_human", "revision_required", "export_ready"}
)


def run_research_loop(args: Any) -> int:
    """Execute one research-loop operation and print exactly one JSON object."""
    operation = str(getattr(args, "operation", ""))
    project_root = str(getattr(args, "project_root", "") or "").strip()
    if not project_root:
        return _emit(operation, "blocked", ["project_root_required"])
    try:
        service = ResearchLoopService.open(project_root)
    except (OSError, TypeError, ValueError):
        return _emit(operation, "blocked", ["project_root_invalid"])

    try:
        if operation == "create":
            question = str(getattr(args, "question", "") or "").strip()
            project_id = str(getattr(args, "project_id", "") or "").strip()
            if not question or not project_id:
                return _emit(operation, "blocked", ["project_id_and_question_required"])
            task = service.create_task(
                project_id=project_id,
                research_question=question,
                data_scope=tuple(getattr(args, "paths", ()) or ()),
                target_journal=getattr(args, "target_journal", None),
            )
            return _emit(operation, task.status, task=task.to_dict())

        if operation == "list":
            tasks = service.store.list_tasks()
            return _emit(operation, "completed", tasks=[task.to_dict() for task in tasks])

        task_id = str(getattr(args, "task_id", "") or "").strip()
        if not task_id:
            return _emit(operation, "blocked", ["task_id_required"])

        if operation == "resume":
            return _emit(operation, service.resume(task_id).status, task=service.resume(task_id).to_dict())
        if operation == "inspect":
            task = _quiet_call(service.inspect, task_id)
            return _emit(operation, task.status, task=task.to_dict())
        if operation == "propose-mapping":
            mapping = _read_mapping(getattr(args, "mapping", None))
            if mapping is None:
                return _emit(operation, "blocked", ["mapping_invalid"])
            task = service.propose_mapping(task_id, mapping)
            return _emit(operation, task.status, task=task.to_dict())
        if operation == "confirm-mapping":
            task = service.confirm_mapping(
                task_id,
                approved=bool(getattr(args, "approve", False)),
                approver=str(getattr(args, "approver", "") or ""),
                note=str(getattr(args, "note", "") or ""),
            )
            return _emit(operation, task.status, task=task.to_dict())
        if operation == "run":
            task = _quiet_call(service.run, task_id, requested_outputs=tuple(getattr(args, "requested_outputs", ()) or ("figures", "tables", "writing_input")))
            return _emit(operation, task.status, task=task.to_dict())
        if operation == "recompute":
            task = _quiet_call(service.recompute, task_id, requested_outputs=tuple(getattr(args, "requested_outputs", ()) or ("figures", "tables", "writing_input")))
            return _emit(operation, task.status, task=task.to_dict())
        if operation == "checkpoint":
            package = getattr(args, "package", None)
            task = _quiet_call(service.checkpoint, task_id, package_path=package)
            return _emit(operation, task.status, task=task.to_dict())
        if operation == "handoff":
            package = str(getattr(args, "package", "") or "").strip()
            if not package:
                return _emit(operation, "blocked", ["package_required"])
            task = _quiet_call(service.handoff_to_ars, task_id, package)
            return _emit(operation, task.status, task=task.to_dict())
        if operation == "ars-actions":
            actions = _read_list(getattr(args, "actions", None))
            if actions is None:
                return _emit(operation, "blocked", ["actions_invalid"])
            values = _quiet_call(service.record_ars_actions, task_id, actions)
            task = service.resume(task_id)
            return _emit(operation, task.status, task=task.to_dict(), actions=[value.to_dict() for value in values])
        if operation == "resolve-action":
            action_id = str(getattr(args, "action_id", "") or "").strip()
            if not action_id:
                return _emit(operation, "blocked", ["action_id_required"])
            task = _quiet_call(
                service.resolve_action,
                task_id,
                action_id,
                approved=bool(getattr(args, "approve", False)),
                note=str(getattr(args, "note", "") or ""),
            )
            return _emit(operation, task.status, task=task.to_dict())
        if operation == "ars-completion":
            completion = _read_mapping(getattr(args, "ars_completion", None))
            if completion is None:
                return _emit(operation, "blocked", ["ars_completion_invalid"])
            record = _quiet_call(service.record_ars_completion, task_id, completion)
            return _emit(
                operation,
                service.resume(task_id).status,
                task=service.resume(task_id).to_dict(),
                ars_completion=record,
            )
        if operation == "preflight":
            manuscript = _read_mapping(getattr(args, "manuscript", None))
            if manuscript is None:
                return _emit(operation, "blocked", ["manuscript_invalid"])
            report = _quiet_call(service.submission_preflight, task_id, manuscript)
            return _emit(operation, report.status, task=service.resume(task_id).to_dict(), preflight=report.to_dict())
        if operation == "complete-export":
            export_paths = tuple(getattr(args, "export_paths", ()) or ())
            if not export_paths:
                return _emit(operation, "blocked", ["export_paths_required"])
            task = _quiet_call(service.complete_export, task_id, export_paths=export_paths)
            return _emit(operation, task.status, task=task.to_dict())
    except (OSError, TypeError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
        return _emit(operation, "blocked", ["research_loop_invalid"], error=str(exc))

    return _emit(operation, "blocked", ["operation_unknown"])


def _read_mapping(path: str | None) -> Mapping[str, Any] | None:
    if not path:
        return None
    try:
        value = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    except (OSError, UnicodeError, TypeError, ValueError, json.JSONDecodeError):
        return None
    return value if isinstance(value, Mapping) else None


def _read_list(path: str | None) -> list[Mapping[str, Any]] | None:
    value = _read_mapping(path)
    if value is not None:
        raw = value.get("actions", value.get("items"))
    else:
        if not path:
            return None
        try:
            raw = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
        except (OSError, UnicodeError, TypeError, ValueError, json.JSONDecodeError):
            return None
    if not isinstance(raw, list) or any(not isinstance(item, Mapping) for item in raw):
        return None
    return list(raw)


def _emit(operation: str, status: str, reason_codes: list[str] | tuple[str, ...] = (), **payload: Any) -> int:
    envelope: dict[str, Any] = {
        "operation": operation,
        "status": status,
        "reason_codes": list(dict.fromkeys(str(value) for value in reason_codes)),
    }
    envelope.update(payload)
    print(json.dumps(envelope, ensure_ascii=False, sort_keys=True, allow_nan=False))
    return 0 if status in _SUCCESS_STATUSES else 2


def _quiet_call(function: Any, *args: Any, **kwargs: Any) -> Any:
    """Keep the machine-readable stdout channel free of provider progress."""
    with redirect_stdout(sys.stderr):
        return function(*args, **kwargs)


__all__ = ["run_research_loop"]
