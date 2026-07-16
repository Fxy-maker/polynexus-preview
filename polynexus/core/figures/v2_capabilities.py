"""Technique-neutral V2 capability hooks for manifest-backed figure definitions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from .contracts import FigureDefinition


@dataclass(frozen=True)
class V2DefinitionArtifact:
    capability: dict[str, Any]
    sidecar: dict[str, Any] | None = None


def build_v2_definition_artifact(definition: FigureDefinition) -> V2DefinitionArtifact:
    """Resolve an approved V2 adapter without replacing legacy assets."""

    adapter_key = str(definition.recipe.get("v2_adapter") or "")
    if adapter_key == "static_compat":
        return V2DefinitionArtifact(
            capability={
                "v2_runtime": "static_fallback",
                "v2_default": False,
                "v2_reviewed": False,
                "v2_reason_code": "static_compatibility",
                "user_label": f"Static {definition.technique.upper()} (not data-linked)",
            }
        )
    if adapter_key not in {
        "temperature_saxs",
        "dsc",
        "waxs",
        "nmr",
        "ir",
        "saxs_strain",
        "saxs_static",
    }:
        return V2DefinitionArtifact(
            capability={
                "v2_runtime": "not_configured",
                "v2_default": False,
                "v2_reviewed": False,
                "v2_reason_code": "no_v2_adapter",
            }
        )
    from polynexus.core.figures.v2_adapter import adapt_figure_definition

    result = adapt_figure_definition(definition)
    if not result.ok or result.worksheet is None or result.document is None:
        reason = result.diagnostics[0] if result.diagnostics else None
        return V2DefinitionArtifact(
            capability={
                "v2_runtime": "static_fallback",
                "v2_default": False,
                "v2_reviewed": False,
                "v2_reason_code": reason.reason_code if reason else "adapter_failed",
                "v2_diagnostics": [
                    {
                        "reason_code": item.reason_code,
                        "message": item.message,
                        "object_id": item.object_id,
                    }
                    for item in result.diagnostics
                ],
            }
        )
    from polynexus.plot_runtime.layout import LayoutResolver

    layout = LayoutResolver().resolve(result.document, result.worksheet.current)
    if not layout.ok:
        return V2DefinitionArtifact(
            capability={
                "v2_runtime": "static_fallback",
                "v2_default": False,
                "v2_reviewed": False,
                "v2_reason_code": "scene_resolution_failed",
                "v2_diagnostics": [
                    {
                        "reason_code": item.reason_code,
                        "message": item.message,
                        "object_id": item.object_id,
                    }
                    for item in layout.diagnostics
                ],
            }
        )
    return V2DefinitionArtifact(
        capability={
            "v2_runtime": "ready",
            **_approved_route_capability(adapter_key),
            "v2_reason_code": "",
        },
        sidecar={
            "schema_version": 1,
            "runtime": "reactive_figure_v2",
            "figure_id": definition.figure_id,
            "source_revision_id": result.worksheet.current.revision_id,
            "graph_revision_id": result.document.revision_id,
            "worksheet": result.worksheet.to_payload(),
            "graph_document": result.document.to_payload(),
        },
    )


def _approved_route_capability(adapter_key: str) -> dict[str, Any]:
    """Return the explicit user-approved default policy for ready adapters.

    Unsupported objects never reach this helper: adapter/document/layout
    failures return static fallback before the ready capability is emitted.
    Working-revision saves still clear this approval through
    ``ReactiveFigureProjectService`` until the edited revision is reviewed.
    """

    scope = [
        "architecture",
        "science",
        "publication",
        "compatibility",
        str(adapter_key),
    ]
    return {
        "v2_default": True,
        "v2_reviewed": True,
        "v2_review_record": {
            "reviewer": "workspace-owner",
            "decision": "approved",
            "scope": scope,
            "notes": "User-approved all V2-ready routes; unsupported objects retain static compatibility.",
            "recorded_at": date.today().isoformat(),
            "approval_source": "user-confirmed-in-thread",
        },
    }
