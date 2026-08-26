"""Shared raw-artifact identity primitives used by all entry points."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


def raw_artifact_id(
    path: str | Path,
    *,
    technique: str,
    format: str,
    sha256: str | None,
    observed_facts: Mapping[str, Any] | None = None,
) -> str:
    """Return the stable identity for one source artifact.

    Agent recipes and direct ComputeRuns intentionally share this exact
    content-addressed identity.  The function accepts only the public fields
    that define an artifact; callers remain responsible for reading and
    validating the source before invoking it.
    """
    payload = {
        "kind": "raw_artifact",
        "path": str(Path(path).expanduser().resolve(strict=False)),
        "technique": str(technique),
        "format": str(format),
        "sha256": sha256,
        "observed_facts": dict(observed_facts or {}),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


__all__ = ["raw_artifact_id"]
