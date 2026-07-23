from __future__ import annotations

import csv
import logging
from copy import deepcopy
from pathlib import Path

import matplotlib
from PySide6.QtCore import QRect, QRectF, QSize, QSizeF
from PySide6.QtGui import QImage, QPageSize, QPainter, QPdfWriter
from PySide6.QtSvg import QSvgGenerator

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from ..i18n import tr
from ..chart_editor_generated_helpers import (
    coerce_plot_value as _shared_coerce_plot_value,
    format_generated_grid_label as _shared_format_generated_grid_label,
    optional_float as _shared_optional_float,
)
from ..chart_editor_generated_object_helpers import (
    generated_column_values as _shared_generated_column_values,
    generated_object_xy as _shared_generated_object_xy,
)
from ...plotting.sci_style import set_sci_style as _apply_sci_style
from ...core.figure_text_geometry import (
    axes_box_from_display,
    is_axes_text_box,
    text_box_anchor,
)
from ...core.figures.legend_presentation import legend_presentation
from ...core.plot_edits import COLOUR_SCHEMES, FIGURE_SIZES, LINE_WIDTHS
from ...core.figures.render_plan import FigureRenderPlanBuilder
from ...core.figures.renderer import MatplotlibFigureRenderer

logger = logging.getLogger(__name__)


