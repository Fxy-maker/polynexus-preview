"""Resolve portable FigureDocuments into deterministic render plans."""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RenderAxis:
    label: str
    unit: str
    scale: str
    reversed: bool


@dataclass(frozen=True)
class RenderPanel:
    panel_id: str
    row: int
    column: int
    x_axis: RenderAxis
    y_axis: RenderAxis
    title: str = ""
    show_legend: bool = False


@dataclass(frozen=True)
class FigureRenderPlan:
    run_id: str
    figure_id: str
    revision: int
    width_in: float
    height_in: float
    rows: int
    columns: int
    horizontal_spacing: float
    vertical_spacing: float
    panels: tuple[RenderPanel, ...]
    objects: tuple[dict[str, object], ...]
    data_tables: dict[str, dict[str, list[object]]]
    background: str


class FigureRenderPlanBuilder:
    def __init__(self, run_root: Path):
        self.run_root = Path(run_root).resolve()

    def build(
        self,
        document_path: Path,
        document: dict[str, Any],
    ) -> FigureRenderPlan:
        document_path = Path(document_path).resolve()
        self._require_within_run(document_path)
        layout = document["layout"]
        canvas = layout["canvas"]
        grid = layout["grid"]
        panels = tuple(self._panel_from_payload(item) for item in layout["panels"])
        positions = {(panel.row, panel.column) for panel in panels}
        if len(positions) != len(panels):
            raise ValueError("render plan contains duplicate panel positions")
        data_tables = {
            str(source["id"]): self._load_data_source(source)
            for source in document.get("data_sources", [])
        }
        return FigureRenderPlan(
            run_id=str(document.get("run_id") or ""),
            figure_id=str(document.get("figure_id") or ""),
            revision=int(document.get("revision", 0) or 0),
            width_in=float(canvas["width"]),
            height_in=float(canvas["height"]),
            rows=int(grid["rows"]),
            columns=int(grid["columns"]),
            horizontal_spacing=float(grid.get("horizontal_spacing", 0.25)),
            vertical_spacing=float(grid.get("vertical_spacing", 0.25)),
            panels=panels,
            objects=tuple(
                dict(item)
                for item in document.get("objects", [])
                if isinstance(item, dict)
            ),
            data_tables=data_tables,
            background=str(canvas.get("background") or "white"),
        )

    def _panel_from_payload(self, payload: dict[str, Any]) -> RenderPanel:
        position = payload["grid_position"]
        return RenderPanel(
            panel_id=str(payload["panel_id"]),
            row=int(position["row"]),
            column=int(position["column"]),
            x_axis=self._axis_from_payload(payload["x_axis"]),
            y_axis=self._axis_from_payload(payload["y_axis"]),
            title=str(payload.get("title") or ""),
            show_legend=bool(payload.get("show_legend", False)),
        )

    @staticmethod
    def _axis_from_payload(payload: dict[str, Any]) -> RenderAxis:
        return RenderAxis(
            label=str(payload.get("label") or ""),
            unit=str(payload.get("unit") or ""),
            scale=str(payload.get("scale") or "linear"),
            reversed=bool(payload.get("reversed", False)),
        )

    def _load_data_source(
        self,
        source: dict[str, Any],
    ) -> dict[str, list[object]]:
        if str(source.get("kind") or "") != "csv":
            raise ValueError(f"unsupported data source kind: {source.get('kind')}")
        path = self._resolve_data_path(source)
        expected_sha256 = str(source.get("sha256") or "")
        if expected_sha256:
            actual_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual_sha256 != expected_sha256:
                raise ValueError(f"data source checksum mismatch: {source.get('id')}")
        schema = {
            str(column["name"]): str(column.get("dtype") or "float64")
            for column in source.get("columns", [])
        }
        table = {name: [] for name in schema}
        with path.open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                for name, dtype in schema.items():
                    table[name].append(self._coerce(row[name], dtype))
        return table

    def _resolve_data_path(self, source: dict[str, Any]) -> Path:
        path_kind = str(source.get("path_kind") or "")
        path_text = str(source.get("path") or "")
        if path_kind != "run_relative":
            raise ValueError(f"unsupported data path kind: {path_kind}")
        path = (self.run_root / Path(path_text)).resolve()
        self._require_within_run(path)
        if not path.is_file():
            raise FileNotFoundError(path)
        return path

    def _require_within_run(self, path: Path) -> None:
        try:
            path.relative_to(self.run_root)
        except ValueError as exc:
            raise ValueError(f"path escapes run root: {path}") from exc

    @staticmethod
    def _coerce(value: str, dtype: str) -> object:
        lookup = dtype.lower()
        if lookup.startswith("float"):
            return float(value)
        if lookup.startswith("int"):
            return int(value)
        return value
