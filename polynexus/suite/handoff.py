"""Suite-level handoff projections for writing skills and ARS actions."""

from __future__ import annotations

import json
import hashlib
import math
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

from polynexus.core.project_workflow.evidence_view import load_evidence_package_view
from polynexus.core.project_workflow.models import canonical_json
from .paper_contracts import stable_id


ARS_ACTION_KINDS = frozenset({"edit", "recompute", "ask_human"})
_ARS_ACTION_STATES = frozenset({"pending", "resolved", "rejected"})
_SAFE_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")


def _json_value(value: Any, *, label: str) -> Any:
    """Return a strict JSON value without accepting NaN or opaque objects."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{label} is not JSON-safe")
        return value
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            text = str(key)
            if not text:
                raise ValueError(f"{label} is not JSON-safe")
            result[text] = _json_value(item, label=label)
        return result
    if isinstance(value, (tuple, list)):
        return [_json_value(item, label=label) for item in value]
    raise ValueError(f"{label} is not JSON-safe")


def _task_id(value: Any, *, required: bool) -> str:
    text = "" if value is None else str(value).strip()
    if not text:
        if required:
            raise ValueError("ARS action task id is invalid")
        return ""
    if not _SAFE_IDENTIFIER.fullmatch(text):
        raise ValueError("ARS action task id is invalid")
    return text


def validate_ars_action(
    action: Mapping[str, Any] | Any,
    *,
    task_id: str | None = None,
) -> dict[str, Any]:
    """Validate one ARS return action and bind it to one research task.

    The Suite boundary deliberately returns a normalized JSON mapping rather
    than a second persisted action class.  ``ResearchAction`` remains the
    project-level durable contract; this function only validates untrusted ARS
    output before that contract is constructed.
    """
    if not isinstance(action, Mapping) and hasattr(action, "to_dict"):
        action = action.to_dict()
    if not isinstance(action, Mapping):
        raise ValueError("ARS action is invalid")

    kind = str(action.get("kind", "")).strip().lower()
    if kind not in ARS_ACTION_KINDS:
        raise ValueError("ARS action kind is invalid")

    expected_task_id = _task_id(task_id, required=False)
    declared_task_id = _task_id(action.get("task_id"), required=False)
    if expected_task_id and declared_task_id and expected_task_id != declared_task_id:
        raise ValueError("ARS action belongs to another task")
    bound_task_id = declared_task_id or expected_task_id
    if not bound_task_id:
        raise ValueError("ARS action task id is invalid")

    payload = action.get("payload", {})
    if not isinstance(payload, Mapping):
        raise ValueError("ARS action payload is invalid")
    try:
        normalized_payload = _json_value(payload, label="ARS action payload")
        json.dumps(normalized_payload, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("ARS action payload is invalid") from exc

    normalized: dict[str, Any] = {
        "kind": kind,
        "payload": normalized_payload,
        "task_id": bound_task_id,
    }
    if "action_id" in action:
        action_id = str(action.get("action_id", "")).strip()
        if not _SAFE_IDENTIFIER.fullmatch(action_id):
            raise ValueError("ARS action id is invalid")
        normalized["action_id"] = action_id
    if "status" in action:
        status = str(action.get("status", "")).strip().lower()
        if status not in _ARS_ACTION_STATES:
            raise ValueError("ARS action status is invalid")
        normalized["status"] = status
    return normalized


def validate_ars_actions(
    actions: Iterable[Mapping[str, Any] | Any],
    *,
    task_id: str | None = None,
) -> tuple[dict[str, Any], ...]:
    """Validate an ordered, single-task ARS action batch."""
    if isinstance(actions, (str, bytes, Mapping)):
        raise ValueError("ARS action list is invalid")
    try:
        values = tuple(validate_ars_action(item, task_id=task_id) for item in actions)
    except TypeError as exc:
        raise ValueError("ARS action list is invalid") from exc
    task_ids = {item["task_id"] for item in values}
    if len(task_ids) > 1:
        raise ValueError("ARS actions belong to multiple tasks")
    return values


def build_suite_handoff(
    package_path: str | Path,
    *,
    task_id: str | None = None,
    actions: Iterable[Mapping[str, Any] | Any] | None = None,
) -> dict[str, Any]:
    """Validate an evidence package and return package-relative skill inputs.

    ``task_id`` and ``actions`` are additive.  Existing package-only callers
    receive the same file projection, while a recoverable research loop can
    persist this return value as a task-bound handoff record.
    """
    root = Path(package_path).expanduser().resolve()
    try:
        view = load_evidence_package_view(root)
    except (OSError, ValueError) as exc:
        return {
            "status": "blocked",
            "reason_codes": ["evidence_package_invalid"],
            "package": str(root),
            "error": str(exc),
        }
    files = {
        "ars_writing_input": "ars-writing-input.json",
        "result_tables": "result-tables.json",
        "writing_evidence": "writing-evidence.json",
        "evidence": "evidence.json",
        "citation_metrics": "citation-metrics.json",
        "figure_index": "figure-index.json",
    }
    optional = {"review_decisions": "review-decision.json"}
    missing = [name for name, relative in files.items() if not (root / relative).is_file()]
    if missing:
        return {"status": "blocked", "reason_codes": ["evidence_package_invalid", "handoff_file_missing"], "missing": missing, "package": str(root)}
    try:
        manifest_hash = _validate_package_integrity(root)
    except ValueError as exc:
        return {
            "status": "blocked",
            "reason_codes": ["evidence_package_invalid", "evidence_package_integrity_invalid"],
            "package": str(root),
            "error": str(exc),
        }
    try:
        bound_task_id = _task_id(task_id, required=actions is not None)
        action_values = validate_ars_actions(actions, task_id=bound_task_id) if actions is not None else ()
    except ValueError as exc:
        return {
            "status": "blocked",
            "reason_codes": ["ars_action_invalid"],
            "package": str(root),
            "error": str(exc),
        }
    identity = {
        "package_id": view.package_id,
        "package_version": view.version,
        "package_hash": manifest_hash,
        "task_id": bound_task_id or None,
        "files": files,
        "actions": list(action_values),
    }
    payload: dict[str, Any] = {
        "version": 1,
        "status": "ready",
        "handoff_id": stable_id("handoff", identity),
        "package": {
            "path": str(root),
            "package_id": view.package_id,
            "version": view.version,
            "status": view.status,
            "handoff_schema": "v1",
        },
        "files": files,
        "human_review_required": bool(view.human_review) or view.status == "review_required",
        "human_review_count": len(view.human_review),
        "techniques": [item.key for item in view.techniques],
        "run_ids": list(view.run_ids),
        "metric_count": len(view.metrics),
    }
    if manifest_hash:
        payload["package"]["package_hash"] = manifest_hash
    if bound_task_id:
        payload["task_id"] = bound_task_id
    if actions is not None:
        payload["actions"] = list(action_values)
    if (root / optional["review_decisions"]).is_file():
        payload["files"]["review_decisions"] = optional["review_decisions"]
    return payload


def _manifest_package_hash(root: Path) -> str:
    try:
        payload = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return ""
    if not isinstance(payload, Mapping):
        return ""
    value = str(payload.get("package_hash", "")).strip().lower()
    if not value:
        return ""
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        return ""
    return value


def _validate_package_integrity(root: Path) -> str:
    """Validate the packager's content hash and copied-asset hashes.

    Older handoff fixtures may not carry a package hash, so an absent field is
    treated as a legacy package.  Whenever the field is present, every hash is
    checked before ARS receives the projection.
    """
    manifest_path = root / "manifest.json"
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("package manifest is invalid") from exc
    if not isinstance(payload, Mapping):
        raise ValueError("package manifest is invalid")
    declared = str(payload.get("package_hash", "")).strip().lower()
    if not declared:
        return ""
    if len(declared) != 64 or any(char not in "0123456789abcdef" for char in declared):
        raise ValueError("package hash is invalid")
    unsigned = dict(payload)
    unsigned.pop("package_hash", None)
    expected = hashlib.sha256(canonical_json(unsigned).encode("utf-8")).hexdigest()
    if declared != expected:
        raise ValueError("package hash does not match its manifest")
    records = payload.get("artifact_hashes", ())
    if not isinstance(records, list):
        raise ValueError("package artifact hashes are invalid")
    for record in records:
        if not isinstance(record, Mapping):
            raise ValueError("package artifact hash record is invalid")
        relative = str(record.get("path", ""))
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError as exc:
            raise ValueError("package artifact path escapes package") from exc
        if not candidate.is_file():
            raise ValueError(f"package artifact is missing: {relative}")
        expected_file = str(record.get("sha256", "")).lower()
        actual_file = _sha256_file(candidate)
        if expected_file != actual_file:
            raise ValueError(f"package artifact hash does not match: {relative}")
    return declared


def _sha256_file(path: Path) -> str:
    """Hash package content incrementally so multi-gigabyte packages stay bounded."""
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise ValueError(f"package artifact is unreadable: {path.name}") from exc
    return digest.hexdigest()


__all__ = [
    "ARS_ACTION_KINDS",
    "build_suite_handoff",
    "validate_ars_action",
    "validate_ars_actions",
]
