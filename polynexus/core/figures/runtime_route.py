"""Explicit capability-gated routing between V2 and legacy figure runtimes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class FigureRuntimeRoute:
    name: str
    reason_code: str
    v2_ready: bool
    static_fallback: bool


def resolve_runtime_route(capability: Mapping[str, Any] | None) -> FigureRuntimeRoute:
    """Resolve one route without silently upgrading or downgrading a document.

    ``v2_default`` is an explicit product switch, but it is not sufficient by
    itself: a human-reviewed capability must also set ``v2_reviewed``. This
    keeps a copied or prematurely edited manifest on the legacy route.
    """

    capability = capability or {}
    v2_ready = str(capability.get("v2_runtime") or "") == "ready"
    v2_default = bool(capability.get("v2_default", False))
    v2_reviewed = bool(capability.get("v2_reviewed", False))
    if v2_ready and v2_default and not v2_reviewed:
        if str(capability.get("editing_mode") or "") == "object" and bool(
            capability.get("object_editing", False)
        ):
            return FigureRuntimeRoute(
                "legacy_object",
                "v2_default_review_pending",
                True,
                False,
            )
    if v2_ready and v2_default and v2_reviewed:
        return FigureRuntimeRoute("reactive_v2", "v2_default_enabled", True, False)
    if v2_ready and not v2_default:
        if str(capability.get("editing_mode") or "") == "object" and bool(
            capability.get("object_editing", False)
        ):
            return FigureRuntimeRoute("legacy_object", "v2_default_disabled", True, False)
    if str(capability.get("editing_mode") or "") == "object" and bool(
        capability.get("object_editing", False)
    ):
        return FigureRuntimeRoute("legacy_object", "legacy_object_capability", False, False)
    return FigureRuntimeRoute("static_compat", "static_capability", v2_ready, True)
