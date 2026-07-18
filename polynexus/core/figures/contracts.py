"""Immutable, technique-neutral figure-definition contracts."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Mapping, Sequence


PUBLICATION_ROLES = frozenset({"main", "si", "diagnostic"})


@dataclass(frozen=True)
class FigureEligibilityDecision:
    """Publication role decision based on already-emitted evidence."""

    highest_role: str
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.highest_role not in PUBLICATION_ROLES:
            raise ValueError(f"unsupported publication role: {self.highest_role}")
        object.__setattr__(self, "reasons", tuple(self.reasons))


@dataclass(frozen=True)
class DataColumnDefinition:
    name: str
    unit: str
    dtype: str = "float64"

    def to_payload(self) -> dict[str, str]:
        return {"name": self.name, "unit": self.unit, "dtype": self.dtype}


@dataclass(frozen=True)
class FigureDataSourceDefinition:
    source_id: str
    columns: tuple[DataColumnDefinition, ...]
    values: Mapping[str, Sequence[Any]] = field(repr=False, compare=False)
    role: str = "plot_data"

    def to_payload(self) -> dict[str, Any]:
        return {
            "id": self.source_id,
            "kind": "memory",
            "role": self.role,
            "columns": [column.to_payload() for column in self.columns],
        }


@dataclass(frozen=True)
class AxisDefinition:
    axis_id: str
    label: str
    unit: str = ""
    scale: str = "linear"
    reversed: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {
            "axis_id": self.axis_id,
            "label": self.label,
            "unit": self.unit,
            "scale": self.scale,
            "reversed": self.reversed,
        }


@dataclass(frozen=True)
class PanelDefinition:
    panel_id: str
    row: int
    column: int
    x_axis: AxisDefinition
    y_axis: AxisDefinition
    title: str = ""
    show_legend: bool = False
    row_span: int = 1
    column_span: int = 1
    panel_label: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "panel_id": self.panel_id,
            "grid_position": {"row": self.row, "column": self.column},
            "grid_span": {"rows": self.row_span, "columns": self.column_span},
            "x_axis": self.x_axis.to_payload(),
            "y_axis": self.y_axis.to_payload(),
            "title": self.title,
            "show_legend": self.show_legend,
            "panel_label": self.panel_label,
        }


@dataclass(frozen=True)
class FigureLayoutDefinition:
    width_in: float
    height_in: float
    rows: int
    columns: int
    panels: tuple[PanelDefinition, ...]
    horizontal_spacing: float = 0.25
    vertical_spacing: float = 0.25

    def to_payload(self) -> dict[str, Any]:
        return {
            "canvas": {
                "width": self.width_in,
                "height": self.height_in,
                "unit": "inch",
            },
            "grid": {
                "rows": self.rows,
                "columns": self.columns,
                "horizontal_spacing": self.horizontal_spacing,
                "vertical_spacing": self.vertical_spacing,
            },
            "panels": [panel.to_payload() for panel in self.panels],
        }


@dataclass(frozen=True)
class FigureDefinition:
    figure_id: str
    technique: str
    scope: str
    category: str
    title: str
    layout: FigureLayoutDefinition
    data_sources: tuple[FigureDataSourceDefinition, ...]
    objects: tuple[dict[str, Any], ...]
    recipe: Mapping[str, Any]
    style_profile: str
    publication_role: str = "si"
    display_order: int = 0

    def with_objects(
        self,
        objects: Sequence[Mapping[str, Any]],
    ) -> FigureDefinition:
        return replace(
            self,
            objects=tuple(dict(item) for item in objects),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "figure_id": self.figure_id,
            "technique": self.technique,
            "scope": self.scope,
            "category": self.category,
            "publication_role": self.publication_role,
            "display_order": self.display_order,
            "title": self.title,
            "layout": self.layout.to_payload(),
            "data_sources": [source.to_payload() for source in self.data_sources],
            "objects": [dict(item) for item in self.objects],
            "recipe": dict(self.recipe),
            "style_profile": self.style_profile,
        }
