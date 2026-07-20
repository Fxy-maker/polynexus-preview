"""Validated style bundles used by the chart-editor format painter."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from .figure_edit_capabilities import capabilities_for


_STYLE_CAPABILITY_NAMES = {
    "color": "color",
    "line_width": "line_width",
    "line_style": "line_style",
    "marker": "marker",
    "marker_size": "marker_size",
    "font_size": "font_size",
    "alpha": "style",
    "fill": "style",
    "stroke": "style",
}


@dataclass(frozen=True)
class StyleApplyResult:
    object: dict[str, Any]
    applied: tuple[str, ...] = ()
    skipped: tuple[str, ...] = ()
    changed: bool = False


def capture_style_bundle(object_payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(object_payload, dict):
        raise ValueError("An object mapping is required.")
    style = object_payload.get("style", {})
    return {
        "version": 1,
        "object_type": str(object_payload.get("type", "unknown") or "unknown"),
        "style": deepcopy(style) if isinstance(style, dict) else {},
    }


def apply_style_bundle(object_payload: dict[str, Any], bundle: dict[str, Any]) -> StyleApplyResult:
    if not isinstance(object_payload, dict) or not isinstance(bundle, dict):
        raise ValueError("An object and style bundle mapping are required.")
    source_style = bundle.get("style", {})
    if not isinstance(source_style, dict):
        return StyleApplyResult(deepcopy(object_payload))
    result = deepcopy(object_payload)
    target_style = result.get("style")
    if not isinstance(target_style, dict):
        target_style = {}
    capabilities = capabilities_for(result)
    applied = []
    skipped = []
    for key, value in source_style.items():
        capability_name = _STYLE_CAPABILITY_NAMES.get(str(key))
        if capability_name is None or not getattr(capabilities, capability_name, False):
            skipped.append(str(key))
            continue
        if target_style.get(key) != value:
            target_style[key] = deepcopy(value)
        applied.append(str(key))
    result["style"] = target_style
    return StyleApplyResult(
        object=result,
        applied=tuple(applied),
        skipped=tuple(skipped),
        changed=result != object_payload,
    )


__all__ = ["StyleApplyResult", "apply_style_bundle", "capture_style_bundle"]
