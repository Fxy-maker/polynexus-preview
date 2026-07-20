"""Validated, data-free chart-template persistence and application."""

from __future__ import annotations

import json
import os
import tempfile
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from ..utils.config import get_user_config_dir


TEMPLATE_FILENAME = "chart_templates.json"
TEMPLATE_VERSION = 1
_SOURCE_KEYS = {"data", "data_ref", "x_column", "y_column", "source_id", "values"}


def template_store_path() -> Path:
    return get_user_config_dir() / TEMPLATE_FILENAME


def _read_store() -> dict[str, Any]:
    path = template_store_path()
    if not path.exists():
        return {"version": TEMPLATE_VERSION, "templates": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {"version": TEMPLATE_VERSION, "templates": {}}
    if not isinstance(payload, dict) or not isinstance(payload.get("templates"), dict):
        return {"version": TEMPLATE_VERSION, "templates": {}}
    return {"version": TEMPLATE_VERSION, "templates": payload["templates"]}


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


def template_from_document(document: dict, name: str) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise ValueError("A figure document mapping is required.")
    template_name = str(name or "").strip()
    if not template_name:
        raise ValueError("Template name is required.")
    objects = []
    for raw in document.get("objects", []):
        if not isinstance(raw, dict):
            continue
        obj = deepcopy(raw)
        for key in _SOURCE_KEYS:
            obj.pop(key, None)
        objects.append(obj)
    return {
        "version": TEMPLATE_VERSION,
        "name": template_name,
        "canvas": deepcopy(document.get("canvas", {})) if isinstance(document.get("canvas"), dict) else {},
        "style": deepcopy(document.get("style", {})) if isinstance(document.get("style"), dict) else {},
        "objects": objects,
    }


def save_template(name: str, template: dict[str, Any]) -> Path:
    template_name = str(name or "").strip()
    if not template_name or not isinstance(template, dict):
        raise ValueError("A template name and mapping are required.")
    payload = deepcopy(template)
    payload["version"] = TEMPLATE_VERSION
    payload["name"] = template_name
    payload["updated_at"] = datetime.now().isoformat(timespec="seconds")
    data = _read_store()
    data["templates"][template_name] = payload
    path = template_store_path()
    _atomic_write(path, data)
    return path


def list_templates() -> list[str]:
    return sorted(_read_store()["templates"].keys(), key=str.casefold)


def load_template(name: str) -> dict[str, Any]:
    template_name = str(name or "").strip()
    payload = _read_store()["templates"].get(template_name, {})
    return deepcopy(payload) if isinstance(payload, dict) else {}


def apply_template(document: dict, template: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(document, dict) or not isinstance(template, dict):
        raise ValueError("A document and template mapping are required.")
    result = deepcopy(document)
    if isinstance(template.get("canvas"), dict):
        result["canvas"] = deepcopy(template["canvas"])
    if isinstance(template.get("style"), dict):
        result["style"] = deepcopy(template["style"])
    current_objects = result.get("objects")
    template_objects = template.get("objects")
    if isinstance(current_objects, list) and isinstance(template_objects, list):
        by_id = {
            str(item.get("id")): item
            for item in current_objects
            if isinstance(item, dict) and str(item.get("id", ""))
        }
        for raw_template in template_objects:
            if not isinstance(raw_template, dict):
                continue
            object_id = str(raw_template.get("id", "") or "")
            current = by_id.get(object_id)
            if current is None:
                current_objects.append(deepcopy(raw_template))
                continue
            preserved = {key: deepcopy(current.get(key)) for key in _SOURCE_KEYS if key in current}
            current.clear()
            current.update(deepcopy(raw_template))
            current.update(preserved)
    return result


__all__ = [
    "TEMPLATE_FILENAME",
    "TEMPLATE_VERSION",
    "apply_template",
    "list_templates",
    "load_template",
    "save_template",
    "template_from_document",
    "template_store_path",
]