class ChartEditorGeneratedDocumentMixin:
    def _show_style_preview_figure(self):
        """Create a live preview for static-file edits."""
        if self._source_path and self._show_source_image_figure():
            return

        self._show_placeholder_style_preview()

    def _is_generated_figure_document(self):
        return (
            isinstance(self._figure_document, dict)
            and self._figure_document.get("mode") == "object"
        )

    def _show_generated_figure_document(self):
        try:
            fig = self._build_generated_figure_document()
        except Exception as exc:
            logger.warning("Generated figure render failed.", exc_info=True)
            status_label = getattr(self, "_status_label", None)
            if status_label is not None:
                status_label.setText(tr("EDITOR_STATUS_RENDER_FAILED", exc))
            return False
        if fig is None:
            return False
        self._replace_canvas_figure(fig)
        return True

    def _build_generated_figure_document(self):
        if not self._is_generated_figure_document():
            return None
        self._ensure_generated_legend_object()
        entry = getattr(self, "_source_entry_context", None)
        run_root = str(getattr(entry, "run_root", "") or "").strip()
        document_path = str(getattr(entry, "document_path", "") or "").strip()
        if run_root and document_path:
            plan = FigureRenderPlanBuilder(Path(run_root)).build(
                Path(document_path),
                self._figure_document,
            )
            self._shared_render_plan = plan
            renderer = MatplotlibFigureRenderer()
            figure = renderer.render(plan, dpi=self._dpi)
            self._apply_formal_editor_style(
                figure,
                getattr(renderer, "last_artist_map", {}),
            )
            adapter = getattr(self, "_figure_render_adapter", None)
            if adapter is not None:
                adapter.reset_artist_map()
                artist_map = getattr(renderer, "last_artist_map", {})
                if isinstance(artist_map, dict):
                    for object_id, artists in artist_map.items():
                        adapter.register_artists(object_id, artists)
                    adapter.highlight_selection(
                        artist_map.get(str(self._selected_figure_object_id or ""), [])
                    )
                self._add_generated_selection_handles(
                    figure,
                    self._load_generated_document_data_sources(),
                )
            return figure

        self._shared_render_plan = None
        return self._build_legacy_generated_figure_document()

    def _apply_formal_editor_style(self, figure, artist_map):
        if figure is None or not hasattr(self, "_bg_color"):
            return
        figure.set_facecolor(self._bg_color)
        figure.set_size_inches(*self._fig_size, forward=False)
        title = self._title_edit.text().strip()
        xlabel = self._xlabel_edit.text().strip()
        ylabel = self._ylabel_edit.text().strip()
        object_types = {
            str(item.get("id") or ""): str(item.get("type") or "")
            for item in self._figure_document.get("objects", [])
            if isinstance(item, dict)
        }
        artist_to_object = {
            id(artist): object_id
            for object_id, artists in (artist_map or {}).items()
            for artist in artists or ()
        }
        series_index = 0
        for axis in figure.axes:
            axis.set_facecolor(self._bg_color)
            if title:
                axis.set_title(title, fontsize=self._title_size, fontweight="bold")
            if xlabel:
                axis.set_xlabel(xlabel, fontsize=self._label_size)
            if ylabel:
                axis.set_ylabel(ylabel, fontsize=self._label_size)
            axis.tick_params(labelsize=self._tick_size)
            if self._grid_on:
                axis.grid(
                    True,
                    alpha=self._grid_alpha,
                    linestyle="--",
                    linewidth=0.5,
                )
            else:
                axis.grid(False)
            for line in axis.lines:
                object_id = str(artist_to_object.get(id(line), "") or "")
                if object_types.get(object_id) == "plot_series":
                    line.set_color(self._current_colours[series_index % len(self._current_colours)])
                    line.set_linewidth(self._line_width)
                    series_index += 1
            for text in axis.texts:
                object_id = str(artist_to_object.get(id(text), "") or "")
                if (
                    object_types.get(object_id) == "text"
                    or str(text.get_gid() or "").startswith("pn-panel-label:")
                ):
                    continue
                text.set_fontsize(max(6, self._label_size - 2))

    @matplotlib.rc_context()
    def _build_legacy_generated_figure_document(self):
        _apply_sci_style(font_size=8.0)
        data_sources = self._load_generated_document_data_sources()
        if self._has_generated_image_grid_object():
            fig = self._build_generated_image_grid_figure(data_sources)
            if fig is not None:
                return fig
        fig, _artist_map = self._figure_render_adapter.render_document(
            document=self._figure_document,
            objects=self._generated_figure_objects(),
            figsize=self._fig_size,
            dpi=self._dpi,
            background=self._bg_color,
            render_object=lambda ax, figure_object, index: self._render_generated_figure_object(
                ax, figure_object, data_sources, index
            ),
            apply_axes_style=self._apply_generated_document_axes_style,
            selected_object_id=self._selected_figure_object_id,
        )
        if fig is None:
            return None
        self._add_generated_selection_handles(fig, data_sources)
        return fig

    def _has_generated_image_grid_object(self):
        return any(
            isinstance(obj, dict)
            and (
                obj.get("type") == "image_grid"
                or (
                    obj.get("type") == "plot_series"
                    and str(obj.get("chart_kind", "") or "") == "image_grid"
                )
            )
            and obj.get("deleted") is not True
            and obj.get("visible", True) is not False
            for obj in self._generated_figure_objects()
        )

    def _build_generated_image_grid_figure(self, data_sources):
        image_grid_object = next(
            (
                obj
                for obj in self._generated_figure_objects()
                if isinstance(obj, dict)
                and (
                    obj.get("type") == "image_grid"
                    or (
                        obj.get("type") == "plot_series"
                        and str(obj.get("chart_kind", "") or "") == "image_grid"
                    )
                )
                and obj.get("deleted") is not True
                and obj.get("visible", True) is not False
            ),
            None,
        )
        if not image_grid_object:
            return None

        records = self._load_image_grid_records(image_grid_object, data_sources)
        if not records:
            return None

        max_row = max(int(record["grid_row"]) for record in records)
        max_col = max(int(record["grid_col"]) for record in records)
        n_rows = max_row + 1
        n_cols = max_col + 1

        import matplotlib.pyplot as plt

        self._figure_render_adapter.reset_artist_map()
        fig, axes = plt.subplots(
            n_rows,
            n_cols,
            figsize=self._fig_size,
            dpi=self._dpi,
            facecolor=self._bg_color,
            squeeze=False,
        )
        fig.suptitle(
            self._title_edit.text()
            or str(self._figure_document.get("style", {}).get("title", "") or ""),
            fontsize=self._title_size,
            fontweight="bold",
        )

        grid_style = (
            image_grid_object.get("style", {})
            if isinstance(image_grid_object.get("style"), dict)
            else {}
        )
        cmap = str(
            grid_style.get("colormap")
            or grid_style.get("cmap")
            or "inferno"
        )
        object_id = str(image_grid_object.get("id", "") or "")
        artist_map: dict[str, list[object]] = {}
        for row_index in range(n_rows):
            for col_index in range(n_cols):
                axes[row_index, col_index].axis("off")

        for record in records:
            row_index = int(record["grid_row"])
            col_index = int(record["grid_col"])
            ax = axes[row_index, col_index]
            image = record["image"]
            if image is None:
                continue
            image_artist = ax.imshow(
                image,
                cmap=cmap,
                origin=str(
                    grid_style.get("origin")
                    or self._figure_document.get("style", {}).get("origin", "lower")
                    or "lower"
                ),
            )
            artists = [image_artist, ax.patch]
            label = self._format_generated_grid_label(record.get("label", ""))
            if label:
                artists.append(ax.set_title(label, fontsize=self._tick_size))
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_visible(False)
            artist_map.setdefault(object_id, []).extend(
                self._figure_render_adapter.register_artists(object_id, artists)
            )

        self._figure_render_adapter.highlight_selection(
            artist_map.get(str(self._selected_figure_object_id or ""), [])
        )
        self._add_generated_selection_handles(fig, data_sources)

        fig.tight_layout()
        return fig

    def _load_image_grid_records(self, figure_object, data_sources):
        data_ref = str(figure_object.get("data_ref", "") or "")
        if not data_ref:
            return []

        source = next(
            (
                item
                for item in self._figure_document.get("data_sources", [])
                if isinstance(item, dict) and str(item.get("id", "") or "") == data_ref
            ),
            None,
        )
        if not source:
            return []

        rows = []
        source_values = data_sources.get(data_ref)
        if isinstance(source_values, dict) and source_values:
            row_count = max(
                (len(values) for values in source_values.values() if isinstance(values, list)),
                default=0,
            )
            for row_index in range(row_count):
                rows.append(
                    {
                        column: values[row_index] if row_index < len(values) else ""
                        for column, values in source_values.items()
                        if isinstance(values, list)
                    }
                )

        if not rows:
            source_path = str(source.get("path", "") or "")
            if not source_path:
                return []

            path = self._resolve_generated_source_path(source_path)
            if not path.exists():
                return []

            try:
                with path.open("r", encoding="utf-8-sig", newline="") as handle:
                    rows = list(csv.DictReader(handle))
            except Exception:
                logger.warning("Failed to load image grid metadata.", exc_info=True)
                return []

        numeric_records = self._numeric_image_grid_records(rows, figure_object)
        if numeric_records:
            return numeric_records

        records = []
        for row in rows:
            grid_row = self._optional_float(
                row.get(
                    str(figure_object.get("row_column", "grid_row") or "grid_row")
                )
            )
            grid_col = self._optional_float(
                row.get(
                    str(figure_object.get("column_column", "grid_col") or "grid_col")
                )
            )
            if grid_row is None or grid_col is None:
                continue
            image_path = str(
                row.get(
                    str(
                        figure_object.get("image_path_column", "image_path")
                        or "image_path"
                    ),
                    "",
                )
                or ""
            ).strip()
            if not image_path:
                continue
            image_file = self._resolve_generated_source_path(image_path)
            if not image_file.exists():
                continue
            try:
                import numpy as np

                image = np.load(image_file)
            except Exception:
                logger.warning("Failed to load image grid matrix.", exc_info=True)
                continue
            records.append(
                {
                    "grid_row": int(grid_row),
                    "grid_col": int(grid_col),
                    "label": row.get(
                        str(
                            figure_object.get("label_column", "strain_pct")
                            or "strain_pct"
                        ),
                        "",
                    ),
                    "image": image,
                }
            )
        records.sort(key=lambda item: (item["grid_row"], item["grid_col"]))
        return records

    def _numeric_image_grid_records(self, rows, figure_object):
        """Rebuild editable grid cells from portable numeric pixel rows."""
        if not isinstance(rows, list) or not rows:
            return []
        row_column = str(
            figure_object.get("grid_row")
            or figure_object.get("row_column")
            or "grid_row"
        )
        column_column = str(
            figure_object.get("grid_column")
            or figure_object.get("column_column")
            or "grid_column"
        )
        x_column = str(figure_object.get("x_column") or "pixel_x")
        y_column = str(figure_object.get("y_column") or "pixel_y")
        z_column = str(
            figure_object.get("z_column")
            or figure_object.get("value_column")
            or "intensity"
        )
        label_column = str(figure_object.get("label_column") or "strain_pct")

        # Older sidecars called the grid column ``grid_col``.  Keep that
        # spelling as a read-only compatibility alias when no explicit column
        # is present in the portable rows.
        def value(row, key, *aliases):
            for candidate in (key, *aliases):
                if candidate in row:
                    return row.get(candidate)
            return None

        import numpy as np

        cells: dict[tuple[int, int], list[tuple[float, float, float]]] = {}
        labels: dict[tuple[int, int], object] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            grid_row = self._optional_float(value(row, row_column))
            grid_col = self._optional_float(
                value(row, column_column, "grid_col" if column_column == "grid_column" else "grid_column")
            )
            x_value = self._optional_float(value(row, x_column))
            y_value = self._optional_float(value(row, y_column))
            z_value = self._optional_float(value(row, z_column))
            numeric_values = (grid_row, grid_col, x_value, y_value, z_value)
            if any(
                value is None or not np.isfinite(value) for value in numeric_values
            ):
                continue
            cell = (int(grid_row), int(grid_col))
            cells.setdefault(cell, []).append(
                (float(x_value), float(y_value), float(z_value))
            )
            labels.setdefault(cell, value(row, label_column, "strain", "label"))

        records = []
        for (grid_row, grid_col), points in cells.items():
            unique_x = sorted({point[0] for point in points})
            unique_y = sorted({point[1] for point in points})
            if not unique_x or not unique_y:
                continue
            matrix = np.full((len(unique_y), len(unique_x)), np.nan, dtype=float)
            x_index = {value: index for index, value in enumerate(unique_x)}
            y_index = {value: index for index, value in enumerate(unique_y)}
            for x_value, y_value, z_value in points:
                matrix[y_index[y_value], x_index[x_value]] = z_value
            if np.isnan(matrix).any():
                continue
            records.append(
                {
                    "grid_row": grid_row,
                    "grid_col": grid_col,
                    "label": labels.get((grid_row, grid_col), ""),
                    "image": matrix,
                }
            )
        records.sort(key=lambda item: (item["grid_row"], item["grid_col"]))
        return records

    def _format_generated_grid_label(self, value):
        return _shared_format_generated_grid_label(value)

    def _generated_document_root(self):
        return (
            Path(self._source_path).resolve().parent if self._source_path else Path.cwd()
        )

    def _resolve_generated_source_path(self, source_path):
        path = Path(str(source_path or ""))
        if path.is_absolute():
            return path
        document_root = self._generated_document_root()
        candidate = document_root / path
        if candidate.exists():
            return candidate
        # Portable WAXS documents may store paths relative to their run root,
        # while a no-manifest editor only knows the figure asset directory.
        for parent in document_root.parents:
            candidate = parent / path
            if candidate.exists():
                return candidate
        return document_root / path

    def _load_generated_document_data_sources(self):
        data_sources = {}
        for source in self._figure_document.get("data_sources", []):
            source_id = str(source.get("id", "") or "")
            source_path = str(source.get("path", "") or "")
            if not source_id or not source_path:
                continue
            path = self._resolve_generated_source_path(source_path)
            if not path.exists():
                continue
            if source.get("kind") == "csv":
                try:
                    with path.open("r", encoding="utf-8-sig", newline="") as handle:
                        rows = list(csv.DictReader(handle))
                except Exception:
                    logger.warning(
                        "Failed to load generated figure data source.",
                        exc_info=True,
                    )
                    continue
                columns = {}
                for row in rows:
                    for key, value in row.items():
                        columns.setdefault(key, []).append(self._coerce_plot_value(value))
                data_sources[source_id] = columns
            elif source.get("kind") == "npy":
                try:
                    import numpy as np

                    data_sources[source_id] = np.load(path)
                except Exception:
                    logger.warning(
                        "Failed to load generated figure image data source.",
                        exc_info=True,
                    )
        return data_sources

    def _render_generated_figure_object(self, ax, figure_object, data_sources, index):
        object_type = str(figure_object.get("type", "") or "")
        chart_kind = str(figure_object.get("chart_kind", "") or "")
        style = (
            figure_object.get("style", {})
            if isinstance(figure_object.get("style"), dict)
            else {}
        )
        color = style.get("color") or self._current_colours[
            index % len(self._current_colours)
        ]
        line_width = float(style.get("line_width", self._line_width) or self._line_width)
        alpha = float(style.get("alpha", 1.0) or 1.0)
        marker_size = float(style.get("marker_size", 6.0) or 6.0)
        name = str(figure_object.get("name", "") or "")

        if object_type == "plot_series":
            if chart_kind == "heatmap":
                return self._render_generated_heatmap(ax, figure_object, data_sources)
            x_values, y_values = self._generated_object_xy(figure_object, data_sources)
            if not x_values or not y_values:
                return []
            if chart_kind == "bar":
                container = ax.bar(
                    x_values,
                    y_values,
                    color=color,
                    alpha=alpha,
                    label=name or None,
                )
                return list(container.patches)
            if chart_kind == "barh":
                container = ax.barh(
                    y_values,
                    x_values,
                    color=color,
                    alpha=alpha,
                    label=name or None,
                )
                return list(container.patches)
            if chart_kind == "scatter":
                marker = self._generated_plot_series_marker_value(figure_object) or "o"
                return ax.scatter(
                    x_values,
                    y_values,
                    color=color,
                    alpha=alpha,
                    label=name or None,
                    marker=marker,
                    s=marker_size ** 2,
                    linewidths=line_width,
                )
            return ax.plot(
                x_values,
                y_values,
                color=color,
                linewidth=line_width,
                linestyle=style.get("line_style", "-"),
                alpha=alpha,
                label=name or None,
                marker=style.get("marker") or None,
                markersize=marker_size,
            )

        if object_type == "line":
            x1 = self._optional_float(figure_object.get("x1"))
            x2 = self._optional_float(figure_object.get("x2"))
            y1 = self._optional_float(figure_object.get("y1"))
            y2 = self._optional_float(figure_object.get("y2"))
            if x1 is None or y1 is None:
                return []
            if x2 is None:
                return ax.axvline(
                    x1,
                    color=color,
                    linewidth=line_width,
                    linestyle=style.get("line_style", "-"),
                    alpha=alpha,
                    label=name or None,
                )
            if y2 is None:
                return ax.axhline(
                    y1,
                    color=color,
                    linewidth=line_width,
                    linestyle=style.get("line_style", "-"),
                    alpha=alpha,
                    label=name or None,
                )
            return ax.plot(
                [x1, x2],
                [y1, y2],
                color=color,
                linewidth=line_width,
                linestyle=style.get("line_style", "-"),
                alpha=alpha,
                label=name or None,
            )

        if object_type == "curve":
            from matplotlib.patches import PathPatch
            from matplotlib.path import Path

            bounds = (
                figure_object.get("bounds", {})
                if isinstance(figure_object.get("bounds"), dict)
                else {}
            )

            def curve_value(name):
                value = figure_object.get(name)
                if value is None:
                    value = bounds.get(name)
                return self._optional_float(value)

            x1 = curve_value("x1")
            y1 = curve_value("y1")
            x2 = curve_value("x2")
            y2 = curve_value("y2")
            control_x = curve_value("control_x")
            control_y = curve_value("control_y")
            if None in {x1, y1, x2, y2}:
                return []
            control_x = float(control_x if control_x is not None else (x1 + x2) / 2.0)
            control_y = float(control_y if control_y is not None else (y1 + y2) / 2.0)
            patch = PathPatch(
                Path(
                    [(x1, y1), (control_x, control_y), (x2, y2)],
                    [Path.MOVETO, Path.CURVE3, Path.CURVE3],
                ),
                fill=False,
                edgecolor=color,
                linewidth=line_width,
                linestyle=style.get("line_style", "-"),
                alpha=alpha,
            )
            ax.add_patch(patch)
            return [patch]

        if object_type == "text":
            bounds = (
                figure_object.get("bounds", {})
                if isinstance(figure_object.get("bounds"), dict)
                else {}
            )
            x = self._optional_float(bounds.get("x", figure_object.get("x")))
            y = self._optional_float(bounds.get("y", figure_object.get("y")))
            width = self._optional_float(bounds.get("width", figure_object.get("width")))
            height = self._optional_float(bounds.get("height", figure_object.get("height")))
            has_box = width is not None and width > 0.0 and height is not None and height > 0.0
            horizontal_alignment = str(
                figure_object.get(
                    "horizontal_alignment", "left" if has_box else "center"
                )
                or ("left" if has_box else "center")
            )
            vertical_alignment = str(
                figure_object.get("vertical_alignment", "top" if has_box else "bottom")
                or ("top" if has_box else "bottom")
            )
            anchor_x, anchor_y = text_box_anchor(
                float(x or 0.0),
                float(y or 0.0),
                float(width or 0.0),
                float(height or 0.0),
                horizontal_alignment=horizontal_alignment,
                vertical_alignment=vertical_alignment,
            )
            is_axes_label = is_axes_text_box(figure_object)
            text_kwargs = {}
            if width is not None and width > 0.0 and not is_axes_label:
                text_kwargs.update(wrap=True, clip_on=True)
            if is_axes_label:
                text_kwargs["transform"] = ax.transAxes
            return [
                ax.text(
                    anchor_x,
                    anchor_y,
                    str(figure_object.get("text", "") or ""),
                    color=color,
                    fontsize=float(style.get("font_size", 12.0) or 12.0),
                    alpha=alpha,
                    rotation=float(figure_object.get("rotation", 0.0) or 0.0),
                    ha=horizontal_alignment,
                    va=vertical_alignment,
                    **text_kwargs,
                )
            ]

        if object_type == "arrow":
            x1 = self._optional_float(figure_object.get("x1"))
            y1 = self._optional_float(figure_object.get("y1"))
            x2 = self._optional_float(figure_object.get("x2"))
            y2 = self._optional_float(figure_object.get("y2"))
            if None in {x1, y1, x2, y2}:
                return []
            return [
                ax.annotate(
                    "",
                    xy=(x2, y2),
                    xytext=(x1, y1),
                    arrowprops={
                        "arrowstyle": "->",
                        "color": color,
                        "linewidth": line_width,
                        "linestyle": style.get("line_style", "-"),
                        "alpha": alpha,
                    },
                )
            ]

        if object_type == "rectangle":
            from matplotlib.patches import Rectangle

            bounds = (
                figure_object.get("bounds", {})
                if isinstance(figure_object.get("bounds"), dict)
                else figure_object
            )
            x = self._optional_float(bounds.get("x"))
            y = self._optional_float(bounds.get("y"))
            width = self._optional_float(bounds.get("width"))
            height = self._optional_float(bounds.get("height"))
            if None in {x, y, width, height}:
                return []
            patch = Rectangle(
                (x, y),
                width,
                height,
                fill=bool(style.get("fill", False)),
                facecolor=color,
                edgecolor=color,
                linewidth=line_width,
                linestyle=style.get("line_style", "-"),
                alpha=alpha,
            )
            ax.add_patch(patch)
            return [patch]

        if object_type == "highlight":
            x_values = self._generated_column_values(figure_object, data_sources, "x_column")
            lower = self._generated_column_values(
                figure_object,
                data_sources,
                "lower_y_column",
            )
            upper = self._generated_column_values(
                figure_object,
                data_sources,
                "upper_y_column",
            )
            if not x_values or not lower or not upper:
                return []
            return ax.fill_between(
                x_values,
                lower,
                upper,
                color=color,
                alpha=float(style.get("alpha", 0.2) or 0.2),
                label=name or None,
            )

        return []

    def _render_generated_heatmap(self, ax, figure_object, data_sources):
        columns = data_sources.get(str(figure_object.get("data_ref", "") or ""), {})
        x_key = str(figure_object.get("x_column", "") or "")
        y_key = str(figure_object.get("y_column", "") or "")
        value_key = str(figure_object.get("value_column", "") or "")
        if not x_key or not y_key or not value_key:
            return []
        x_values = columns.get(x_key, [])
        y_values = columns.get(y_key, [])
        z_values = columns.get(value_key, [])
        if not x_values or not y_values or not z_values:
            return []
        try:
            import numpy as np

            unique_x = sorted({float(value) for value in x_values if value is not None})
            unique_y = sorted({float(value) for value in y_values if value is not None})
            matrix = np.full((len(unique_y), len(unique_x)), np.nan)
            x_index = {value: i for i, value in enumerate(unique_x)}
            y_index = {value: i for i, value in enumerate(unique_y)}
            for x_value, y_value, z_value in zip(x_values, y_values, z_values):
                if x_value is None or y_value is None or z_value is None:
                    continue
                matrix[y_index[float(y_value)], x_index[float(x_value)]] = float(
                    z_value
                )
            style = (
                figure_object.get("style", {})
                if isinstance(figure_object.get("style"), dict)
                else {}
            )
            mesh = ax.pcolormesh(
                unique_x,
                unique_y,
                matrix,
                cmap=style.get("colormap", "viridis"),
                shading="auto",
            )
            ax.figure.colorbar(mesh, ax=ax)
            return mesh
        except Exception:
            logger.warning("Failed to render generated heatmap object.", exc_info=True)
            return []

    def _generated_object_xy(self, figure_object, data_sources):
        return _shared_generated_object_xy(figure_object, data_sources)

    def _convert_legacy_generated_text_objects_for_save(self, document):
        """Materialize legacy data-coordinate text as Axes-relative boxes."""

        if not isinstance(document, dict) or self._figure is None or not self._figure.axes:
            return False
        renderer = None
        try:
            renderer = self._canvas.get_renderer()
        except (AttributeError, RuntimeError):
            renderer = None
        if renderer is None:
            try:
                self._canvas.draw()
                renderer = self._canvas.get_renderer()
            except (AttributeError, RuntimeError):
                return False
        changed = False
        objects = document.get("objects", [])
        for figure_object in objects if isinstance(objects, list) else []:
            if is_axes_text_box(figure_object):
                continue
            if not isinstance(figure_object, dict) or figure_object.get("type") != "text":
                continue
            artists = self._figure_render_adapter.artists_for_object_id(
                str(figure_object.get("id", "") or "")
            )
            artist = next((item for item in artists if hasattr(item, "get_window_extent")), None)
            axes = getattr(artist, "axes", None) or self._figure.axes[0]
            if artist is None or axes is None:
                continue
            try:
                extent = artist.get_window_extent(renderer)
                geometry = axes_box_from_display(
                    (extent.x0, extent.y0, extent.width, extent.height),
                    axes.transAxes,
                )
            except (AttributeError, RuntimeError, TypeError, ValueError):
                continue
            figure_object["coordinate_space"] = "axes"
            figure_object["bounds"] = dict(geometry)
            figure_object.update(geometry)
            changed = True
        return changed

    def _generated_column_values(self, figure_object, data_sources, key):
        return _shared_generated_column_values(figure_object, data_sources, key)

    def _add_generated_selection_handles(self, fig, data_sources):
        if fig is None or not self._selected_figure_object_id:
            return
        figure_object = self._generated_figure_object_by_id(self._selected_figure_object_id)
        if not figure_object:
            return
        object_type = str(figure_object.get("type", "") or "")
        chart_kind = str(figure_object.get("chart_kind", "") or "")
        selected_handle_index = None
        if object_type == "line":
            selected_handle_index = self._selected_generated_line_handle_index_for_object(
                figure_object
            )
        if object_type == "plot_series" and chart_kind not in {
            "heatmap",
            "bar",
            "barh",
            "image_grid",
        }:
            inline_data = figure_object.get("data", {})
            if not (
                isinstance(inline_data, dict)
                and inline_data.get("x")
                and inline_data.get("y")
            ):
                x_values, y_values = self._generated_object_xy(figure_object, data_sources)
                if x_values and y_values:
                    figure_object = deepcopy(figure_object)
                    figure_object["data"] = {"x": x_values, "y": y_values}
            selected_handle_index = self._selected_generated_plot_series_point_index(
                figure_object
            )
        target_axes = fig.axes[0] if fig.axes else None
        if target_axes is None:
            return
        self._figure_render_adapter.add_selection_frame(target_axes, figure_object)
        self._figure_render_adapter.add_selection_handles(
            target_axes,
            figure_object,
            selected_handle_index=selected_handle_index,
        )

    def _apply_generated_document_axes_style(self, ax):
        style = self._figure_document.get("style", {})
        if not isinstance(style, dict):
            style = {}
        title = self._title_edit.text() or str(style.get("title", "") or "")
        xlabel = self._xlabel_edit.text() or str(style.get("xlabel", "") or "")
        ylabel = self._ylabel_edit.text() or str(style.get("ylabel", "") or "")
        if title:
            ax.set_title(title, fontsize=self._title_size, fontweight="bold")
        if xlabel:
            ax.set_xlabel(xlabel, fontsize=self._label_size)
        if ylabel:
            ax.set_ylabel(ylabel, fontsize=self._label_size)
        ax.tick_params(labelsize=self._tick_size)
        if self._grid_on:
            ax.grid(True, alpha=self._grid_alpha, linestyle="--", linewidth=0.5)
        else:
            ax.grid(False)
        for spine in ax.spines.values():
            spine.set_linewidth(0.8)
        handles, _labels = ax.get_legend_handles_labels()
        legend_object = self._generated_figure_object_by_id_including_deleted("legend")
        automatic_legend_series_count = sum(
            1
            for figure_object in self._figure_document.get("objects", [])
            if isinstance(figure_object, dict)
            and str(figure_object.get("type", "") or "") == "plot_series"
            and figure_object.get("visible", True) is not False
            and figure_object.get("deleted") is not True
            and str(figure_object.get("name", "") or "").strip()
        )
        if (
            handles
            and self._generated_legend_visible()
            and (
                not isinstance(legend_object, dict)
                or legend_object.get("auto_generated") is not True
                or automatic_legend_series_count >= 2
            )
        ):
            legend_style = (
                legend_object.get("style", {})
                if isinstance(legend_object, dict)
                and isinstance(legend_object.get("style"), dict)
                else {}
            )
            canvas = getattr(self, "_canvas", None)
            canvas_width = (
                float(canvas.width())
                if canvas is not None and callable(getattr(canvas, "width", None))
                else float(ax.bbox.width)
            )
            presentation = legend_presentation(
                legend_object,
                handle_count=len(handles),
                available_width_px=max(1.0, canvas_width),
                default_fontsize=9.0,
            )
            bbox_to_anchor = legend_style.get("bbox_to_anchor")
            anchor_x = None
            anchor_y = None
            if isinstance(bbox_to_anchor, (list, tuple)) and len(bbox_to_anchor) >= 2:
                anchor_x = self._optional_float(bbox_to_anchor[0])
                anchor_y = self._optional_float(bbox_to_anchor[1])
            if anchor_x is not None and anchor_y is not None:
                ax.legend(
                    fontsize=presentation.fontsize,
                    frameon=False,
                    ncol=presentation.ncol,
                    loc=str(legend_style.get("loc", "") or "upper left"),
                    bbox_to_anchor=(float(anchor_x), float(anchor_y)),
                    bbox_transform=ax.transAxes,
                )
            else:
                ax.legend(
                    fontsize=presentation.fontsize,
                    frameon=False,
                    ncol=presentation.ncol,
                    loc=str(legend_style.get("loc", "") or "upper right"),
                )
        elif ax.get_legend() is not None:
            ax.get_legend().remove()

    def _coerce_plot_value(self, value):
        return _shared_coerce_plot_value(value)

    def _optional_float(self, value):
        return _shared_optional_float(value)

    def _show_source_image_figure(self):
        fig = self._build_source_image_figure()
        if fig is None:
            return False

        self._replace_canvas_figure(fig)
        return True

    def _build_source_image_figure(self):
        image = self._load_source_image_array()
        if image is None:
            return None

        fig = Figure(figsize=self._fig_size, dpi=self._dpi, facecolor=self._bg_color)
        ax = fig.add_subplot(111)
        ax.imshow(image)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)

        title = self._title_edit.text()
        if title:
            ax.set_title(title, fontsize=self._title_size, fontweight="bold")

        xlabel = self._xlabel_edit.text()
        if xlabel:
            ax.set_xlabel(xlabel, fontsize=self._label_size)

        ylabel = self._ylabel_edit.text()
        if ylabel:
            ax.set_ylabel(ylabel, fontsize=self._label_size)

        fig.tight_layout()
        return fig

    def _refresh_static_annotation_canvas_preview(self):
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return False
        fig = self._build_source_image_figure()
        if fig is None:
            return False
        try:
            image = self._figure_to_qimage(fig)
        finally:
            fig.clear()
        if image.isNull():
            return False
        return self._annotation_canvas.replace_image(image)

    def _figure_to_qimage(self, fig):
        canvas = FigureCanvasAgg(fig)
        canvas.draw()
        buffer, (width, height) = canvas.print_to_buffer()
        image = QImage(buffer, width, height, QImage.Format_RGBA8888)
        return image.copy()

    def _load_source_image_array(self):
        if not self._source_path:
            return None
        try:
            pixmap = self._source_preview._load_pixmap(self._source_path)
            if pixmap is None or pixmap.isNull():
                return None
            image = pixmap.toImage().convertToFormat(QImage.Format_RGBA8888)
            width = image.width()
            height = image.height()
            if width <= 0 or height <= 0:
                return None
            bytes_per_line = image.bytesPerLine()
            buffer = bytes(image.constBits())
            import numpy as np

            array = np.frombuffer(buffer, dtype=np.uint8).reshape(
                (height, bytes_per_line)
            )
            array = array[:, : width * 4].reshape((height, width, 4))
            return array.copy()
        except Exception:
            logger.warning("Failed to render static source figure for editing.", exc_info=True)
            return None

    def _save_static_rendered_figure(self, path):
        if not self._show_source_image_figure():
            return False
        ext = path.suffix.lower().lstrip(".") or "png"
        if ext == "jpg":
            ext = "jpeg"
        try:
            self._figure.savefig(
                str(path),
                format=ext,
                dpi=300 if ext in {"png", "jpeg", "jpg", "tiff"} else self._dpi,
                bbox_inches="tight",
                facecolor=self._bg_color,
            )
            return True
        except Exception:
            logger.warning("Failed to save static rendered figure.", exc_info=True)
            return False

    def _save_static_canvas_to_path(self, path):
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return False
        ext = path.suffix.lower().lstrip(".") or "png"
        if ext == "jpg":
            ext = "jpeg"
        if ext in {"pdf", "svg"}:
            return self._save_static_canvas_vector(path, ext)
        image = self._annotation_canvas.render_to_image(self._bg_color)
        if image.isNull():
            return False
        if ext not in {"png", "jpeg", "jpg", "bmp", "tiff", "tif"}:
            return False
        return bool(image.save(str(path), ext.upper()))

    def _save_static_canvas_vector(self, path, ext):
        scene = self._annotation_canvas._scene
        rect = scene.sceneRect()
        if rect.isNull():
            return False

        width = max(1, int(rect.width()))
        height = max(1, int(rect.height()))
        if ext == "pdf":
            device = QPdfWriter(str(path))
            device.setResolution(72)
            device.setPageSize(QPageSize(QSizeF(width, height), QPageSize.Point))
        elif ext == "svg":
            device = QSvgGenerator()
            device.setFileName(str(path))
            device.setSize(QSize(width, height))
            device.setViewBox(QRect(0, 0, width, height))
        else:
            return False

        painter = QPainter()
        if not painter.begin(device):
            return False
        try:
            target = QRectF(0, 0, width, height)
            painter.fillRect(target, self._bg_color)
            self._annotation_canvas.render_scene(painter, target, rect)
        finally:
            painter.end()
        return path.exists() and path.stat().st_size > 0

    def _replace_canvas_figure(self, fig):
        import matplotlib.pyplot as plt

        old = self._canvas.figure
        self._hovered_figure_object_id = ""
        captured_here = False
        if getattr(self, "_generated_viewport_snapshot", None) is None:
            capture = getattr(self, "_capture_generated_viewport", None)
            if callable(capture):
                capture()
                captured_here = True
        self._canvas.figure = fig
        self._figure = fig
        self._restore_generated_viewport()
        # The Qt canvas can normalize a replacement Figure to logical pixels,
        # and viewport restoration can restore the old logical figure size;
        # apply the live-canvas device-pixel fit after both operations.
        self._fit_figure_to_live_canvas(fig)
        if captured_here:
            self._generated_viewport_snapshot = None
        self._connect_canvas_interaction_events()
        self._canvas.draw()
        if old:
            plt.close(old)

    @matplotlib.rc_context()
    def _show_placeholder_style_preview(self):
        """Create a placeholder figure showing current style when the source cannot render."""
        _apply_sci_style(font_size=8.0)

        fig = Figure(figsize=self._fig_size, dpi=self._dpi, facecolor=self._bg_color)
        ax = fig.add_subplot(111)

        import numpy as np

        x = np.linspace(0, 10, 200)
        for i, color in enumerate(self._current_colours[:3]):
            ax.plot(
                x,
                np.sin(x + i * 1.5) + i * 2,
                color=color,
                linewidth=self._line_width,
                label=f"Curve {i + 1}",
            )

        title = self._title_edit.text()
        if title:
            ax.set_title(title, fontsize=self._title_size, fontweight="bold")

        xlabel = self._xlabel_edit.text()
        if xlabel:
            ax.set_xlabel(xlabel, fontsize=self._label_size)

        ylabel = self._ylabel_edit.text()
        if ylabel:
            ax.set_ylabel(ylabel, fontsize=self._label_size)

        ax.tick_params(labelsize=self._tick_size)
        ax.grid(self._grid_on, alpha=self._grid_alpha, linestyle="--", linewidth=0.5)
        for spine in ax.spines.values():
            spine.set_linewidth(0.8)

        if self._current_colours:
            ax.legend(fontsize=self._tick_size, frameon=False)
        ax.text(
            0.02,
            0.98,
            "Style Preview - data for illustration only",
            transform=ax.transAxes,
            fontsize=7,
            color="#999999",
            va="top",
            ha="left",
        )

        self._replace_canvas_figure(fig)

    def _apply_sci_defaults(self):
        """Reset all ChartEditor controls to SCI journal defaults."""
        self._set_line_edit(self._title_edit, "")
        self._bg_color = "#FFFFFF"

        idx = self._colour_cb.findText("Wong (SCI)")
        if idx >= 0:
            self._colour_cb.setCurrentIndex(idx)
        self._current_colours = list(COLOUR_SCHEMES["Wong (SCI)"])

        idx = self._font_cb.findText("Small")
        if idx >= 0:
            self._font_cb.setCurrentIndex(idx)
        self._set_font_size("Small")

        idx = self._lw_cb.findText("Normal")
        if idx >= 0:
            self._lw_cb.setCurrentIndex(idx)
        self._line_width = LINE_WIDTHS["Normal"]

        idx = self._figsize_cb.findText("Small (4in)")
        if idx >= 0:
            self._figsize_cb.setCurrentIndex(idx)
        self._fig_size = FIGURE_SIZES["Small (4in)"]

        self._grid_cb.setChecked(False)
        self._grid_on = False
        self._grid_alpha = 0.0

        self._render()
        self._status_label.setText(tr("EDITOR_APPLY_SCI_DONE"))
