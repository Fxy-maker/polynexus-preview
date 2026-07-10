"""Validation for technique-neutral figure definitions."""

from __future__ import annotations

import re

from .contracts import FigureDefinition

_FIGURE_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
_SCOPES = {"frame", "series"}
_CATEGORIES = {
    "series_overview",
    "per_frame",
    "diagnostic",
    "supplementary",
}


class FigureDefinitionValidationError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = tuple(errors)
        super().__init__("; ".join(errors))


def validate_figure_definition(definition: FigureDefinition) -> None:
    errors: list[str] = []

    if not _FIGURE_ID_PATTERN.fullmatch(definition.figure_id):
        errors.append(f"invalid figure_id: {definition.figure_id}")
    if definition.scope not in _SCOPES:
        errors.append(f"invalid scope: {definition.scope}")
    if definition.category not in _CATEGORIES:
        errors.append(f"invalid category: {definition.category}")

    panel_ids: set[str] = set()
    panel_positions: set[tuple[int, int]] = set()
    if definition.layout.rows <= 0 or definition.layout.columns <= 0:
        errors.append("layout grid must have positive rows and columns")
    for panel in definition.layout.panels:
        if not panel.panel_id or panel.panel_id in panel_ids:
            errors.append(f"invalid or duplicate panel id: {panel.panel_id}")
        panel_ids.add(panel.panel_id)
        position = (panel.row, panel.column)
        if position in panel_positions:
            errors.append(f"duplicate panel grid position: {position}")
        panel_positions.add(position)
        if panel.row < 0 or panel.row >= definition.layout.rows:
            errors.append(f"panel row out of range: {panel.panel_id}")
        if panel.column < 0 or panel.column >= definition.layout.columns:
            errors.append(f"panel column out of range: {panel.panel_id}")

    source_map = {}
    for source in definition.data_sources:
        if not source.source_id or source.source_id in source_map:
            errors.append(f"invalid or duplicate data source id: {source.source_id}")
        source_map[source.source_id] = source
        column_names = [column.name for column in source.columns]
        if not column_names:
            errors.append(f"data source has no columns: {source.source_id}")
        if len(column_names) != len(set(column_names)):
            errors.append(f"duplicate columns in data source: {source.source_id}")
        if set(source.values) != set(column_names):
            errors.append(f"data columns do not match schema: {source.source_id}")
        lengths = {len(source.values.get(name, ())) for name in column_names}
        if len(lengths) > 1:
            errors.append(f"data column lengths differ: {source.source_id}")

    object_ids: set[str] = set()
    for figure_object in definition.objects:
        object_id = str(figure_object.get("id") or "")
        if not object_id or object_id in object_ids:
            errors.append(f"invalid or duplicate object id: {object_id}")
        object_ids.add(object_id)
        panel_id = str(figure_object.get("panel_id") or "")
        if panel_id not in panel_ids:
            errors.append(f"unknown panel_id: {panel_id}")
        if figure_object.get("type") != "plot_series":
            continue
        data_ref = str(figure_object.get("data_ref") or "")
        source = source_map.get(data_ref)
        if source is None:
            errors.append(f"unknown data_ref: {data_ref}")
            continue
        column_names = {column.name for column in source.columns}
        for key in ("x_column", "y_column"):
            column = str(figure_object.get(key) or "")
            if column not in column_names:
                errors.append(f"unknown {key}: {column}")

    if errors:
        raise FigureDefinitionValidationError(errors)
