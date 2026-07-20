"""Named export-preset persistence and validation."""

from __future__ import annotations

import json
import os
import tempfile
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from ..utils.config import get_user_config_dir


EXPORT_PRESET_FILENAME = "figure_export_presets.json"
SUPPORTED_EXPORT_FORMATS = frozenset({"png", "svg", "pdf", "origin", "project"})


def export_preset_store_path() -> Path:
    return get_user_config_dir() / EXPORT_PRESET_FILENAME


def validate_export_preset(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Export preset must be a mapping.")
    formats = payload.get("formats", [])
    if not isinstance(formats, (list, tuple)) or not formats:
        raise ValueError("Export preset formats are required.")
    normalized = [str(value or "").strip().lower() for value in formats]
    unsupported = sorted(set(normalized) - SUPPORTED_EXPORT_FORMATS)
    if unsupported:
        raise ValueError(f"unsupported export formats: {', '.join(unsupported)}")
    result = deepcopy(payload)
    result["formats"] = list(dict.fromkeys(normalized))
    if "dpi" in result:
        try:
            dpi = int(result["dpi"])
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("Export preset dpi must be an integer.") from exc
        if dpi <= 0:
            raise ValueError("Export preset dpi must be positive.")
        result["dpi"] = dpi
    return result


def _read_store() -> dict[str, Any]:
    path = export_preset_store_path()
    if not path.exists():
        return {"version": 1, "presets": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {"version": 1, "presets": {}}
    if not isinstance(payload, dict) or not isinstance(payload.get("presets"), dict):
        return {"version": 1, "presets": {}}
    return {"version": 1, "presets": payload["presets"]}


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def save_export_preset(name: str, payload: dict[str, Any]) -> Path:
    preset_name = str(name or "").strip()
    if not preset_name:
        raise ValueError("Export preset name is required.")
    normalized = validate_export_preset(payload)
    normalized["name"] = preset_name
    normalized["updated_at"] = datetime.now().isoformat(timespec="seconds")
    store = _read_store()
    store["presets"][preset_name] = normalized
    path = export_preset_store_path()
    _atomic_write(path, store)
    return path


def list_export_presets() -> list[str]:
    return sorted(_read_store()["presets"].keys(), key=str.casefold)


def load_export_preset(name: str) -> dict[str, Any]:
    payload = _read_store()["presets"].get(str(name or "").strip(), {})
    return deepcopy(payload) if isinstance(payload, dict) else {}


__all__ = [
    "EXPORT_PRESET_FILENAME",
    "SUPPORTED_EXPORT_FORMATS",
    "export_preset_store_path",
    "list_export_presets",
    "load_export_preset",
    "save_export_preset",
    "validate_export_preset",
]
