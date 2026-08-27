"""Shared raw-artifact identity primitives used by all entry points."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Any, Mapping


def directory_manifest_entries(path: str | Path) -> list[dict[str, str]]:
    """Collect validated recursive directory entries for all entry points."""
    root = Path(path).expanduser().resolve(strict=False)
    root_stat = root.lstat()
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)

    def is_reparse(value: os.stat_result) -> bool:
        return bool(getattr(value, "st_file_attributes", 0) & reparse)

    if not stat.S_ISDIR(root_stat.st_mode) or is_reparse(root_stat):
        raise OSError("directory source is not a regular directory")
    entries: list[dict[str, str]] = []

    def collect(directory: Path) -> None:
        directory_stat = directory.lstat()
        if not stat.S_ISDIR(directory_stat.st_mode) or is_reparse(directory_stat):
            raise OSError("directory source contains unsupported directory")
        children = list(directory.iterdir())
        if not children:
            raise OSError("directory source contains an empty directory")
        for child in children:
            child_stat = child.lstat()
            if is_reparse(child_stat):
                raise OSError("directory source contains a symlink or reparse point")
            if stat.S_ISDIR(child_stat.st_mode):
                collect(child)
            elif stat.S_ISREG(child_stat.st_mode):
                entries.append({
                    "path": child.relative_to(root).as_posix(),
                    "sha256": hashlib.sha256(child.read_bytes()).hexdigest(),
                })
            else:
                raise OSError("directory source contains unsupported entry")

    collect(root)
    if not entries:
        raise OSError("directory source contains no files")
    entries.sort(key=lambda entry: entry["path"])
    return entries


def directory_manifest_sha256(entries: list[Mapping[str, str]] | tuple[Mapping[str, str], ...]) -> str:
    """Hash a directory manifest using the shared canonical serialization."""
    normalized = [
        {"path": str(entry["path"]), "sha256": str(entry["sha256"])}
        for entry in entries
    ]
    normalized.sort(key=lambda entry: entry["path"])
    payload = {"kind": "directory_manifest", "entries": normalized}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


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


__all__ = ["directory_manifest_entries", "directory_manifest_sha256", "raw_artifact_id"]
