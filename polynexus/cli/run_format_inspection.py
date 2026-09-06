"""CLI adapter for the shared raw-format inspection contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from polynexus.core.compute import RawArtifact
from polynexus.core.input_formats import inspect_format


def run_format_inspection(args: Any) -> int:
    source = Path(args.input)
    technique = getattr(args, "technique", "unknown")
    try:
        artifact = RawArtifact.from_path(source, technique=technique)
    except (OSError, ValueError):
        payload = {
            "input": str(source),
            "status": "blocked",
            "reason_codes": ["raw_artifact_unreadable"],
        }
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False))
        return 2
    inspection = inspect_format(
        source,
        technique=technique,
        source_sha256=artifact.sha256,
    )
    payload = inspection.to_dict()
    payload["input"] = str(source)
    if getattr(args, "json", False):
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False))
    else:
        print(f"format: {payload['container_kind']}")
        print(f"status: {payload['status']}")
        print(f"plugin: {payload['plugin_id'] or 'none'}")
        print(f"reader: {payload['reader_availability']}")
        print(f"canonical: {payload['canonical_conversion']}")
        if payload["reason_codes"]:
            print(f"reasons: {', '.join(payload['reason_codes'])}")
        if payload["next_actions"]:
            print(f"next: {', '.join(payload['next_actions'])}")
    return 0 if inspection.status in {"ready", "needs_mapping", "unknown"} else 2
