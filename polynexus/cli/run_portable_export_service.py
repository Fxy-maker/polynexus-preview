"""CLI adapter for source-bound vendor portable exports."""

from __future__ import annotations

import json
import io
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any

from polynexus.core.canonical_experiments import MappingProposal, default_converter_registry
from polynexus.core.compute import ComputeRunService, RawArtifact


def run_portable_export(args: Any) -> int:
    raw_source = Path(args.raw_source)
    export_path = Path(args.export)
    technique = str(args.technique or "").strip().lower()
    try:
        raw_artifact = RawArtifact.from_path(raw_source, technique=technique)
        mapping = _load_mapping(getattr(args, "mapping_proposal", None))
        outcome = default_converter_registry().convert_portable_export(
            raw_source,
            export_path,
            technique=technique,
            source_artifact_id=raw_artifact.artifact_id,
            exporter=str(args.exporter),
            mapping_proposal=mapping,
        )
    except (OSError, TypeError, ValueError) as exc:
        payload = {
            "status": "blocked",
            "reason_codes": ["portable_export_invalid"],
            "error": str(exc),
            "raw_artifact": None,
        }
        return _emit(payload, json_output=bool(getattr(args, "json", False)), exit_code=2)

    payload: dict[str, Any] = {
        "status": outcome.status,
        "reason_codes": list(outcome.reason_codes),
        "record": outcome.record.to_dict(),
        "raw_artifact": {
            "artifact_id": raw_artifact.artifact_id,
            "path": raw_artifact.path,
            "technique": raw_artifact.technique,
            "format": raw_artifact.format,
            "sha256": raw_artifact.sha256,
            "observed_facts": dict(raw_artifact.observed_facts),
        },
    }
    if outcome.template is not None:
        payload["canonical_template"] = outcome.template.to_dict()

    if outcome.status == "ready" and not bool(getattr(args, "convert_only", False)):
        output_dir = str(args.output or (export_path.parent / "polynexus_portable_export_results"))
        run_kwargs = {
            "technique": technique,
            "path": export_path,
            "output_dir": output_dir,
            "source_artifact_id": raw_artifact.artifact_id,
            "canonical_template": outcome.template,
        }
        if bool(getattr(args, "json", False)):
            with redirect_stdout(io.StringIO()):
                run = ComputeRunService().run_direct(**run_kwargs)
        else:
            run = ComputeRunService().run_direct(**run_kwargs)
        payload["compute_run"] = run.to_dict()
        if run.status != "completed":
            payload["status"] = run.status
            payload["reason_codes"] = list(run.reasons)

    return _emit(
        payload,
        json_output=bool(getattr(args, "json", False)),
        exit_code=0 if payload["status"] in {"ready", "completed", "review_required"} else 2,
    )


def _load_mapping(value: object) -> MappingProposal | None:
    if value in (None, ""):
        return None
    path = Path(str(value))
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("mapping proposal must be a JSON object")
    return MappingProposal.from_dict(payload)


def _emit(payload: dict[str, Any], *, json_output: bool, exit_code: int) -> int:
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False))
    else:
        print(f"status: {payload['status']}")
        if payload.get("reason_codes"):
            print(f"reasons: {', '.join(payload['reason_codes'])}")
        template = payload.get("canonical_template")
        if isinstance(template, dict):
            print(f"template: {template.get('template_id', '')}")
        run = payload.get("compute_run")
        if isinstance(run, dict):
            print(f"compute_run: {run.get('status', '')}")
    return exit_code


__all__ = ["run_portable_export"]
