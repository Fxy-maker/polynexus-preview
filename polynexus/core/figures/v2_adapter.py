"""Technique-neutral adapter from figure definitions to Reactive Figure V2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from polynexus.core.figures.contracts import FigureDefinition, FigureDataSourceDefinition
from polynexus.plot_runtime.bindings import ColumnReference, DataBinding, RowFilter
from polynexus.plot_runtime.models import (
    AxisModel,
    GraphDocument,
    GraphObject,
    PanelModel,
    SourceDataset,
    Worksheet,
)


@dataclass(frozen=True)
class TemperatureV2AdapterDiagnostic:
    reason_code: str
    message: str
    object_id: str = ""


@dataclass(frozen=True)
class TemperatureV2AdapterResult:
    ok: bool
    worksheet: Worksheet | None
    document: GraphDocument | None
    diagnostics: tuple[TemperatureV2AdapterDiagnostic, ...] = ()
    static_fallback: bool = False


_SUPPORTED_OBJECT_TYPES = frozenset({"plot_series", "heatmap", "line", "text"})


def adapt_figure_definition(
    definition: FigureDefinition,
    *,
    dpi: int = 100,
) -> TemperatureV2AdapterResult:
    """Build a renderer-neutral V2 document from one temperature figure recipe."""

    diagnostics = _validate_definition(definition)
    if diagnostics:
        return TemperatureV2AdapterResult(False, None, None, diagnostics, True)
    try:
        worksheet = _build_worksheet(definition)
        document = _build_document(definition, worksheet, dpi=dpi)
    except (KeyError, TypeError, ValueError) as exc:
        diagnostic = TemperatureV2AdapterDiagnostic("invalid_figure_definition", str(exc))
        return TemperatureV2AdapterResult(False, None, None, (diagnostic,), True)
    return TemperatureV2AdapterResult(True, worksheet, document)


def adapt_temperature_figure_definition(
    definition: FigureDefinition,
    *,
    dpi: int = 100,
) -> TemperatureV2AdapterResult:
    """Backward-compatible named entry point for the temperature SAXS route."""

    return adapt_figure_definition(definition, dpi=dpi)


def _validate_definition(
    definition: FigureDefinition,
) -> tuple[TemperatureV2AdapterDiagnostic, ...]:
    diagnostics: list[TemperatureV2AdapterDiagnostic] = []
    source_ids = {source.source_id for source in definition.data_sources}
    for item in definition.objects:
        object_id = str(item.get("id") or "")
        object_type = str(item.get("type") or "")
        if object_type not in _SUPPORTED_OBJECT_TYPES:
            diagnostics.append(
                TemperatureV2AdapterDiagnostic(
                    "unsupported_object_type",
                    f"temperature V2 adapter does not support {object_type}",
                    object_id,
                )
            )
        source_id = str(item.get("data_ref") or "")
        if source_id and source_id not in source_ids:
            diagnostics.append(
                TemperatureV2AdapterDiagnostic(
                    "missing_data_source",
                    f"unknown data source: {source_id}",
                    object_id,
                )
            )
    return tuple(diagnostics)


def _build_worksheet(definition: FigureDefinition) -> Worksheet:
    sources = tuple(definition.data_sources)
    if not sources:
        raise ValueError("temperature figure has no data sources")
    total_rows = 0
    source_lengths: dict[str, int] = {}
    for source in sources:
        lengths = {len(tuple(values)) for values in source.values.values()}
        if len(lengths) != 1:
            raise ValueError(f"source {source.source_id} columns have unequal lengths")
        length = next(iter(lengths), 0)
        if length == 0:
            raise ValueError(f"source {source.source_id} is empty")
        source_lengths[source.source_id] = length
        total_rows += length

    marker_id = "__v2_source_id"
    columns: dict[str, list[Any]] = {marker_id: [None] * total_rows}
    units: dict[str, str] = {marker_id: ""}
    offset = 0
    marker_values = columns[marker_id]
    for source in sources:
        length = source_lengths[source.source_id]
        marker_values[offset : offset + length] = [source.source_id] * length
        for column in source.columns:
            column_id = _column_id(source, column.name)
            values = tuple(source.values.get(column.name, ()))
            if len(values) != length:
                raise ValueError(f"missing or misaligned values for {source.source_id}:{column.name}")
            columns.setdefault(column_id, [None] * total_rows)
            columns[column_id][offset : offset + length] = list(values)
            units[column_id] = column.unit
        offset += length
    source_id = f"{definition.figure_id}:source"
    revision_id = f"{definition.figure_id}:source-r1"
    source_dataset = SourceDataset.from_columns(
        dataset_id=source_id,
        revision_id=revision_id,
        columns=columns,
        units=units,
        names={column_id: column_id for column_id in columns},
        provenance={"figure_id": definition.figure_id, "technique": definition.technique},
    )
    return Worksheet.from_source(source_dataset)


def _build_document(
    definition: FigureDefinition,
    worksheet: Worksheet,
    *,
    dpi: int,
) -> GraphDocument:
    source_map = {source.source_id: source for source in definition.data_sources}
    bindings: list[DataBinding] = []
    objects: list[GraphObject] = []
    for item in definition.objects:
        object_id = str(item.get("id") or "")
        object_type = str(item.get("type") or "")
        panel_id = str(item.get("panel_id") or "")
        source_id = str(item.get("data_ref") or "")
        binding_id = ""
        if source_id:
            source = source_map[source_id]
            references: list[ColumnReference] = []
            for role, key in (("x", "x_column"), ("y", "y_column"), ("z", "z_column"), ("error", "error_column")):
                column_name = str(item.get(key) or "")
                if not column_name:
                    continue
                column = next((candidate for candidate in source.columns if candidate.name == column_name), None)
                if column is None:
                    raise ValueError(f"unknown column {column_name} in source {source_id}")
                references.append(ColumnReference(role, _column_id(source, column.name), column.unit))
            if not references:
                raise ValueError(f"object {object_id} has no data columns")
            binding_id = f"{object_id}::binding"
            bindings.append(
                DataBinding(
                    binding_id=binding_id,
                    object_id=object_id,
                    kind="heatmap" if object_type == "heatmap" else "line",
                    columns=tuple(references),
                    filters=(RowFilter("__v2_source_id", "==", source_id),),
                )
            )
        properties = {
            str(key): value
            for key, value in item.items()
            if key not in {"id", "type", "panel_id", "data_ref", "x_column", "y_column", "z_column", "error_column", "style"}
        }
        objects.append(
            GraphObject(
                object_id=object_id,
                object_type=object_type,
                panel_id=panel_id,
                binding_id=binding_id,
                style=dict(item.get("style") or {}),
                properties=properties,
                z_index=len(objects),
            )
        )
    for panel in definition.layout.panels:
        if panel.show_legend:
            labels = [str(item.get("name") or item.get("id") or "") for item in definition.objects if item.get("panel_id") == panel.panel_id]
            objects.append(
                GraphObject(
                    object_id=f"{panel.panel_id}::legend",
                    object_type="legend",
                    panel_id=panel.panel_id,
                    properties={"text": ", ".join(label for label in labels if label)},
                    z_index=len(objects),
                )
            )
    panels = tuple(
        PanelModel(
            panel_id=panel.panel_id,
            row=panel.row,
            column=panel.column,
            x_axis=AxisModel(panel.x_axis.label, panel.x_axis.unit, panel.x_axis.scale, panel.x_axis.reversed),
            y_axis=AxisModel(panel.y_axis.label, panel.y_axis.unit, panel.y_axis.scale, panel.y_axis.reversed),
            title=definition.title if index == 0 else "",
        )
        for index, panel in enumerate(definition.layout.panels)
    )
    return GraphDocument(
        graph_id=definition.figure_id,
        revision_id=f"{definition.figure_id}:graph-r1",
        canvas_width_px=max(1, round(definition.layout.width_in * dpi)),
        canvas_height_px=max(1, round(definition.layout.height_in * dpi)),
        panels=panels,
        objects=tuple(objects),
        bindings=tuple(bindings),
        metadata=(
            ("technique", definition.technique),
            ("source_revision_id", worksheet.current.revision_id),
            (
                "source_roles",
                tuple((source.source_id, source.role) for source in definition.data_sources),
            ),
            ("recipe", dict(definition.recipe)),
        ),
    )


def _column_id(source: FigureDataSourceDefinition, column_name: str) -> str:
    return f"{source.source_id}::{column_name}"
