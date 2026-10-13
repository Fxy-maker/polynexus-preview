"""CLI adapter for aggregate validation-suite evidence reports."""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
from typing import Any

from polynexus.core.project_workflow.workspace import ProjectWorkspace
from polynexus.core.public_validation import (
    load_public_validation_manifest,
    run_public_validation_manifest,
)
from polynexus.core.validation_suite import build_validation_suite_report


def run_validation_suite_cli(args: Any) -> int:
    """Build one report from existing public replay and smoke projections."""

    try:
        replay_batch = None
        replay_manifest = getattr(args, "public_replay_manifest", None)
        if replay_manifest:
            data_root = getattr(args, "data_root", None)
            if not data_root:
                raise ValueError("--data-root is required with --public-replay-manifest")
            manifest = load_public_validation_manifest(replay_manifest)
            # Legacy providers may print progress; preserve the one-JSON-line
            # contract of this machine-facing command.
            with redirect_stdout(io.StringIO()):
                replay_batch = run_public_validation_manifest(
                    manifest,
                    data_root=Path(str(data_root)).expanduser(),
                )

        smoke_report = None
        smoke_path = getattr(args, "smoke_report", None)
        if smoke_path:
            smoke_report = _read_json(smoke_path, "smoke report")

        report = build_validation_suite_report(
            suite_id=getattr(args, "suite_id", None) or "polynexus-validation-suite-v1",
            replay_batch=replay_batch,
            replay_source_ref=str(replay_manifest or "public-replay-batch"),
            smoke_report=smoke_report,
            smoke_source_ref=str(smoke_path or "all-module-smoke-report"),
        )

        report_path = None
        project_root = getattr(args, "project_root", None)
        output_path = getattr(args, "output", None)
        if project_root and output_path:
            raise ValueError("--project-root and --output are mutually exclusive")
        if project_root:
            report_path = ProjectWorkspace.open(project_root).write_validation_suite(report)
        elif output_path:
            report_path = _write_json(output_path, report.to_dict())

        payload = report.to_dict()
        if report_path is not None:
            payload["report_path"] = str(report_path)
    except (OSError, TypeError, ValueError, KeyError, StopIteration, json.JSONDecodeError) as exc:
        payload = {
            "status": "failed",
            "reason_codes": ["validation_suite_input_invalid"],
            "error": str(exc),
        }
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False))
        return 2
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False))
    return 0 if report.status != "failed" else 2


def _read_json(path_value: object, label: str) -> dict[str, Any]:
    if path_value in (None, ""):
        raise ValueError(f"{label} path is required")
    value = json.loads(Path(str(path_value)).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _write_json(path_value: object, payload: dict[str, Any]) -> Path:
    if path_value in (None, ""):
        raise ValueError("output path is required")
    destination = Path(str(path_value)).expanduser().resolve()
    if destination.exists() and destination.is_dir():
        raise ValueError("output path must be a file")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        handle.write("\n")
        handle.flush()
    try:
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


__all__ = ["run_validation_suite_cli"]
