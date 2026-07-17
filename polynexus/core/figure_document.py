"""Editable figure document helpers.

The document is the long-term editing truth for Origin-style figure editing.
It stays JSON-friendly so UI, sidecar migration, and exporters can evolve
without binding the schema to a Qt widget implementation.
"""

from __future__ import annotations

import json
import math
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .figure_objects import GEOMETRY_KEYS, normalize_figure_object, style_from_payload


DOCUMENT_VERSION = 1
STATIC_BACKGROUND_MODE = "static_background"
OBJECT_MODE = "object"


def figure_document_path(figure_path: str) -> Path:
    return Path(figure_path).resolve().with_suffix(".pnfig.json")


def create_static_figure_document(
    figure_path: str,
    asset_spec: dict | None = None,
    style: dict | None = None,
    annotations: list[dict] | None = None,
) -> dict:
    source = Path(figure_path).resolve()
    spec = deepcopy(asset_spec) if isinstance(asset_spec, dict) else {}
    figure_id = str(spec.get("figure_id") or source.stem)
    width_px = int(spec.get("width_px", 0) or 0)
    height_px = int(spec.get("height_px", 0) or 0)
    objects = [_image_background_object(source, spec)]
    objects.extend(
        annotation_to_figure_object(annotation)
        for annotation in (annotations or [])
        if isinstance(annotation, dict)
    )

    return {
        "version": DOCUMENT_VERSION,
        "figure_id": figure_id,
        "mode": STATIC_BACKGROUND_MODE,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "canvas": {
            "width_px": width_px,
            "height_px": height_px,
            "dpi": int(spec.get("dpi", 0) or 0),
            "background": str(spec.get("background") or "#FFFFFF"),
        },
        "asset_spec": spec,
        "style": deepcopy(style) if isinstance(style, dict) else {},
        "layers": [
            {
                "id": "layer-1",
                "name": "Layer 1",
                "visible": True,
                "locked": False,
                "object_ids": [obj["id"] for obj in objects],
            }
        ],
        "objects": objects,
        "data_sources": [],
        "export": {
            "formats": ["png", "svg", "pdf"],
            "last_exported": {},
        },
    }


def create_generated_figure_document(
    figure_path: str,
    *,
    technique: str = "",
    figure_id: str = "",
    data_sources: list[dict] | None = None,
    recipe: dict | None = None,
    style: dict | None = None,
    objects: list[dict] | None = None,
    canvas: dict | None = None,
) -> dict:
    source = Path(figure_path).resolve()
    figure_objects = [
        normalize_figure_object(obj)
        for obj in (objects or [])
        if isinstance(obj, dict)
    ]
    return {
        "version": DOCUMENT_VERSION,
        "figure_id": str(figure_id or source.stem),
        "mode": OBJECT_MODE,
        "technique": str(technique or ""),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "canvas": deepcopy(canvas) if isinstance(canvas, dict) else {},
        "asset_spec": {},
        "style": deepcopy(style) if isinstance(style, dict) else {},
        "layers": [
            {
                "id": "layer-1",
                "name": "Layer 1",
                "visible": True,
                "locked": False,
                "object_ids": [obj["id"] for obj in figure_objects],
            }
        ],
        "objects": figure_objects,
        "data_sources": [
            _normalize_data_source(source_data)
            for source_data in (data_sources or [])
            if isinstance(source_data, dict)
        ],
        "recipe": _normalize_recipe(recipe),
        "export": {
            "formats": ["png", "svg", "pdf"],
            "last_exported": {source.suffix.lower().lstrip(".") or "figure": str(source)},
        },
    }


def annotation_to_figure_object(annotation: dict) -> dict:
    raw = deepcopy(annotation) if isinstance(annotation, dict) else {}
    kind = str(raw.get("type") or "unknown").strip().lower()
    obj = {
        "id": str(raw.get("id") or f"obj-{uuid4().hex[:12]}"),
        "type": kind,
        "name": _annotation_name(kind),
        "visible": True,
        "locked": False,
        "z_index": int(raw.get("z_index", 0) or 0),
        "bounds": _annotation_bounds(raw),
        "style": style_from_payload(raw),
    }
    for key, value in raw.items():
        if key in {"type", "name", "visible", "locked", "z_index", "bounds", "style"}:
            continue
        if key in obj["style"]:
            continue
        obj[key] = deepcopy(value)
    return normalize_figure_object(obj)


def save_figure_document(figure_path: str, document: dict) -> Path:
    path = figure_document_path(figure_path)
    payload = normalize_figure_document(document)
    payload["updated_at"] = datetime.now().isoformat(timespec="seconds")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    return path


