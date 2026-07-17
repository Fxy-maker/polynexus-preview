"""Resolve worksheet bindings and graph documents into scene geometry."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, log10
from typing import Any, Iterable

from .bindings import BindingResolution
from .models import AxisModel, DataRevision, GraphDocument, GraphObject
from .scene import (
    HeatmapCell,
    PanelScene,
    Point,
    Rect,
    RenderScene,
    SceneDiagnostic,
    SceneNode,
    Segment,
    TickMark,
)


@dataclass(frozen=True)
class LayoutResult:
    scene: RenderScene | None
    diagnostics: tuple[SceneDiagnostic, ...] = ()

    @property
    def ok(self) -> bool:
        return self.scene is not None and not self.diagnostics


@dataclass(frozen=True)
class _AxisResolution:
    limits: tuple[float, float]
    categories: tuple[str, ...] = ()


class LayoutResolver:
    """Pure resolver; it has no renderer or Qt dependency."""

    def __init__(self, *, dpi: int = 100):
        self.dpi = int(dpi)

    def resolve(self, document: GraphDocument, revision: DataRevision) -> LayoutResult:
        bindings = {binding.binding_id: binding for binding in document.bindings}
        panel_layout = self._panel_layout(document)
        diagnostics: list[SceneDiagnostic] = []
        resolved: dict[str, BindingResolution] = {}
        for graph_object in document.objects:
            if not graph_object.binding_id or graph_object.binding_id not in bindings:
                continue
            binding_result = bindings[graph_object.binding_id].resolve(revision)
            if not binding_result.ok:
                diagnostics.extend(
                    SceneDiagnostic(
                        item.reason_code,
                        item.message,
                        object_id=graph_object.object_id,
                        revision_id=revision.revision_id,
                    )
                    for item in binding_result.diagnostics
                )
            resolved[graph_object.object_id] = binding_result
        if diagnostics:
            return LayoutResult(None, tuple(diagnostics))

        panels: list[PanelScene] = []
        for panel in document.panels:
            axis_rect = panel_layout[panel.panel_id]
            data_values = self._panel_data_values(panel.panel_id, document.objects, resolved)
            category_roles = self._category_roles(panel.panel_id, document.objects)
            x_object_id = self._axis_diagnostic_object_id(
                panel.panel_id, "x", document.objects, resolved
            )
            y_object_id = self._axis_diagnostic_object_id(
                panel.panel_id, "y", document.objects, resolved
            )
            x_resolution = self._axis_limits(
                panel.x_axis,
                data_values.get("x", ()),
                allow_categories=category_roles["x"],
                object_id=x_object_id,
            )
            y_resolution = self._axis_limits(
                panel.y_axis,
                data_values.get("y", ()),
                allow_categories=category_roles["y"],
                object_id=y_object_id,
            )
            if isinstance(x_resolution, SceneDiagnostic):
                return LayoutResult(None, (x_resolution,))
            if isinstance(y_resolution, SceneDiagnostic):
                return LayoutResult(None, (y_resolution,))
            panels.append(
                PanelScene(
                    panel_id=panel.panel_id,
                    axis_rect=axis_rect,
                    x_ticks=self._ticks(
                        x_resolution.limits,
                        axis_rect.left,
                        axis_rect.right,
                        panel.x_axis.reversed,
                        panel.x_axis.scale,
                        categories=x_resolution.categories,
                    ),
                    y_ticks=self._ticks(
                        y_resolution.limits,
                        axis_rect.bottom,
                        axis_rect.top,
                        panel.y_axis.reversed,
                        panel.y_axis.scale,
                        categories=y_resolution.categories,
                    ),
                    x_label=self._axis_label(panel.x_axis),
                    y_label=self._axis_label(panel.y_axis),
                    title=panel.title,
                    x_scale=panel.x_axis.scale,
                    y_scale=panel.y_axis.scale,
                    x_reversed=panel.x_axis.reversed,
                    y_reversed=panel.y_axis.reversed,
                    x_categories=x_resolution.categories,
                    y_categories=y_resolution.categories,
                )
            )

        panel_map = {panel.panel_id: panel for panel in panels}
        nodes: list[SceneNode] = []
        for graph_object in sorted(document.objects, key=lambda item: item.z_index):
            if not graph_object.visible:
                continue
            panel = panel_map[graph_object.panel_id]
            binding_result = resolved.get(graph_object.object_id)
            node_result = self._resolve_object(
                graph_object,
                panel,
                binding_result,
                document,
                resolved,
            )
            if isinstance(node_result, SceneDiagnostic):
                return LayoutResult(None, (node_result,))
            if node_result is not None:
                nodes.append(node_result)
        return LayoutResult(
            RenderScene(
                revision_id=revision.revision_id,
                width_px=document.canvas_width_px,
                height_px=document.canvas_height_px,
                dpi=self.dpi,
                background="#FFFFFF",
                panels=tuple(panels),
                nodes=tuple(nodes),
            )
        )

    def resolve_incremental(
        self,
        document: GraphDocument,
        revision: DataRevision,
        previous_scene: RenderScene,
        dirty_object_ids: tuple[str, ...] | set[str],
        *,
        data_changed: bool = False,
    ) -> LayoutResult:
        """Re-resolve dirty nodes when panel geometry remains valid.

        Automatic axis limits and panel-definition changes require a full
        resolve because they can move every node. Explicit limits allow a
        worksheet or object-style edit to preserve unaffected scene nodes.
        """

        dirty = {str(item) for item in dirty_object_ids}
        previous_panels = {panel.panel_id: panel for panel in previous_scene.panels}
        if not self._can_reuse_panels(document, previous_scene, data_changed):
            return self.resolve(document, revision)
        bindings = {binding.binding_id: binding for binding in document.bindings}
        resolved: dict[str, BindingResolution] = {}
        diagnostics: list[SceneDiagnostic] = []
        for graph_object in document.objects:
            if graph_object.object_id not in dirty or not graph_object.binding_id:
                continue
            binding = bindings.get(graph_object.binding_id)
            if binding is None:
                diagnostics.append(
                    SceneDiagnostic(
                        "missing_binding",
                        "graph object references an unknown binding",
                        graph_object.object_id,
                        revision.revision_id,
                    )
                )
                continue
            result = binding.resolve(revision)
            if not result.ok:
                diagnostics.extend(
                    SceneDiagnostic(
                        item.reason_code,
                        item.message,
                        graph_object.object_id,
                        revision.revision_id,
                    )
                    for item in result.diagnostics
                )
            resolved[graph_object.object_id] = result
        if diagnostics:
            return LayoutResult(None, tuple(diagnostics))

        previous_nodes = {node.node_id: node for node in previous_scene.nodes}
        nodes: list[SceneNode] = []
        for graph_object in sorted(document.objects, key=lambda item: item.z_index):
            if not graph_object.visible:
                continue
            panel = previous_panels.get(graph_object.panel_id)
            if panel is None:
                return self.resolve(document, revision)
            if graph_object.object_id not in dirty and graph_object.object_id in previous_nodes:
                nodes.append(previous_nodes[graph_object.object_id])
                continue
            node_result = self._resolve_object(
                graph_object,
                panel,
                resolved.get(graph_object.object_id),
                document,
                resolved,
            )
            if isinstance(node_result, SceneDiagnostic):
                return LayoutResult(None, (node_result,))
            if node_result is not None:
                nodes.append(node_result)
        return LayoutResult(
            RenderScene(
                revision_id=revision.revision_id,
                width_px=document.canvas_width_px,
                height_px=document.canvas_height_px,
                dpi=self.dpi,
                background=previous_scene.background,
                panels=previous_scene.panels,
                nodes=tuple(nodes),
            )
        )

    @staticmethod
    def _can_reuse_panels(
        document: GraphDocument,
        previous_scene: RenderScene,
        data_changed: bool,
    ) -> bool:
        if document.canvas_width_px != previous_scene.width_px or document.canvas_height_px != previous_scene.height_px:
            return False
        previous_by_id = {panel.panel_id: panel for panel in previous_scene.panels}
        for panel in document.panels:
            previous = previous_by_id.get(panel.panel_id)
            if previous is None:
                return False
            if panel.title != previous.title:
                return False
            if panel.x_axis.scale != previous.x_scale or panel.y_axis.scale != previous.y_scale:
                return False
            if panel.x_axis.reversed != previous.x_reversed or panel.y_axis.reversed != previous.y_reversed:
                return False
            if panel.x_axis.minimum is None and panel.x_axis.maximum is None:
                # Category labels are part of the resolved panel geometry.
                if previous.x_categories:
                    return False
            if panel.y_axis.minimum is None and panel.y_axis.maximum is None:
                if previous.y_categories:
                    return False
            if panel.x_axis.minimum is None or panel.x_axis.maximum is None or panel.y_axis.minimum is None or panel.y_axis.maximum is None:
                if data_changed:
                    return False
        return len(previous_by_id) == len(document.panels)

    def _resolve_object(
        self,
        graph_object: GraphObject,
        panel: PanelScene,
        binding_result: BindingResolution | None,
        document: GraphDocument,
        resolved: dict[str, BindingResolution],
    ) -> SceneNode | SceneDiagnostic | None:
        if graph_object.object_type == "plot_series":
            if binding_result is None:
                return SceneDiagnostic("missing_binding", "plot series has no data binding", graph_object.object_id)
            return self._line_node(graph_object, panel, binding_result)
        if graph_object.object_type == "heatmap":
            if binding_result is None:
                return SceneDiagnostic("missing_binding", "heatmap has no data binding", graph_object.object_id)
            return self._heatmap_node(graph_object, panel, binding_result)
        if graph_object.object_type == "image_grid":
            if binding_result is None:
                return SceneDiagnostic("missing_binding", "image grid has no data binding", graph_object.object_id)
            return self._image_grid_node(graph_object, panel, binding_result)
        if graph_object.object_type == "line":
            props = graph_object.property_map
            if {"x1", "y1", "x2", "y2"}.issubset(props):
                coordinates = tuple(
                    self._number(props[key], graph_object.object_id, key)
                    for key in ("x1", "y1", "x2", "y2")
                )
                diagnostic = next(
                    (item for item in coordinates if isinstance(item, SceneDiagnostic)),
                    None,
                )
                if diagnostic is not None:
                    return diagnostic
                start = self._map_point(panel, coordinates[0], coordinates[1])
                end = self._map_point(panel, coordinates[2], coordinates[3])
                return SceneNode(
                    graph_object.object_id,
                    "line",
                    panel.panel_id,
                    graph_object.z_index,
                    segments=(Segment(start, end),),
                    style=graph_object.style_map,
                )
            if "x" in props:
                x = self._number(props["x"], graph_object.object_id, "x")
                if isinstance(x, SceneDiagnostic):
                    return x
                point = self._map_point(panel, x, 0.0)
                return SceneNode(graph_object.object_id, "line", panel.panel_id, graph_object.z_index, segments=(Segment(Point(point.x, panel.axis_rect.top), Point(point.x, panel.axis_rect.bottom)),), style=graph_object.style_map)
            if "y" in props:
                y = self._number(props["y"], graph_object.object_id, "y")
                if isinstance(y, SceneDiagnostic):
                    return y
                point = self._map_point(panel, 0.0, y)
                return SceneNode(graph_object.object_id, "line", panel.panel_id, graph_object.z_index, segments=(Segment(Point(panel.axis_rect.left, point.y), Point(panel.axis_rect.right, point.y)),), style=graph_object.style_map)
            return SceneDiagnostic("invalid_line", "line object requires x or y", graph_object.object_id)
        if graph_object.object_type == "text":
            props = graph_object.property_map
            x = self._number(props.get("x", 0.0), graph_object.object_id, "x")
            y = self._number(props.get("y", 0.0), graph_object.object_id, "y")
            if isinstance(x, SceneDiagnostic):
                return x
            if isinstance(y, SceneDiagnostic):
                return y
            return SceneNode(
                graph_object.object_id,
                "text",
                panel.panel_id,
                graph_object.z_index,
                text_anchor=self._map_point(panel, x, y),
                text=str(props.get("text", "")),
                style=graph_object.style_map,
            )
        if graph_object.object_type == "legend":
            return SceneNode(
                graph_object.object_id,
                "legend",
                panel.panel_id,
                graph_object.z_index,
                bounds=Rect(panel.axis_rect.right - 150.0, panel.axis_rect.top + 10.0, 140.0, 24.0),
                text_anchor=Point(panel.axis_rect.right - 140.0, panel.axis_rect.top + 28.0),
                text=str(graph_object.property_map.get("text", "")),
                style=graph_object.style_map,
            )
        if graph_object.object_type in {"highlight", "image_grid"}:
            return SceneDiagnostic(
                "unsupported_object_type",
                f"scene resolver does not yet support {graph_object.object_type}",
                graph_object.object_id,
            )
        return SceneDiagnostic(
            "unsupported_object_type",
            f"unknown graph object type: {graph_object.object_type}",
            graph_object.object_id,
        )

    def _line_node(self, graph_object: GraphObject, panel: PanelScene, result: BindingResolution) -> SceneNode | SceneDiagnostic:
        if "x" not in result.columns or "y" not in result.columns:
            return SceneDiagnostic("missing_binding_role", "line binding requires x and y roles", graph_object.object_id)
        x_values = self._axis_numbers(
            result.columns["x"], panel.x_categories, graph_object.object_id, "x"
        )
        y_values = self._axis_numbers(
            result.columns["y"], panel.y_categories, graph_object.object_id, "y"
        )
        if isinstance(x_values, SceneDiagnostic):
            return x_values
        if isinstance(y_values, SceneDiagnostic):
            return y_values
        if len(x_values) != len(y_values) or len(x_values) < 2:
            return SceneDiagnostic("invalid_series", "line binding needs matching x/y values", graph_object.object_id)
        points = tuple(self._map_point(panel, x, y) for x, y in zip(x_values, y_values))
        segments: list[Segment] = []
        error_values = result.columns.get("error", result.columns.get("y_error", ()))
        if error_values:
            errors = self._numbers(error_values, graph_object.object_id, "error")
            if isinstance(errors, SceneDiagnostic):
                return errors
            if len(errors) != len(points):
                return SceneDiagnostic("invalid_error_series", "error values do not match line values", graph_object.object_id)
            for point, error in zip(points, errors):
                upper = self._map_point(panel, 0.0, self._unmap_y(panel, point.y) + error)
                lower = self._map_point(panel, 0.0, self._unmap_y(panel, point.y) - error)
                segments.append(Segment(Point(point.x, upper.y), Point(point.x, lower.y)))
        return SceneNode(
            graph_object.object_id,
            "plot_series",
            panel.panel_id,
            graph_object.z_index,
            points=points,
            segments=tuple(segments),
            style=graph_object.style_map,
            metadata={"source_revision_id": result.provenance.revision_id},
        )

    def _heatmap_node(self, graph_object: GraphObject, panel: PanelScene, result: BindingResolution) -> SceneNode | SceneDiagnostic:
        required = {"x", "y", "z"}
        if not required.issubset(result.columns):
            return SceneDiagnostic("missing_binding_role", "heatmap binding requires x, y, and z roles", graph_object.object_id)
        x_values = self._numbers(result.columns["x"], graph_object.object_id, "x")
        y_values = self._numbers(result.columns["y"], graph_object.object_id, "y")
        z_values = self._numbers(result.columns["z"], graph_object.object_id, "z")
        if isinstance(x_values, SceneDiagnostic):
            return x_values
        if isinstance(y_values, SceneDiagnostic):
            return y_values
        if isinstance(z_values, SceneDiagnostic):
            return z_values
        if not (len(x_values) == len(y_values) == len(z_values)):
            return SceneDiagnostic("invalid_heatmap", "heatmap columns do not have equal length", graph_object.object_id)
        unique_x = sorted(set(x_values))
        unique_y = sorted(set(y_values))
        x_edges = _edges(unique_x)
        y_edges = _edges(unique_y)
        cells: list[HeatmapCell] = []
        for x, y, value in zip(x_values, y_values, z_values):
            left = self._map_point(panel, x_edges[unique_x.index(x)], 0.0).x
            right = self._map_point(panel, x_edges[unique_x.index(x) + 1], 0.0).x
            top = self._map_point(panel, 0.0, y_edges[unique_y.index(y) + 1]).y
            bottom = self._map_point(panel, 0.0, y_edges[unique_y.index(y)]).y
            cells.append(HeatmapCell(Rect(min(left, right), min(top, bottom), abs(right - left), abs(bottom - top)), value))
        return SceneNode(
            graph_object.object_id,
            "heatmap",
            panel.panel_id,
            graph_object.z_index,
            rectangles=tuple(cells),
            style=graph_object.style_map,
            metadata={"source_revision_id": result.provenance.revision_id},
        )

    def _image_grid_node(self, graph_object: GraphObject, panel: PanelScene, result: BindingResolution) -> SceneNode | SceneDiagnostic:
        required = {"x", "y", "z", "grid_column", "grid_row"}
        if not required.issubset(result.columns):
            return SceneDiagnostic(
                "missing_binding_role",
                "image grid binding requires x, y, z, grid_column, and grid_row roles",
                graph_object.object_id,
            )
        values: dict[str, tuple[float, ...]] = {}
        for role in required:
            numeric = self._numbers(result.columns[role], graph_object.object_id, role)
            if isinstance(numeric, SceneDiagnostic):
                return numeric
            values[role] = numeric
        if len({len(item) for item in values.values()}) != 1 or not values["x"]:
            return SceneDiagnostic(
                "invalid_image_grid",
                "image grid columns must be non-empty and equally sized",
                graph_object.object_id,
            )

        columns = tuple(sorted(set(values["grid_column"])))
        rows = tuple(sorted(set(values["grid_row"])))
        if not columns or not rows:
            return SceneDiagnostic("invalid_image_grid", "image grid frame coordinates are empty", graph_object.object_id)
        column_index = {value: index for index, value in enumerate(columns)}
        row_index = {value: index for index, value in enumerate(rows)}
        frame_x: dict[tuple[float, float], set[float]] = {}
        frame_y: dict[tuple[float, float], set[float]] = {}
        frame_counts: dict[tuple[float, float], int] = {}
        for grid_column, grid_row, x, y in zip(
            values["grid_column"], values["grid_row"], values["x"], values["y"]
        ):
            key = (grid_column, grid_row)
            frame_x.setdefault(key, set()).add(x)
            frame_y.setdefault(key, set()).add(y)
            frame_counts[key] = frame_counts.get(key, 0) + 1
        # Keep a deterministic pixel lattice for every frame.  The WAXS
        # provider emits equal-shaped images; mixed shapes are rejected rather
        # than silently flattening one frame over another.
        shape = {(
            len(frame_x[key]),
            len(frame_y[key]),
        ) for key in frame_x}
        if len(shape) != 1:
            return SceneDiagnostic("invalid_image_grid", "image grid frames have different shapes", graph_object.object_id)
        expected_cells = next(iter(shape))[0] * next(iter(shape))[1]
        if any(count != expected_cells for count in frame_counts.values()):
            return SceneDiagnostic("invalid_image_grid", "image grid frame is not a complete regular lattice", graph_object.object_id)
        rectangles: list[HeatmapCell] = []
        tile_width = panel.axis_rect.width / len(columns)
        tile_height = panel.axis_rect.height / len(rows)
        for grid_column, grid_row, x, y, intensity in zip(
            values["grid_column"],
            values["grid_row"],
            values["x"],
            values["y"],
            values["z"],
        ):
            key = (grid_column, grid_row)
            xs = tuple(sorted(frame_x[key]))
            ys = tuple(sorted(frame_y[key]))
            x_edges = _edges(xs)
            y_edges = _edges(ys)
            x_pos = xs.index(x)
            y_pos = ys.index(y)
            x_min, x_max = x_edges[0], x_edges[-1]
            y_min, y_max = y_edges[0], y_edges[-1]
            x_span = max(x_max - x_min, 1e-12)
            y_span = max(y_max - y_min, 1e-12)
            tile_left = panel.axis_rect.left + column_index[grid_column] * tile_width
            tile_top = panel.axis_rect.top + row_index[grid_row] * tile_height
            left = tile_left + (x_edges[x_pos] - x_min) / x_span * tile_width
            right = tile_left + (x_edges[x_pos + 1] - x_min) / x_span * tile_width
            top = tile_top + (y_edges[y_pos] - y_min) / y_span * tile_height
            bottom = tile_top + (y_edges[y_pos + 1] - y_min) / y_span * tile_height
            rectangles.append(
                HeatmapCell(
                    Rect(min(left, right), min(top, bottom), abs(right - left), abs(bottom - top)),
                    intensity,
                    int(grid_column),
                    int(grid_row),
                )
            )
        return SceneNode(
            graph_object.object_id,
            "image_grid",
            panel.panel_id,
            graph_object.z_index,
            rectangles=tuple(rectangles),
            style=graph_object.style_map,
            metadata={
                "source_revision_id": result.provenance.revision_id,
                "grid_shape": (len(columns), len(rows)),
                "grid_columns": columns,
                "grid_rows": rows,
            },
        )

    @staticmethod
    def _panel_layout(document: GraphDocument) -> dict[str, Rect]:
        rows = max(panel.row for panel in document.panels) + 1
        columns = max(panel.column for panel in document.panels) + 1
        outer_left, outer_top, outer_right, outer_bottom = 70.0, 40.0, 30.0, 62.0
        gap_x, gap_y = 18.0, 18.0
        slot_width = (document.canvas_width_px - outer_left - outer_right - gap_x * (columns - 1)) / columns
        slot_height = (document.canvas_height_px - outer_top - outer_bottom - gap_y * (rows - 1)) / rows
        return {
            panel.panel_id: Rect(
                outer_left + panel.column * (slot_width + gap_x) + 42.0,
                outer_top + panel.row * (slot_height + gap_y),
                max(1.0, slot_width - 52.0),
                max(1.0, slot_height - 10.0),
            )
            for panel in document.panels
        }

    @staticmethod
    def _panel_data_values(panel_id: str, objects: Iterable[GraphObject], resolved: dict[str, BindingResolution]) -> dict[str, tuple[Any, ...]]:
        values: dict[str, list[Any]] = {"x": [], "y": []}
        for item in objects:
            if item.panel_id != panel_id or item.object_id not in resolved:
                continue
            result = resolved[item.object_id]
            for role in ("x", "y"):
                values[role].extend(result.columns.get(role, ()))
        return {key: tuple(value) for key, value in values.items()}

    @staticmethod
    def _axis_limits(
        axis: AxisModel,
        values: tuple[Any, ...],
        *,
        allow_categories: bool = False,
        object_id: str = "",
    ) -> _AxisResolution | SceneDiagnostic:
        numeric_flags = tuple(_is_finite_number(value) for value in values)
        if values and not all(numeric_flags):
            if (
                not allow_categories
                or any(numeric_flags)
                or axis.scale == "log"
                or axis.minimum is not None
                or axis.maximum is not None
            ):
                return SceneDiagnostic(
                    "non_numeric_value",
                    "axis values must be consistently numeric or categorical",
                    object_id,
                )
            categories = tuple(dict.fromkeys(str(value) for value in values))
            if not categories or any(not item for item in categories):
                return SceneDiagnostic("invalid_categories", "categorical axis labels must be non-empty")
            high = max(0.5, float(len(categories)) - 0.5)
            return _AxisResolution((-0.5, high), categories)
        auto_low = axis.minimum is None
        auto_high = axis.maximum is None
        low = axis.minimum if not auto_low else (min(values) if values else 0.0)
        high = axis.maximum if not auto_high else (max(values) if values else 1.0)
        if low == high and auto_low and auto_high and values:
            if axis.scale == "log" and low > 0:
                low /= 10.0 ** 0.25
                high *= 10.0 ** 0.25
            elif axis.scale != "log":
                padding = max(abs(float(low)) * 0.05, 1e-9)
                low -= padding
                high += padding
        if axis.scale == "log" and (low <= 0 or high <= 0):
            return SceneDiagnostic("invalid_log_axis", "log axis limits must be positive")
        if not isfinite(float(low)) or not isfinite(float(high)) or low >= high:
            return SceneDiagnostic("invalid_axis_limits", "axis limits must be finite and increasing")
        return _AxisResolution((float(low), float(high)))

    @staticmethod
    def _category_roles(panel_id: str, objects: Iterable[GraphObject]) -> dict[str, bool]:
        roles = {"x": False, "y": False}
        for item in objects:
            if item.panel_id != panel_id or item.property_map.get("chart_kind") != "bar":
                continue
            roles["x"] = True
            roles["y"] = True
        return roles

    @staticmethod
    def _axis_diagnostic_object_id(
        panel_id: str,
        role: str,
        objects: Iterable[GraphObject],
        resolved: dict[str, BindingResolution],
    ) -> str:
        for item in objects:
            if item.panel_id != panel_id or item.object_id not in resolved:
                continue
            values = resolved[item.object_id].columns.get(role, ())
            if any(not _is_finite_number(value) for value in values):
                return item.object_id
        return ""

    @staticmethod
    def _ticks(
        limits: tuple[float, float],
        start: float,
        end: float,
        reversed_axis: bool,
        scale: str,
        *,
        categories: tuple[str, ...] = (),
    ) -> tuple[TickMark, ...]:
        low, high = limits
        if categories:
            values = tuple(float(index) for index in range(len(categories)))
            labels = categories
        else:
            values = (
                (low, (low + high) / 2.0, high)
                if scale != "log"
                else (low, 10.0 ** ((log10(low) + log10(high)) / 2.0), high)
            )
            labels = tuple(_format_tick(value) for value in values)
        return tuple(
            TickMark(
                value,
                labels[index],
                start
                + (end - start)
                * (
                    LayoutResolver._axis_fraction(value, low, high, scale)
                    if not reversed_axis
                    else 1.0 - LayoutResolver._axis_fraction(value, low, high, scale)
                ),
            )
            for index, value in enumerate(values)
        )

    @staticmethod
    def _axis_label(axis: AxisModel) -> str:
        return f"{axis.label} ({axis.unit})" if axis.unit else axis.label

    @staticmethod
    def _map_point(panel: PanelScene, x: float, y: float) -> Point:
        x_tick = panel.x_ticks
        y_tick = panel.y_ticks
        x_low, x_high = x_tick[0].value, x_tick[-1].value
        y_low, y_high = y_tick[0].value, y_tick[-1].value
        x_fraction = LayoutResolver._axis_fraction(x, x_low, x_high, panel.x_scale)
        y_fraction = LayoutResolver._axis_fraction(y, y_low, y_high, panel.y_scale)
        x_position = x_tick[0].position + (x_tick[-1].position - x_tick[0].position) * x_fraction
        y_position = (
            panel.axis_rect.top + panel.axis_rect.height * y_fraction
            if panel.y_reversed
            else panel.axis_rect.bottom - panel.axis_rect.height * y_fraction
        )
        return Point(x_position, y_position)

    @staticmethod
    def _unmap_y(panel: PanelScene, y_position: float) -> float:
        low, high = panel.y_ticks[0].value, panel.y_ticks[-1].value
        fraction = (
            (y_position - panel.axis_rect.top) / panel.axis_rect.height
            if panel.y_reversed
            else (panel.axis_rect.bottom - y_position) / panel.axis_rect.height
        )
        return LayoutResolver._axis_value(fraction, low, high, panel.y_scale)

    @staticmethod
    def _axis_fraction(value: float, low: float, high: float, scale: str) -> float:
        if scale == "log":
            return (log10(value) - log10(low)) / (log10(high) - log10(low))
        return (value - low) / (high - low)

    @staticmethod
    def _axis_value(fraction: float, low: float, high: float, scale: str) -> float:
        if scale == "log":
            return 10.0 ** (log10(low) + fraction * (log10(high) - log10(low)))
        return low + fraction * (high - low)

    @staticmethod
    def _number(value: Any, object_id: str, role: str) -> float | SceneDiagnostic:
        if not _is_finite_number(value):
            return SceneDiagnostic("non_numeric_value", f"{role} value is not finite numeric", object_id)
        return float(value)

    def _numbers(self, values: Iterable[Any], object_id: str, role: str) -> tuple[float, ...] | SceneDiagnostic:
        converted: list[float] = []
        for value in values:
            number = self._number(value, object_id, role)
            if isinstance(number, SceneDiagnostic):
                return number
            converted.append(number)
        return tuple(converted)

    def _axis_numbers(
        self,
        values: Iterable[Any],
        categories: tuple[str, ...],
        object_id: str,
        role: str,
    ) -> tuple[float, ...] | SceneDiagnostic:
        if not categories:
            return self._numbers(values, object_id, role)
        category_index = {label: float(index) for index, label in enumerate(categories)}
        converted: list[float] = []
        for value in values:
            label = str(value)
            if label not in category_index:
                return SceneDiagnostic("unknown_category", f"{role} value is not a declared category", object_id)
            converted.append(category_index[label])
        return tuple(converted)


def _is_finite_number(value: Any) -> bool:
    try:
        return isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _format_tick(value: float) -> str:
    return f"{value:.4g}"


def _edges(values: list[float]) -> list[float]:
    if len(values) == 1:
        return [values[0] - 0.5, values[0] + 0.5]
    mids = [(left + right) / 2.0 for left, right in zip(values, values[1:])]
    return [values[0] - (mids[0] - values[0]), *mids, values[-1] + (values[-1] - mids[-1])]
