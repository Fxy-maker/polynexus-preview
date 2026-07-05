"""JSON-friendly figure annotation state helpers."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List


KNOWN_ANNOTATION_TYPES = {"text", "arrow", "line", "rectangle", "highlight"}


def load_annotations_from_entry(entry: Dict[str, Any]) -> List[dict]:
    annotations = entry.get("annotations", []) if isinstance(entry, dict) else []
    if not isinstance(annotations, list):
        return []
    return [
        normalize_annotation_payload(item)
        for item in annotations
        if isinstance(item, dict)
    ]


def save_annotations_to_entry(entry: Dict[str, Any], annotations: List[dict]) -> Dict[str, Any]:
    updated = deepcopy(entry) if isinstance(entry, dict) else {}
    updated["annotations"] = [
        normalize_annotation_payload(item)
        for item in annotations
        if isinstance(item, dict)
    ]
    return updated


def normalize_annotation_payload(payload: Dict[str, Any]) -> dict:
    annotation = deepcopy(payload)
    raw_type = str(annotation.get("type") or "").strip().lower()
    if raw_type not in KNOWN_ANNOTATION_TYPES:
        annotation["original_type"] = raw_type
        annotation["type"] = "unknown"
    else:
        annotation["type"] = raw_type
    annotation.setdefault("id", "")
    return annotation
