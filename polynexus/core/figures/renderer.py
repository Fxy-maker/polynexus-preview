"""Core Matplotlib rendering for FigureRenderPlan."""

from __future__ import annotations

from typing import Any

from matplotlib.figure import Figure

from .render_plan import FigureRenderPlan, RenderAxis


class MatplotlibFigureRenderer:
    def render(self, plan: FigureRenderPlan, *, dpi: int) -> Figure:
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
            axis = figure.add_subplot(grid[panel.row, panel.column])
            axis.set_xlabel(self._axis_label(panel.x_axis))
            axis.set_ylabel(self._axis_label(panel.y_axis))
            axis.set_xscale(panel.x_axis.scale)
            axis.set_yscale(panel.y_axis.scale)
            if panel.x_axis.reversed:
                axis.invert_xaxis()
            if panel.y_axis.reversed:
                axis.invert_yaxis()
            axes[panel.panel_id] = axis

        for figure_object in sorted(
            plan.objects,
            key=lambda item: int(item.get("z_index", 0) or 0),
        ):
            if figure_object.get("visible") is False:
                continue
            panel_id = str(figure_object.get("panel_id") or "")
            if panel_id not in axes:
                raise ValueError(f"unknown render panel: {panel_id}")
            axis = axes[panel_id]
            object_type = str(figure_object.get("type") or "")
            if object_type == "plot_series":
                self._render_plot_series(axis, plan, figure_object)
            elif object_type == "line":
                self._render_line(axis, figure_object)
            elif object_type == "text":
                self._render_text(axis, figure_object)
            else:
                raise ValueError(f"unsupported render object type: {object_type}")

        return figure

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
    ) -> None:
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
        axis.plot(table[x_column], table[y_column], **kwargs)

    def _render_line(self, axis, figure_object: dict[str, Any]) -> None:
        style = self._style(figure_object)
        kwargs = {
            "color": style.get("color", "#222222"),
            "linewidth": float(style.get("line_width", 1.0)),
            "linestyle": style.get("line_style", "-"),
            "alpha": float(style.get("alpha", 1.0)),
        }
        orientation = str(figure_object.get("orientation") or "")
        if orientation == "vertical":
            axis.axvline(float(figure_object["x"]), **kwargs)
        elif orientation == "horizontal":
            axis.axhline(float(figure_object["y"]), **kwargs)
        else:
            axis.plot(
                [float(figure_object["x1"]), float(figure_object["x2"])],
                [float(figure_object["y1"]), float(figure_object["y2"])],
                **kwargs,
            )

    def _render_text(self, axis, figure_object: dict[str, Any]) -> None:
        style = self._style(figure_object)
        axis.text(
            float(figure_object["x"]),
            float(figure_object["y"]),
            str(figure_object.get("text") or ""),
            color=style.get("color", "#222222"),
            fontsize=float(style.get("font_size", 8.0)),
            alpha=float(style.get("alpha", 1.0)),
            rotation=float(figure_object.get("rotation", 0.0) or 0.0),
            ha=str(figure_object.get("horizontal_alignment") or "center"),
            va=str(figure_object.get("vertical_alignment") or "bottom"),
        )
