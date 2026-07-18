"""Core Matplotlib rendering for FigureRenderPlan."""

from __future__ import annotations

from typing import Any

import numpy as np
from matplotlib.figure import Figure

from .render_plan import FigureRenderPlan, RenderAxis


class MatplotlibFigureRenderer:
    """Render a portable plan and retain object-to-artist identity metadata.

    The identity map is intentionally renderer-owned rather than persisted in
    the document.  GUI editors can consume it to reconnect canvas picks to the
    renderer-neutral object ids after each redraw.
    """

    def __init__(self) -> None:
        self.last_artist_map: dict[str, list[Any]] = {}

    def render(self, plan: FigureRenderPlan, *, dpi: int) -> Figure:
        self.last_artist_map = {}
        figure = Figure(
            figsize=(plan.width_in, plan.height_in),
            dpi=dpi,
            facecolor=plan.background,
            layout="constrained",
        )
        grid = figure.add_gridspec(
            plan.rows,
            plan.columns,
            wspace=plan.horizontal_spacing,
            hspace=plan.vertical_spacing,
        )
        axes: dict[str, Any] = {}
        for panel in plan.panels:
            axis = figure.add_subplot(
                grid[
                    panel.row : panel.row + panel.row_span,
                    panel.column : panel.column + panel.column_span,
                ]
            )
            axis.set_gid(f"pn-panel:{panel.panel_id}")
            axis.set_xlabel(self._axis_label(panel.x_axis))
            axis.set_ylabel(self._axis_label(panel.y_axis))
            axis.set_title(panel.title)
            axis.set_xscale(panel.x_axis.scale)
            axis.set_yscale(panel.y_axis.scale)
            if panel.x_axis.reversed:
                axis.invert_xaxis()
            if panel.y_axis.reversed:
                axis.invert_yaxis()
            if panel.panel_label:
                axis.text(
                    0.0,
                    1.02,
                    panel.panel_label,
                    transform=axis.transAxes,
                    fontsize=9.0,
                    fontweight="bold",
                    ha="left",
                    va="bottom",
                    gid=f"pn-panel-label:{panel.panel_id}",
                )
            axes[panel.panel_id] = axis

        ordered_objects = sorted(
            plan.objects,
            key=lambda item: int(item.get("z_index", 0) or 0),
        )
        legend_objects = self._legend_objects(ordered_objects, axes)
        for figure_object in ordered_objects:
            object_type = str(figure_object.get("type") or "")
            if object_type == "legend":
                continue
            if figure_object.get("visible") is False:
                continue
            panel_id = str(figure_object.get("panel_id") or "")
            if panel_id not in axes:
                raise ValueError(f"unknown render panel: {panel_id}")
            axis = axes[panel_id]
            if object_type == "plot_series":
                artists = self._render_plot_series(axis, plan, figure_object)
            elif object_type == "heatmap":
                artists = self._render_heatmap(figure, axis, plan, figure_object)
            elif object_type == "image_grid":
                artists = self._render_image_grid(axis, plan, figure_object)
            elif object_type == "line":
                artists = self._render_line(axis, figure_object)
            elif object_type == "arrow":
                artists = self._render_arrow(axis, figure_object)
            elif object_type == "rectangle":
                artists = self._render_rectangle(axis, figure_object)
            elif object_type == "text":
                artists = self._render_text(axis, figure_object)
            else:
                raise ValueError(f"unsupported render object type: {object_type}")
            object_id = str(figure_object.get("id") or "")
            if object_id:
                for artist in artists or ():
                    if artist is None:
                        continue
                    if hasattr(artist, "set_gid"):
                        artist.set_gid(f"pn-object:{object_id}")
                    self.last_artist_map.setdefault(object_id, []).append(artist)

        for panel in plan.panels:
            legend_object = legend_objects.get(panel.panel_id)
            if not panel.show_legend or (
                legend_object is not None
                and legend_object.get("visible") is False
            ):
                continue
            axis = axes[panel.panel_id]
            handles, labels = axis.get_legend_handles_labels()
            if handles and labels:
                axis.legend(**self._legend_kwargs(legend_object))

        return figure

    @staticmethod
    def _legend_objects(
        objects: list[dict[str, Any]],
        axes: dict[str, Any],
    ) -> dict[str, dict[str, Any]]:
        legends: dict[str, dict[str, Any]] = {}
        for figure_object in objects:
            if str(figure_object.get("type") or "") != "legend":
                continue
            panel_id = str(figure_object.get("panel_id") or "")
            if not panel_id and len(axes) == 1:
                panel_id = next(iter(axes))
            if panel_id not in axes:
                raise ValueError(f"unknown render panel: {panel_id}")
            legends[panel_id] = figure_object
        return legends

    @staticmethod
    def _legend_kwargs(figure_object: dict[str, Any] | None) -> dict[str, Any]:
        if not isinstance(figure_object, dict):
            return {}
        style = figure_object.get("style", {})
        if not isinstance(style, dict):
            return {}
        kwargs: dict[str, Any] = {}
        loc = str(style.get("loc") or "").strip()
        if loc:
            kwargs["loc"] = loc
        anchor = style.get("bbox_to_anchor")
        if isinstance(anchor, (list, tuple)) and len(anchor) >= 2:
            kwargs["bbox_to_anchor"] = (float(anchor[0]), float(anchor[1]))
        return kwargs

    @staticmethod
    def _axis_label(axis: RenderAxis) -> str:
        if axis.unit:
            return f"{axis.label} ({axis.unit})"
        return axis.label

    @staticmethod
    def _style(figure_object: dict[str, Any]) -> dict[str, Any]:
        style = figure_object.get("style", {})
        return style if isinstance(style, dict) else {}

    def _render_plot_series(
        self,
        axis,
        plan: FigureRenderPlan,
        figure_object: dict[str, Any],
    ) -> list[Any]:
        data_ref = str(figure_object.get("data_ref") or "")
        try:
            table = plan.data_tables[data_ref]
        except KeyError as exc:
            raise ValueError(f"unknown render data source: {data_ref}") from exc
        x_column = str(figure_object.get("x_column") or "")
        y_column = str(figure_object.get("y_column") or "")
        style = self._style(figure_object)
        kwargs: dict[str, Any] = {
            "color": style.get("color", "#222222"),
            "linewidth": float(style.get("line_width", 1.0)),
            "linestyle": style.get("line_style", "-"),
            "alpha": float(style.get("alpha", 1.0)),
        }
        marker = str(style.get("marker") or "")
        if marker:
            kwargs["marker"] = marker
            kwargs["markersize"] = float(style.get("marker_size", 4.0))
        name = str(figure_object.get("name") or "")
        if name:
            kwargs["label"] = name
        chart_kind = str(figure_object.get("chart_kind") or "line")
        if chart_kind == "bar":
            container = axis.bar(
                table[x_column],
                table[y_column],
                color=style.get("color", "#4477AA"),
                alpha=float(style.get("alpha", 1.0)),
                label=name or None,
            )
            return list(container.patches)
        elif chart_kind == "scatter":
            return [axis.scatter(
                table[x_column],
                table[y_column],
                color=style.get("color", "#222222"),
                s=float(style.get("marker_size", 12.0)),
                alpha=float(style.get("alpha", 1.0)),
                label=name or None,
            )]
        elif chart_kind == "line":
            return list(axis.plot(table[x_column], table[y_column], **kwargs))
        else:
            raise ValueError(f"unsupported chart kind: {chart_kind}")

    def _render_heatmap(
        self,
        figure: Figure,
        axis,
        plan: FigureRenderPlan,
        figure_object: dict[str, Any],
    ) -> list[Any]:
        data_ref = str(figure_object.get("data_ref") or "")
        try:
            table = plan.data_tables[data_ref]
        except KeyError as exc:
            raise ValueError(f"unknown render data source: {data_ref}") from exc
        x_values = np.asarray(
            table[str(figure_object.get("x_column") or "")],
            dtype=float,
        )
        y_values = np.asarray(
            table[str(figure_object.get("y_column") or "")],
            dtype=float,
        )
        z_values = np.asarray(
            table[str(figure_object.get("z_column") or "")],
            dtype=float,
        )
        unique_x = np.unique(x_values)
        unique_y = np.unique(y_values)
        if len(unique_x) == 0 or len(unique_y) == 0:
            raise ValueError("heatmap data is empty")
        matrix = np.full((len(unique_y), len(unique_x)), np.nan, dtype=float)
        x_index = {value: index for index, value in enumerate(unique_x)}
        y_index = {value: index for index, value in enumerate(unique_y)}
        for x_value, y_value, z_value in zip(x_values, y_values, z_values):
            matrix[y_index[y_value], x_index[x_value]] = z_value
        if np.isnan(matrix).any():
            raise ValueError("heatmap data does not form a complete regular grid")
        style = self._style(figure_object)
        image = axis.pcolormesh(
            unique_x,
            unique_y,
            matrix,
            shading="auto",
            cmap=str(style.get("cmap") or "viridis"),
        )
        label = str(style.get("colorbar_label") or "")
        figure.colorbar(image, ax=axis, label=label)
        return [image]

    def _render_image_grid(
        self,
        axis,
        plan: FigureRenderPlan,
        figure_object: dict[str, Any],
    ) -> list[Any]:
        data_ref = str(figure_object.get("data_ref") or "")
        try:
            table = plan.data_tables[data_ref]
        except KeyError as exc:
            raise ValueError(f"unknown render data source: {data_ref}") from exc
        grid_column = np.asarray(table[str(figure_object.get("grid_column") or "")], dtype=int)
        grid_row = np.asarray(table[str(figure_object.get("grid_row") or "")], dtype=int)
        x_values = np.asarray(table[str(figure_object.get("x_column") or "")], dtype=float)
        y_values = np.asarray(table[str(figure_object.get("y_column") or "")], dtype=float)
        z_values = np.asarray(table[str(figure_object.get("z_column") or "")], dtype=float)
        if not (len(grid_column) == len(grid_row) == len(x_values) == len(y_values) == len(z_values)):
            raise ValueError("image_grid data columns differ in length")
        cells = sorted(set(zip(grid_column.tolist(), grid_row.tolist())))
        if not cells:
            raise ValueError("image_grid data is empty")
        columns = max(item[0] for item in cells) + 1
        rows = max(item[1] for item in cells) + 1
        style = self._style(figure_object)
        artists: list[Any] = []
        for column, row in cells:
            mask = (grid_column == column) & (grid_row == row)
            unique_x = np.unique(x_values[mask])
            unique_y = np.unique(y_values[mask])
            if not len(unique_x) or not len(unique_y):
                raise ValueError("image_grid cell is empty")
            matrix = np.full((len(unique_y), len(unique_x)), np.nan, dtype=float)
            x_index = {value: index for index, value in enumerate(unique_x)}
            y_index = {value: index for index, value in enumerate(unique_y)}
            for x_value, y_value, z_value in zip(x_values[mask], y_values[mask], z_values[mask]):
                matrix[y_index[y_value], x_index[x_value]] = z_value
            if np.isnan(matrix).any():
                raise ValueError("image_grid cell is not a complete regular grid")
            inset = axis.inset_axes([column / columns, 1.0 - (row + 1) / rows, 1.0 / columns, 1.0 / rows])
            inset.set_xticks([])
            inset.set_yticks([])
            image = inset.imshow(
                matrix,
                origin=str(style.get("origin") or "upper"),
                cmap=str(style.get("cmap") or "viridis"),
                aspect="auto",
            )
            # Include the inset frame so the ChartEditor can highlight and
            # pick the whole native image-grid object, not just its pixels.
            artists.extend((image, inset.patch))
        return artists

    def _render_line(self, axis, figure_object: dict[str, Any]) -> list[Any]:
        style = self._style(figure_object)
        kwargs = {
            "color": style.get("color", "#222222"),
            "linewidth": float(style.get("line_width", 1.0)),
            "linestyle": style.get("line_style", "-"),
            "alpha": float(style.get("alpha", 1.0)),
        }
        orientation = str(figure_object.get("orientation") or "")
        if orientation == "vertical":
            return [axis.axvline(float(figure_object["x"]), **kwargs)]
        elif orientation == "horizontal":
            return [axis.axhline(float(figure_object["y"]), **kwargs)]
        else:
            return axis.plot(
                [float(figure_object["x1"]), float(figure_object["x2"])],
                [float(figure_object["y1"]), float(figure_object["y2"])],
                **kwargs,
            )

    def _render_text(self, axis, figure_object: dict[str, Any]) -> list[Any]:
        style = self._style(figure_object)
        return [axis.text(
            float(figure_object["x"]),
            float(figure_object["y"]),
            str(figure_object.get("text") or ""),
            color=style.get("color", "#222222"),
            fontsize=float(style.get("font_size", 8.0)),
            alpha=float(style.get("alpha", 1.0)),
            rotation=float(figure_object.get("rotation", 0.0) or 0.0),
            ha=str(figure_object.get("horizontal_alignment") or "center"),
            va=str(figure_object.get("vertical_alignment") or "bottom"),
        )]

    def _render_arrow(self, axis, figure_object: dict[str, Any]) -> list[Any]:
        style = self._style(figure_object)
        return [axis.annotate(
            "",
            xy=(float(figure_object["x2"]), float(figure_object["y2"])),
            xytext=(float(figure_object["x1"]), float(figure_object["y1"])),
            arrowprops={
                "arrowstyle": "->",
                "color": style.get("color", "#222222"),
                "linewidth": float(style.get("line_width", 1.0)),
                "linestyle": style.get("line_style", "-"),
                "alpha": float(style.get("alpha", 1.0)),
            },
        )]

    def _render_rectangle(self, axis, figure_object: dict[str, Any]) -> list[Any]:
        from matplotlib.patches import Rectangle

        style = self._style(figure_object)
        patch = Rectangle(
            (float(figure_object["x"]), float(figure_object["y"])),
            float(figure_object["width"]),
            float(figure_object["height"]),
            fill=bool(style.get("fill", False)),
            facecolor=style.get("color", "#222222"),
            edgecolor=style.get("color", "#222222"),
            linewidth=float(style.get("line_width", 1.0)),
            linestyle=style.get("line_style", "-"),
            alpha=float(style.get("alpha", 1.0)),
        )
        axis.add_patch(patch)
        return [patch]
