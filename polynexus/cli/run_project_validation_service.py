"""CLI adapter for project-local validation batch aggregation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from polynexus.core.project_workflow.validation import (
    ProjectValidationEntry,
    run_project_validation_batch,
)
from polynexus.core.project_workflow.workspace import ProjectWorkspace


def run_project_validation_cli(args: Any) -> int:
    try:
        project_root = Path(str(args.project_root)).expanduser().resolve()
        workspace = ProjectWorkspace.open(project_root)
        manifest_payload = _read_json(args.manifest)
        raw_entries = manifest_payload.get("entries")
        if not isinstance(raw_entries, list):
            raise ValueError("project validation manifest requires an entries list")
        entries = tuple(ProjectValidationEntry.from_dict(item) for item in raw_entries)
        batch = run_project_validation_batch(entries)
        report_path = workspace.write_validation_batch(batch)
        payload = batch.to_dict()
        payload["report_path"] = str(report_path)
    except (OSError, TypeError, ValueError, json.JSONDecodeError, StopIteration) as exc:
        payload = {
            "status": "failed",
            "reason_codes": ["project_validation_manifest_invalid"],
            "error": str(exc),
        }
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False))
        return 2
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False))
    return 0 if batch.status == "passed" else 2


def _read_json(path_value: object) -> dict[str, Any]:
    if path_value in (None, ""):
        raise ValueError("project validation manifest path is required")
    payload = json.loads(Path(str(path_value)).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("project validation manifest must be a JSON object")
    return payload


__all__ = ["run_project_validation_cli"]