def save_generated_figure_document(
    figure_path: str,
    *,
    technique: str = "",
    figure_id: str = "",
    data_sources: list[dict] | None = None,
    recipe: dict | None = None,
    style: dict | None = None,
    objects: list[dict] | None = None,
    canvas: dict | None = None,
) -> Path:
    document = create_generated_figure_document(
        figure_path,
        technique=technique,
        figure_id=figure_id,
        data_sources=data_sources,
        recipe=recipe,
        style=style,
        objects=objects,
        canvas=canvas,
    )
    path = save_figure_document(figure_path, document)
    from .plot_edits import save_figure_document_path

    save_figure_document_path(figure_path, str(path))
    return path


def load_figure_document(figure_path: str) -> dict:
    source_path = Path(figure_path).resolve()
    is_document_path = source_path.name.lower().endswith(".pnfig.json")
    path = source_path if is_document_path else figure_document_path(figure_path)
    if not path.exists() and not is_document_path:
        try:
            from .plot_edits import load_figure_document_path

            recorded_path = str(load_figure_document_path(figure_path) or "").strip()
            if recorded_path:
                candidate = Path(recorded_path)
                if candidate.exists():
                    path = candidate
        except Exception:
            path = figure_document_path(figure_path)
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception:
        return {}
    return normalize_figure_document(payload)


def normalize_figure_document(payload: dict[str, Any]) -> dict:
    document = deepcopy(payload) if isinstance(payload, dict) else {}
    try:
        document["version"] = int(document.get("version", DOCUMENT_VERSION) or DOCUMENT_VERSION)
    except (TypeError, ValueError, OverflowError):
        document["version"] = DOCUMENT_VERSION
    document.setdefault("figure_id", "")
    document.setdefault("mode", OBJECT_MODE)
    document.setdefault("created_at", document.get("updated_at", ""))
    document.setdefault("updated_at", "")
    if not isinstance(document.get("canvas"), dict):
        document["canvas"] = {}
    if not isinstance(document.get("asset_spec"), dict):
        document["asset_spec"] = {}
    if not isinstance(document.get("style"), dict):
        document["style"] = {}
    if not isinstance(document.get("layers"), list):
        document["layers"] = []
    document.setdefault("technique", "")
    document.setdefault("publication_role", "si")
    document["recipe"] = _normalize_recipe(document.get("recipe", {}))
    objects = document.get("objects")
    document["objects"] = [
        normalize_figure_object(obj)
        for obj in (objects if isinstance(objects, list) else [])
        if isinstance(obj, dict)
    ]
    data_sources = document.get("data_sources")
    document["data_sources"] = [
        _normalize_data_source(source)
        for source in (data_sources if isinstance(data_sources, list) else [])
        if isinstance(source, dict)
    ]
    document.setdefault("export", {"formats": ["png", "svg", "pdf"], "last_exported": {}})
    return document


def _normalize_data_source(source: dict) -> dict:
    normalized = deepcopy(source) if isinstance(source, dict) else {}
    normalized.setdefault("id", f"data-{uuid4().hex[:12]}")
    normalized.setdefault("kind", "")
    normalized.setdefault("role", "")
    path = str(normalized.get("path") or "").strip()
    path_kind = str(normalized.get("path_kind") or "").strip().lower()
    if path and path_kind == "run_relative":
        normalized["path"] = Path(path).as_posix()
    elif path:
        normalized["path"] = str(Path(path).resolve())
    return normalized


def _normalize_recipe(recipe: dict | None) -> dict:
    normalized = deepcopy(recipe) if isinstance(recipe, dict) else {}
    normalized.setdefault("module", "")
    normalized.setdefault("function", "")
    normalized.setdefault("inputs", {})
    normalized.setdefault("parameters", {})
    return normalized


def _image_background_object(source: Path, asset_spec: dict) -> dict:
    return normalize_figure_object(
        {
            "id": "background",
            "type": "image_background",
            "name": "Background",
            "visible": True,
            "locked": True,
            "z_index": -1000,
            "bounds": {
                "x": 0.0,
                "y": 0.0,
                "width": 1.0,
                "height": 1.0,
            },
            "style": {"alpha": 1.0},
            "source_path": str(source),
            "asset_spec": deepcopy(asset_spec) if isinstance(asset_spec, dict) else {},
        }
    )


def _annotation_name(kind: str) -> str:
    return {
        "text": "Text",
        "arrow": "Arrow",
        "line": "Line",
        "rectangle": "Rectangle",
        "highlight": "Highlight",
    }.get(kind, "Annotation")


def _annotation_bounds(annotation: dict) -> dict:
    bounds = {}
    for key in GEOMETRY_KEYS:
        if key not in annotation:
            continue
        try:
            value = float(annotation[key])
        except (TypeError, ValueError, OverflowError):
            continue
        if math.isfinite(value):
            bounds[key] = value
    return bounds
