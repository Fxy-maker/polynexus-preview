"""Pure, loss-aware mapping from PolyNexus figure documents to Origin specs."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping

from ..core.figure_document import normalize_figure_document


@dataclass(frozen=True)
class OriginSourceSpec:
    source_id: str
    path: str = ""
    role: str = ""
    columns: tuple[Mapping[str, Any], ...] = ()
    values: Mapping[str, Any] = field(default_factory=dict, repr=False)


@dataclass(frozen=True)
class OriginPlotSpec:
    object_id: str
    name: str
    data_ref: str
    x_column: str
    y_column: str = ""
    lower_y_column: str = ""
    upper_y_column: str = ""
    style: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OriginAnnotationSpec:
    object_id: str
    object_type: str
    payload: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OriginFigureModel:
    figure_id: str
    title: str
    xlabel: str
    ylabel: str
    sources: tuple[OriginSourceSpec, ...] = ()
    plots: tuple[OriginPlotSpec, ...] = ()
    annotations: tuple[OriginAnnotationSpec, ...] = ()
    warnings: tuple[str, ...] = ()


def map_figure_document(document: Mapping[str, Any] | None) -> OriginFigureModel:
    normalized = normalize_figure_document(dict(document or {}))
    style = normalized.get("style", {})
    style = style if isinstance(style, dict) else {}

    sources = tuple(
        OriginSourceSpec(
            source_id=str(source.get("id") or ""),
            path=str(source.get("path") or ""),
            role=str(source.get("role") or ""),
            columns=tuple(
                deepcopy(column)
                for column in source.get("columns", [])
                if isinstance(column, dict)
            ),
            values=deepcopy(source.get("values", {}))
            if isinstance(source.get("values"), dict)
            else {},
        )
        for source in normalized.get("data_sources", [])
        if isinstance(source, dict)
    )

    plots: list[OriginPlotSpec] = []
    annotations: list[OriginAnnotationSpec] = []
    warnings: list[str] = []
    supported_annotations = {"line", "arrow", "rectangle", "text"}

    for raw_object in normalized.get("objects", []):
        if not isinstance(raw_object, dict):
            continue
        object_type = str(raw_object.get("type") or "").strip().lower()
        object_id = str(raw_object.get("id") or "").strip()
        if object_type == "plot_series":
            plots.append(
                OriginPlotSpec(
                    object_id=object_id,
                    name=str(raw_object.get("name") or object_id),
                    data_ref=str(raw_object.get("data_ref") or ""),
                    x_column=str(raw_object.get("x_column") or ""),
                    y_column=str(raw_object.get("y_column") or ""),
                    lower_y_column=str(raw_object.get("lower_y_column") or ""),
                    upper_y_column=str(raw_object.get("upper_y_column") or ""),
                    style=deepcopy(raw_object.get("style", {}))
                    if isinstance(raw_object.get("style"), dict)
                    else {},
                )
            )
        elif object_type in supported_annotations:
            annotations.append(
                OriginAnnotationSpec(
                    object_id=object_id,
                    object_type=object_type,
                    payload=deepcopy(raw_object),
                )
            )
        elif object_type:
            warnings.append(
                f"Object {object_id or '<unnamed>'} of type {object_type} "
                "is not editable through the Origin adapter"
            )

    return OriginFigureModel(
        figure_id=str(normalized.get("figure_id") or ""),
        title=str(style.get("title") or normalized.get("title") or ""),
        xlabel=str(style.get("xlabel") or ""),
        ylabel=str(style.get("ylabel") or ""),
        sources=sources,
        plots=tuple(plots),
        annotations=tuple(annotations),
        warnings=tuple(warnings),
    )
