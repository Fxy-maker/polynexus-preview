"""Compatibility adapters for legacy FigureDocument payloads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .bindings import ColumnReference, DataBinding
from .models import GraphDocument, GraphObject, PanelModel


@dataclass(frozen=True)
class CompatibilityDiagnostic:
    reason_code: str
    message: str
    static_fallback: bool


@dataclass(frozen=True)
class CompatibilityResult:
    document: GraphDocument | None
    diagnostic: CompatibilityDiagnostic | None = None


_SUPPORTED_OBJECT_TYPES = frozenset(
    {"plot_series", "heatmap", "image_grid", "line", "text", "legend"}
)


def adapt_legacy_figure_document(payload: Mapping[str, Any]) -> CompatibilityResult:
    if not isinstance(payload, Mapping) or payload.get("mode") != "object":
        return CompatibilityResult(
            None,
            CompatibilityDiagnostic(
                "static_document",
                "legacy payload is not an object-editable figure document",
                True,
            ),
        )
    objects_payload = payload.get("objects", ())
    if not isinstance(objects_payload, (list, tuple)):
        return _fallback("invalid_objects", "legacy objects must be a list")
    for item in objects_payload:
        object_type = str(item.get("type") or "") if isinstance(item, Mapping) else ""
        if object_type not in _SUPPORTED_OBJECT_TYPES:
            return _fallback(
                "unsupported_object_type",
                f"legacy object type is not supported by V2: {object_type or '<empty>'}",
            )

    layout = dict(payload.get("layout") or {})
    canvas = dict(layout.get("canvas") or {})
    width_px = int(float(canvas.get("width", 6.4) or 6.4) * 100.0)
    height_px = int(float(canvas.get("height", 4.8) or 4.8) * 100.0)
    panel_payloads = layout.get("panels") or [
        {
            "panel_id": "main",
            "grid_position": {"row": 0, "column": 0},
            "x_axis": {},
            "y_axis": {},
        }
    ]
    panels = tuple(PanelModel.from_payload(item) for item in panel_payloads)
    objects: list[GraphObject] = []
    bindings: list[DataBinding] = []
    for raw in objects_payload:
        raw = dict(raw)
        object_item = GraphObject.from_payload(raw)
        object_item = GraphObject(
            object_id=object_item.object_id,
            object_type=object_item.object_type,
            panel_id=object_item.panel_id,
            binding_id=object_item.binding_id,
            style=object_item.style_map,
            properties={
                key: value
                for key, value in raw.items()
                if key
                not in {
                    "id",
                    "type",
                    "panel_id",
                    "binding_id",
                    "data_ref",
                    "style",
                    "visible",
                    "z_index",
                }
            },
            visible=object_item.visible,
            z_index=object_item.z_index,
        )
        objects.append(object_item)
        if object_item.binding_id and object_item.object_type in {"plot_series", "heatmap", "image_grid", "highlight"}:
            references = []
            role_keys = [("x", "x_column"), ("y", "y_column"), ("z", "z_column"), ("value", "value_column")]
            if object_item.object_type == "image_grid":
                role_keys.extend((("grid_column", "grid_column"), ("grid_row", "grid_row")))
            for role, key in role_keys:
                column_id = str(raw.get(key) or "")
                if column_id:
                    references.append(ColumnReference(role=role, column_id=column_id))
            if references:
                bindings.append(
                    DataBinding(
                        binding_id=object_item.binding_id,
                        object_id=object_item.object_id,
                        kind=str(raw.get("chart_kind") or object_item.object_type),
                        columns=tuple(references),
                    )
                )
    try:
        document = GraphDocument(
            graph_id=str(payload.get("figure_id") or "legacy-figure"),
            revision_id=str(payload.get("revision_id") or "legacy-r1"),
            canvas_width_px=width_px,
            canvas_height_px=height_px,
            panels=panels,
            objects=tuple(objects),
            bindings=tuple(bindings),
        )
    except (TypeError, ValueError, KeyError) as exc:
        return _fallback("invalid_object_document", str(exc))
    return CompatibilityResult(document)


def _fallback(reason_code: str, message: str) -> CompatibilityResult:
    return CompatibilityResult(
        None,
        CompatibilityDiagnostic(reason_code, message, True),
    )
