"""Manifest and lock-file handling for Suite components."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from .contracts import SuiteComponent, SuiteManifest


def load_manifest(path: str | Path) -> SuiteManifest:
    source = Path(path).expanduser()
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("suite manifest is invalid") from exc
    if not isinstance(payload, Mapping) or payload.get("schema_version") != 1:
        raise ValueError("suite manifest schema_version must be 1")
    raw_components = payload.get("components")
    if not isinstance(raw_components, list) or not raw_components:
        raise ValueError("suite manifest requires at least one component")
    components: list[SuiteComponent] = []
    seen: set[str] = set()
    for raw in raw_components:
        if not isinstance(raw, Mapping):
            raise ValueError("suite manifest component is invalid")
        component_id = str(raw.get("id", "")).strip()
        version = str(raw.get("version", "")).strip()
        destination = str(raw.get("destination", "")).strip()
        source_url = str(raw.get("source", "")).strip()
        sha256 = str(raw.get("sha256", "")).strip().lower()
        required = raw.get("required_files", ())
        if not component_id or component_id in seen or not version or not destination or not source_url:
            raise ValueError("suite manifest component identity is invalid")
        if Path(destination).is_absolute() or destination in {".", ".."}:
            raise ValueError("suite manifest destination must be relative")
        if not isinstance(required, list) or any(
            not str(item).strip() or Path(str(item)).is_absolute() or ".." in Path(str(item)).parts
            for item in required
        ):
            raise ValueError("suite manifest required_files are invalid")
        if len(sha256) != 64 or any(char not in "0123456789abcdef" for char in sha256):
            raise ValueError("suite manifest sha256 is invalid")
        seen.add(component_id)
        components.append(SuiteComponent(
            component_id=component_id,
            version=version,
            destination=destination,
            required_files=tuple(str(item).strip() for item in required),
            source=source_url,
            sha256=sha256,
            core_range=str(raw.get("core_range", "")).strip(),
            handoff_schema=str(raw.get("handoff_schema", "v1")).strip() or "v1",
        ))
    return SuiteManifest(schema_version=1, components=tuple(components))


def load_lock(path: str | Path) -> dict[str, Any]:
    target = Path(path).expanduser()
    if not target.is_file():
        return {}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("suite lock is invalid") from exc
    if not isinstance(payload, dict):
        raise ValueError("suite lock is invalid")
    return payload


def write_lock(path: str | Path, payload: Mapping[str, Any]) -> None:
    if not isinstance(payload, Mapping):
        raise ValueError("suite lock payload is invalid")
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, target)


__all__ = ["load_manifest", "load_lock", "write_lock"]
