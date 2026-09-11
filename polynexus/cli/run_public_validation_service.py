"""CLI adapter for hash-bound external public validation replay."""

from __future__ import annotations

import json
import io
from pathlib import Path
from typing import Any
from contextlib import redirect_stdout

from polynexus.core.project_workflow.workspace import ProjectWorkspace
from polynexus.core.public_validation import (
    load_public_validation_manifest,
    run_public_validation_manifest,
)


def run_public_validation_cli(args: Any) -> int:
    try:
        manifest = load_public_validation_manifest(args.manifest)
        # Several legacy technique providers still print progress to stdout.
        # This machine-facing command must emit exactly one JSON envelope.
        with redirect_stdout(io.StringIO()):
            batch = run_public_validation_manifest(
                manifest,
                data_root=Path(str(args.data_root)).expanduser(),
            )
        report_path = None
        if getattr(args, "project_root", None):
            report_path = ProjectWorkspace.open(args.project_root).write_validation_batch(batch)
        payload = batch.to_dict()
        if report_path is not None:
            payload["report_path"] = str(report_path)
    except (OSError, TypeError, ValueError, KeyError, StopIteration, json.JSONDecodeError) as exc:
        payload = {
            "status": "failed",
            "reason_codes": ["public_validation_manifest_invalid"],
            "error": str(exc),
        }
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False))
        return 2
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False))
    return 0 if batch.status == "passed" else 2


__all__ = ["run_public_validation_cli"]
