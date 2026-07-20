from __future__ import annotations

from copy import deepcopy

from matplotlib.collections import PathCollection

from ...core.figure_edit_commands import (
    UpdateGeometryCommand,
    UpdateStyleCommand,
)
from ...core.figure_object_store import FigureObjectStore

GENERATED_LEGEND_HIT_SLOP_PX = 6.0


class ChartEditorGeneratedGeometryMixin:
    def _generated_line_artist(self, object_id):
        if self._figure is None or not self._figure.axes:
            return None
        for artist in self._figure.axes[0].lines:
            if self._figure_render_adapter.object_id_for_artist(artist) == object_id:
                return artist
        return None

    def _generated_hover_handle_artist(self):
        if self._figure is None:
            return None
        for axes in self._figure.axes:
            for artist in axes.collections:
                gid = str(artist.get_gid() or "")
                if gid.startswith("pn-hover-handle:"):
                    return artist
        return None

    def _generated_current_handle_artist(self, object_id):
        if self._figure is None:
            return None
        expected_gid = f"pn-current-handle:{str(object_id or '')}"
        for axes in self._figure.axes:
            for artist in axes.collections:
                if artist.get_gid() == expected_gid:
                    return artist
        return None

    def _generated_event_data_coordinates(self, event):
        axes = getattr(event, "inaxes", None)
        if axes is None:
            axes = self._figure.axes[0] if self._figure.axes else None
        if axes is None:
            return None
        x_value = getattr(event, "xdata", None)
        y_value = getattr(event, "ydata", None)
        if x_value is None or y_value is None:
            try:
                x_value, y_value = axes.transData.inverted().transform(
                    [float(getattr(event, "x", 0.0) or 0.0), float(getattr(event, "y", 0.0) or 0.0)]
                )
            except Exception:
                return None
        try:
            return round(float(x_value), 12), round(float(y_value), 12)
        except (TypeError, ValueError):
            return None

    def _generated_event_axes_fraction(self, event, axes=None):
        if axes is None:
            axes = getattr(event, "inaxes", None)
        if axes is None:
            axes = self._figure.axes[0] if self._figure.axes else None
        if axes is None:
            return None
        try:
            anchor_x, anchor_y = axes.transAxes.inverted().transform(
                [float(getattr(event, "x", 0.0) or 0.0), float(getattr(event, "y", 0.0) or 0.0)]
            )
        except Exception:
            return None
        try:
            return round(float(anchor_x), 12), round(float(anchor_y), 12)
        except (TypeError, ValueError):
            return None

    def _apply_generated_line_handle_drag(self, object_id, handle_index, x_value, y_value):
        figure_object = self._generated_figure_object_by_id(object_id)
        if not figure_object:
            return False
        geometry = self._generated_object_geometry_config(figure_object)
        mode = str(geometry.get("mode", "segment") or "segment")
        if mode == "vertical":
            updates = {"x1": float(x_value)}
        elif mode == "horizontal":
            updates = {"y1": float(y_value)}
        elif int(handle_index or 0) <= 0:
            updates = {"x1": float(x_value), "y1": float(y_value)}
        else:
            updates = {"x2": float(x_value), "y2": float(y_value)}
        drag_state = self._generated_drag_preview_mode(object_id)
        if drag_state is not None:
            original_object = drag_state.get("original_object")
            original_geometry = self._generated_persisted_geometry(
                original_object if isinstance(original_object, dict) else figure_object
            )
            preview_geometry = deepcopy(original_geometry)
            preview_geometry.update(updates)
            return self._update_generated_drag_preview(
                object_id,
                preview_geometry,
                object_type="line",
            )
        session = self._edit_session_for_adapter()
        if session is not None:
            session.select(object_id, "generated-canvas")
            result = self._execute_edit(UpdateGeometryCommand(object_id, updates))
            if result is not None and result.changed:
                self._sync_generated_object_property_controls(object_id)
                self._update_generated_line_preview(object_id)
                axes = self._figure.axes[0] if self._figure and self._figure.axes else None
                if axes is not None:
                    point = (
                        [updates.get("x1"), updates.get("y1")]
                        if int(handle_index or 0) <= 0
                        else [updates.get("x2"), updates.get("y2")]
                    )
                    for artist in axes.collections:
                        if artist.get_gid() == f"pn-current-handle:{object_id}":
                            artist.set_offsets([point])
            return bool(result is not None and result.changed)
        if not self._generated_store().update_geometry(object_id, updates):
            return False
        self._sync_generated_object_property_controls(object_id)
        self._update_generated_line_preview(object_id)
        return True

    def _apply_generated_curve_handle_drag(self, object_id, handle_index, x_value, y_value):
        figure_object = self._generated_figure_object_by_id(object_id)
        if not figure_object or str(figure_object.get("type", "") or "") != "curve":
            return False
        key_pair = {
            0: ("x1", "y1"),
            1: ("x2", "y2"),
            2: ("control_x", "control_y"),
        }.get(int(handle_index))
        if key_pair is None:
            return False
        updates = {key_pair[0]: float(x_value), key_pair[1]: float(y_value)}
        drag_state = self._generated_drag_preview_mode(object_id)
        if drag_state is not None:
            original_object = drag_state.get("original_object")
            original_geometry = self._generated_persisted_geometry(
                original_object if isinstance(original_object, dict) else figure_object
            )
            preview_geometry = deepcopy(original_geometry)
            preview_geometry.update(updates)
            return self._update_generated_drag_preview(
                object_id,
                preview_geometry,
                object_type="curve",
            )
        session = self._edit_session_for_adapter()
        if session is None:
            return bool(self._generated_store().update_geometry(object_id, updates))
        session.select(object_id, "generated-canvas")
        result = self._execute_edit(UpdateGeometryCommand(object_id, updates))
        if result is None or not result.changed:
            return False
        self._sync_generated_object_property_controls(object_id)
        self._show_generated_figure_document()
        return True

    def _apply_generated_rectangle_handle_drag(
        self, object_id, handle_index, x_value, y_value, *, preview=False
    ):
        figure_object = self._generated_figure_object_by_id(object_id)
        if not figure_object or str(figure_object.get("type", "") or "") != "rectangle":
            return False
        bounds = (
            figure_object.get("bounds", {})
            if isinstance(figure_object.get("bounds"), dict)
            else figure_object
        )
        x = self._optional_float(bounds.get("x"))
        y = self._optional_float(bounds.get("y"))
        width = self._optional_float(bounds.get("width"))
        height = self._optional_float(bounds.get("height"))
        try:
            corner_index = int(handle_index)
            dragged_x = float(x_value)
            dragged_y = float(y_value)
        except (TypeError, ValueError):
            return False
        if None in {x, y, width, height} or corner_index not in {0, 1, 2, 3}:
            return False
        right = float(x) + float(width)
        top = float(y) + float(height)
        opposite_x, opposite_y = ((right, top), (float(x), top), (float(x), float(y)), (right, float(y)))[
            corner_index
        ]
        updates = {
            "x": min(dragged_x, opposite_x),
            "y": min(dragged_y, opposite_y),
            "width": abs(dragged_x - opposite_x),
            "height": abs(dragged_y - opposite_y),
        }
        drag_state = self._generated_drag_preview_mode(object_id)
        if drag_state is not None:
            original_object = drag_state.get("original_object")
            original_bounds = (
                original_object.get("bounds", {})
                if isinstance(original_object, dict)
                and isinstance(original_object.get("bounds"), dict)
                else original_object
            )
            preview_geometry = deepcopy(original_bounds or bounds)
            preview_geometry.update(updates)
            return self._update_generated_drag_preview(
                object_id,
                preview_geometry,
                object_type="rectangle",
            )
        if preview:
            preview_object = self._generated_figure_object_by_id(object_id)
            if not isinstance(preview_object, dict):
                return False
            preview_geometry = (
                preview_object.get("bounds", {})
                if isinstance(preview_object.get("bounds"), dict)
                else preview_object
            )
            if all(preview_geometry.get(key) == value for key, value in updates.items()):
                return False
            preview_geometry.update(updates)
            self._show_generated_figure_document()
            return True
        session = self._edit_session_for_adapter()
        if session is None:
            return bool(self._generated_store().update_geometry(object_id, updates))
        session.select(object_id, "generated-canvas")
        result = self._execute_edit(UpdateGeometryCommand(object_id, updates))
        if result is None or not result.changed:
            return False
        self._sync_generated_object_property_controls(object_id)
        self._show_generated_figure_document()
        return True

    def _apply_generated_line_body_drag(self, object_id, drag_state, x_value, y_value):
        figure_object = self._generated_figure_object_by_id(object_id)
        if not figure_object or str(figure_object.get("type", "") or "") != "line":
            return False
        press_data = drag_state.get("press_data")
        origin_geometry = drag_state.get("origin_geometry", {})
        if not isinstance(press_data, (list, tuple)) or len(press_data) < 2:
            return False
        start_x = self._optional_float(press_data[0])
        start_y = self._optional_float(press_data[1])
        origin_x1 = self._optional_float(origin_geometry.get("x1"))
        origin_y1 = self._optional_float(origin_geometry.get("y1"))
        origin_x2 = self._optional_float(origin_geometry.get("x2"))
        origin_y2 = self._optional_float(origin_geometry.get("y2"))
        if start_x is None or start_y is None or origin_x1 is None or origin_y1 is None:
            return False
        dx = round(float(x_value) - float(start_x), 12)
        dy = round(float(y_value) - float(start_y), 12)
        mode = str(drag_state.get("geometry_mode", "segment") or "segment")
        if mode == "vertical":
            updates = {"x1": round(float(origin_x1) + dx, 12)}
        elif mode == "horizontal":
            updates = {"y1": round(float(origin_y1) + dy, 12)}
        else:
            if origin_x2 is None or origin_y2 is None:
                return False
            updates = {
                "x1": round(float(origin_x1) + dx, 12),
                "y1": round(float(origin_y1) + dy, 12),
                "x2": round(float(origin_x2) + dx, 12),
                "y2": round(float(origin_y2) + dy, 12),
            }
        drag_state = self._generated_drag_preview_mode(object_id)
        if drag_state is not None:
            original_object = drag_state.get("original_object")
            original_geometry = self._generated_persisted_geometry(
                original_object if isinstance(original_object, dict) else figure_object
            )
            preview_geometry = deepcopy(original_geometry)
            preview_geometry.update(updates)
            return self._update_generated_drag_preview(
                object_id,
                preview_geometry,
                object_type="line",
            )
        session = self._edit_session_for_adapter()
        if session is not None:
            session.select(object_id, "generated-canvas")
            result = self._execute_edit(UpdateGeometryCommand(object_id, updates))
            if result is not None and result.changed:
                self._sync_generated_object_property_controls(object_id)
                self._update_generated_line_preview(object_id)
                axes = self._figure.axes[0] if self._figure and self._figure.axes else None
                if axes is not None:
                    point = [updates.get("x1"), updates.get("y1")]
                    if self._selected_generated_line_handle_index == 1:
                        point = [updates.get("x2"), updates.get("y2")]
                    for artist in axes.collections:
                        if artist.get_gid() == f"pn-current-handle:{object_id}":
                            artist.set_offsets([point])
            return bool(result is not None and result.changed)
        if not self._generated_store().update_geometry(object_id, updates):
            return False
        self._sync_generated_object_property_controls(object_id)
        self._update_generated_line_preview(object_id)
        return True

    def _apply_generated_body_drag(self, object_id, drag_state, x_value, y_value):
        figure_object = self._generated_figure_object_by_id(object_id)
        if not isinstance(figure_object, dict):
            return False
        press_data = drag_state.get("press_data")
        origin_geometry = drag_state.get("origin_geometry", {})
        if not isinstance(press_data, (list, tuple)) or len(press_data) < 2:
            return False
        if not isinstance(origin_geometry, dict):
            return False
        dx = round(float(x_value) - float(press_data[0]), 12)
        dy = round(float(y_value) - float(press_data[1]), 12)
        object_type = str(drag_state.get("object_type", "") or figure_object.get("type", ""))
        preview_geometry = deepcopy(origin_geometry)
        if object_type in {"text", "rectangle"}:
            preview_geometry["x"] = round(float(origin_geometry.get("x", 0.0)) + dx, 12)
            preview_geometry["y"] = round(float(origin_geometry.get("y", 0.0)) + dy, 12)
        elif object_type == "curve":
            for x_key, y_key in (("x1", "y1"), ("x2", "y2"), ("control_x", "control_y")):
                preview_geometry[x_key] = round(float(origin_geometry.get(x_key, 0.0)) + dx, 12)
                preview_geometry[y_key] = round(float(origin_geometry.get(y_key, 0.0)) + dy, 12)
        else:
            return False
        drag_state = self._generated_drag_preview_mode(object_id)
        if drag_state is not None:
            return self._update_generated_drag_preview(
                object_id,
                preview_geometry,
                object_type=object_type,
            )
        session = self._edit_session_for_adapter()
        if session is None:
            return bool(self._generated_store().update_geometry(object_id, preview_geometry))
        session.select(object_id, "generated-canvas")
        result = self._execute_edit(UpdateGeometryCommand(object_id, preview_geometry))
        return bool(result is not None and result.changed)

    def _apply_generated_plot_series_handle_drag(self, object_id, handle_index, x_value, y_value):
        figure_object = self._generated_figure_object_by_id(object_id)
        if not figure_object or str(figure_object.get("type", "") or "") != "plot_series":
            return False
        drag_state = self._generated_drag_preview_mode(object_id)
        if drag_state is not None:
            original_object = drag_state.get("original_object")
            source_object = (
                original_object if isinstance(original_object, dict) else figure_object
            )
            inline_data = source_object.get("data", {})
            if isinstance(inline_data, dict):
                x_values = list(inline_data.get("x", inline_data.get("x_values", [])) or [])
                y_values = list(inline_data.get("y", inline_data.get("y_values", [])) or [])
            else:
                x_values, y_values = self._generated_object_xy(
                    source_object,
                    self._load_generated_document_data_sources(),
                )
            point_index = int(handle_index or 0)
            if (
                not x_values
                or not y_values
                or point_index < 0
                or point_index >= min(len(x_values), len(y_values))
            ):
                return False
            x_values[point_index] = float(x_value)
            y_values[point_index] = float(y_value)
            return self._update_generated_drag_preview(
                object_id,
                {"x_values": x_values, "y_values": y_values},
                object_type="plot_series",
            )
        inline_data = self._materialize_generated_plot_series_inline_data(figure_object)
        if not isinstance(inline_data, dict):
            return False
        x_values = list(inline_data.get("x", []) or [])
        y_values = list(inline_data.get("y", []) or [])
        if not x_values or not y_values:
            return False
        point_index = int(handle_index or 0)
        if point_index < 0 or point_index >= min(len(x_values), len(y_values)):
            return False
        next_x = float(x_value)
        next_y = float(y_value)
        try:
            current_x = float(x_values[point_index])
            current_y = float(y_values[point_index])
        except (TypeError, ValueError):
            current_x = x_values[point_index]
            current_y = y_values[point_index]
        if current_x == next_x and current_y == next_y:
            return False
        x_values[point_index] = next_x
        y_values[point_index] = next_y
        inline_data["x"] = x_values
        inline_data["y"] = y_values
        self._sync_generated_object_property_controls(object_id)
        self._update_generated_plot_series_preview(object_id)
        return True

    def _generated_legend_artist(self):
        if self._figure is None or not self._figure.axes:
            return None
        return self._figure.axes[0].get_legend()

    def _generated_legend_window_extent(self, legend):
        if legend is None:
            return None
        renderer = None
        try:
            renderer = self._canvas.get_renderer()
        except Exception:
            renderer = None
        if renderer is None:
            try:
                self._canvas.draw()
                renderer = self._canvas.get_renderer()
            except Exception:
                return None
        try:
            return legend.get_window_extent(renderer)
        except Exception:
            return None

    def _window_extent_contains_with_slop(self, window_extent, event_x, event_y, slop_px=0.0):
        if window_extent is None:
            return False
        try:
            expanded_extent = window_extent.padded(float(slop_px or 0.0))
        except Exception:
            expanded_extent = window_extent
        try:
            return bool(expanded_extent.contains(float(event_x), float(event_y)))
        except Exception:
            return False

    def _generated_legend_drag_start(self, event, object_id):
        figure_object = self._generated_figure_object_by_id(object_id)
        legend = self._generated_legend_artist()
        axes = getattr(event, "inaxes", None)
        if axes is None and self._figure is not None and self._figure.axes:
            axes = self._figure.axes[0]
        if figure_object is None or legend is None or axes is None:
            return None
        window_extent = self._generated_legend_window_extent(legend)
        if window_extent is None:
            return None
        event_x = float(getattr(event, "x", 0.0) or 0.0)
        event_y = float(getattr(event, "y", 0.0) or 0.0)
        if not self._window_extent_contains_with_slop(
            window_extent,
            event_x,
            event_y,
            GENERATED_LEGEND_HIT_SLOP_PX,
        ):
            return None
        event_axes = self._generated_event_axes_fraction(event, axes)
        anchor_axes = self._generated_legend_anchor_for_drag(figure_object, legend, axes)
        if event_axes is None or anchor_axes is None:
            return None
        return {
            "object_id": str(object_id or ""),
            "kind": "legend",
            "dirty": False,
            "grab_offset_axes": (
                round(float(event_axes[0]) - float(anchor_axes[0]), 12),
                round(float(event_axes[1]) - float(anchor_axes[1]), 12),
            ),
        }

    def _generated_legend_anchor_for_drag(self, figure_object, legend, axes):
        style = figure_object.get("style", {}) if isinstance(figure_object.get("style"), dict) else {}
        bbox_to_anchor = style.get("bbox_to_anchor")
        loc = str(style.get("loc", "") or "")
        if loc == "upper left" and isinstance(bbox_to_anchor, (list, tuple)) and len(bbox_to_anchor) >= 2:
            x_value = self._optional_float(bbox_to_anchor[0])
            y_value = self._optional_float(bbox_to_anchor[1])
            if x_value is not None and y_value is not None:
                return round(float(x_value), 12), round(float(y_value), 12)
        window_extent = self._generated_legend_window_extent(legend)
        if window_extent is None:
            return None
        try:
            anchor_x, anchor_y = axes.transAxes.inverted().transform([float(window_extent.x0), float(window_extent.y1)])
        except Exception:
            return None
        try:
            return round(float(anchor_x), 12), round(float(anchor_y), 12)
        except (TypeError, ValueError):
            return None

    def _apply_generated_legend_drag(self, object_id, anchor_x, anchor_y):
        figure_object = self._generated_figure_object_by_id(object_id)
        if not figure_object or str(figure_object.get("type", "") or "") != "legend":
            return False
        next_anchor = [round(float(anchor_x), 12), round(float(anchor_y), 12)]
        drag_state = self._generated_drag_preview_mode(object_id)
        if drag_state is not None:
            original_object = drag_state.get("original_object")
            original_style = (
                original_object.get("style", {})
                if isinstance(original_object, dict)
                and isinstance(original_object.get("style"), dict)
                else {}
            )
            preview_geometry = {
                "bbox_to_anchor": next_anchor,
                "loc": "upper left",
                "original_style": deepcopy(original_style),
            }
            set_value = getattr(self, "_set_control_value_silently", None)
            if callable(set_value):
                x_spin = getattr(self, "_annotation_x_spin", None)
                y_spin = getattr(self, "_annotation_y_spin", None)
                if x_spin is not None:
                    set_value(x_spin, next_anchor[0])
                if y_spin is not None:
                    set_value(y_spin, next_anchor[1])
            return self._update_generated_drag_preview(
                object_id,
                preview_geometry,
                object_type="legend",
            )
        session = self._edit_session_for_adapter()
        if session is not None:
            session.select(object_id, "generated-canvas")
            result = self._execute_edit(
                UpdateStyleCommand(
                    object_id,
                    {"loc": "upper left", "bbox_to_anchor": next_anchor},
                )
            )
            if result is not None and result.changed:
                self._status_label.setText("Legend anchor updated.")
                self._update_generated_legend_preview(object_id)
                self._sync_generated_object_property_controls(object_id)
            return bool(result is not None and result.changed)
        changed = self._generated_store().update_style(
            object_id,
            {
                "loc": "upper left",
                "bbox_to_anchor": next_anchor,
            },
        )
        if not changed:
            return False
        self._sync_generated_object_property_controls(object_id)
        self._update_generated_legend_preview(object_id)
        return True

    def _materialize_generated_plot_series_inline_data(self, figure_object):
        if not figure_object or str(figure_object.get("type", "") or "") != "plot_series":
            return None
        object_id = str(figure_object.get("id", "") or "")
        inline_data = figure_object.get("data", {})
        if isinstance(inline_data, dict):
            x_values = inline_data.get("x", inline_data.get("x_values", []))
            y_values = inline_data.get("y", inline_data.get("y_values", []))
            if x_values and y_values:
                self._generated_store().set_plot_series_inline_data(
                    object_id,
                    list(x_values),
                    list(y_values),
                )
                updated_object = self._generated_figure_object_by_id(object_id)
                if isinstance(updated_object, dict):
                    updated_inline_data = updated_object.get("data", {})
                    if isinstance(updated_inline_data, dict):
                        return updated_inline_data
        data_sources = self._load_generated_document_data_sources()
        x_values, y_values = self._generated_object_xy(figure_object, data_sources)
        if not x_values or not y_values:
            return None
        self._generated_store().set_plot_series_inline_data(
            object_id,
            list(x_values),
            list(y_values),
        )
        updated_object = self._generated_figure_object_by_id(object_id)
        if isinstance(updated_object, dict):
            updated_inline_data = updated_object.get("data", {})
            if isinstance(updated_inline_data, dict):
                return updated_inline_data
        return None

    def _update_generated_line_preview(self, object_id):
        figure_object = self._generated_figure_object_by_id(object_id)
        if not figure_object or self._figure is None or not self._figure.axes:
            return
        axes = self._figure.axes[0]
        line_artist = self._generated_line_artist(object_id)
        if line_artist is None:
            return
        x1 = self._optional_float(figure_object.get("x1"))
        y1 = self._optional_float(figure_object.get("y1"))
        x2 = self._optional_float(figure_object.get("x2"))
        y2 = self._optional_float(figure_object.get("y2"))
        if x1 is None or y1 is None:
            return
        if x2 is None:
            line_artist.set_xdata([x1, x1])
        elif y2 is None:
            line_artist.set_ydata([y1, y1])
        else:
            line_artist.set_xdata([x1, float(x2)])
            line_artist.set_ydata([y1, float(y2)])
        handle_artist = self._generated_selection_handle_artist(object_id)
        if isinstance(handle_artist, PathCollection):
            offsets = [[x1, y1]]
            if x2 is not None and y2 is not None:
                offsets.append([float(x2), float(y2)])
            handle_artist.set_offsets(offsets)
        current_handle_artist = self._generated_current_handle_artist(object_id)
        handle_index = self._selected_generated_line_handle_index_for_object(figure_object)
        if handle_index is not None and x2 is not None and y2 is not None:
            if current_handle_artist is None:
                current_handle_artist = axes.scatter(
                    [x1 if handle_index <= 0 else float(x2)],
                    [y1 if handle_index <= 0 else float(y2)],
                    s=92,
                    facecolors="none",
                    edgecolors="#D55E00",
                    linewidths=2.2,
                    zorder=10_001,
                )
                current_handle_artist.set_gid(f"pn-current-handle:{object_id}")
            current_handle_artist.set_offsets(
                [[x1, y1]] if handle_index <= 0 else [[float(x2), float(y2)]]
            )
        elif isinstance(current_handle_artist, PathCollection):
            current_handle_artist.set_offsets([])
        self._canvas.draw_idle()

    def _update_generated_plot_series_preview(self, object_id):
        figure_object = self._generated_figure_object_by_id(object_id)
        if not figure_object or self._figure is None or not self._figure.axes:
            return
        x_values, y_values = self._generated_object_xy(figure_object, {})
        if not x_values or not y_values:
            return
        axes = self._figure.axes[0]
        for artist in axes.lines:
            if self._figure_render_adapter.object_id_for_artist(artist) == object_id:
                artist.set_xdata(x_values)
                artist.set_ydata(y_values)
                break
        for artist in axes.collections:
            if self._figure_render_adapter.object_id_for_artist(artist) == object_id:
                artist.set_offsets(list(zip(x_values, y_values)))
                break
        handle_artist = self._generated_selection_handle_artist(object_id)
        if isinstance(handle_artist, PathCollection):
            chart_kind = str(figure_object.get("chart_kind", "") or "")
            style = (
                figure_object.get("style", {})
                if isinstance(figure_object.get("style"), dict)
                else {}
            )
            marker_value = str(style.get("marker", "") or "")
            handle_offsets = list(zip(x_values, y_values))
            if not marker_value and chart_kind != "scatter":
                point_index = self._selected_generated_plot_series_point_index(
                    figure_object
                )
                if point_index is None or point_index >= min(len(x_values), len(y_values)):
                    handle_offsets = []
                else:
                    handle_offsets = [
                        [float(x_values[point_index]), float(y_values[point_index])]
                    ]
            handle_artist.set_offsets(handle_offsets)
        current_handle_artist = self._generated_current_handle_artist(object_id)
        point_index = self._selected_generated_plot_series_point_index(figure_object)
        if point_index is not None and point_index < min(len(x_values), len(y_values)):
            chart_kind = str(figure_object.get("chart_kind", "") or "")
            style = (
                figure_object.get("style", {})
                if isinstance(figure_object.get("style"), dict)
                else {}
            )
            marker_value = str(style.get("marker", "") or "")
            if current_handle_artist is None and (
                chart_kind == "scatter" or marker_value
            ):
                current_handle_artist = axes.scatter(
                    [float(x_values[point_index])],
                    [float(y_values[point_index])],
                    s=92,
                    facecolors="none",
                    edgecolors="#D55E00",
                    linewidths=2.2,
                    zorder=10_001,
                )
                current_handle_artist.set_gid(f"pn-current-handle:{object_id}")
        if isinstance(current_handle_artist, PathCollection):
            if point_index is None or point_index >= min(len(x_values), len(y_values)):
                current_handle_artist.set_offsets([])
            else:
                current_handle_artist.set_offsets(
                    [[float(x_values[point_index]), float(y_values[point_index])]]
                )
        self._canvas.draw_idle()

    def _update_generated_legend_preview(self, object_id):
        figure_object = self._generated_figure_object_by_id(object_id)
        legend = self._generated_legend_artist()
        if (
            not figure_object
            or str(figure_object.get("type", "") or "") != "legend"
            or legend is None
            or self._figure is None
            or not self._figure.axes
        ):
            return
        style = figure_object.get("style", {}) if isinstance(figure_object.get("style"), dict) else {}
        bbox_to_anchor = style.get("bbox_to_anchor")
        if not isinstance(bbox_to_anchor, (list, tuple)) or len(bbox_to_anchor) < 2:
            return
        anchor_x = self._optional_float(bbox_to_anchor[0])
        anchor_y = self._optional_float(bbox_to_anchor[1])
        if anchor_x is None or anchor_y is None:
            return
        axes = self._figure.axes[0]
        legend.set_loc(str(style.get("loc", "") or "upper left"))
        legend.set_bbox_to_anchor((float(anchor_x), float(anchor_y)), transform=axes.transAxes)
        self._canvas.draw_idle()

    def _is_left_mouse_button(self, button):
        if button is None:
            return False
        if button == 1:
            return True
        name = str(getattr(button, "name", "") or "").lower()
        return name == "left"

    def _ensure_generated_legend_object(self):
        if not isinstance(self._figure_document, dict):
            return
        FigureObjectStore(self._figure_document).ensure_legend_object()

    def _generated_legend_visible(self):
        legend = self._generated_figure_object_by_id("legend")
        if legend is None:
            return True
        return legend.get("visible", True) is not False

    def _generated_figure_object_by_id(self, object_id):
        return self._generated_store().get(object_id)

    def _generated_figure_object_by_id_including_deleted(self, object_id):
        return self._generated_store().get_including_deleted(object_id)

    def _clear_selected_generated_plot_series_handle_context(self):
        self._selected_generated_plot_series_object_id = ""
        self._selected_generated_plot_series_handle_index = None

    def _clear_selected_generated_line_handle_context(self):
        self._selected_generated_line_object_id = ""
        self._selected_generated_line_handle_index = None

    def _reset_generated_handle_memory(self):
        self._generated_last_line_handle_indices.clear()
        self._generated_last_plot_series_handle_indices.clear()

    def _set_selected_generated_line_handle_context(self, object_id, handle_index):
        object_id = str(object_id or "")
        if not object_id:
            self._clear_selected_generated_line_handle_context()
            return
        try:
            index_value = int(handle_index)
        except (TypeError, ValueError):
            self._clear_selected_generated_line_handle_context()
            return
        self._selected_generated_line_object_id = object_id
        self._selected_generated_line_handle_index = index_value
        self._generated_last_line_handle_indices[object_id] = index_value

    def _selected_generated_line_handle_index_for_object(self, figure_object):
        if not isinstance(figure_object, dict):
            return None
        object_id = str(figure_object.get("id", "") or "")
        if (
            str(self._selected_generated_line_object_id or "") != object_id
            or self._selected_generated_line_handle_index is None
        ):
            return None
        handle_index = int(self._selected_generated_line_handle_index)
        if handle_index not in {0, 1}:
            return None
        return handle_index

    def _set_selected_generated_plot_series_handle_context(self, object_id, handle_index):
        object_id = str(object_id or "")
        if not object_id:
            self._clear_selected_generated_plot_series_handle_context()
            return
        try:
            index_value = int(handle_index)
        except (TypeError, ValueError):
            self._clear_selected_generated_plot_series_handle_context()
            return
        self._selected_generated_plot_series_object_id = object_id
        self._selected_generated_plot_series_handle_index = index_value
        self._generated_last_plot_series_handle_indices[object_id] = index_value

    def _selected_generated_plot_series_point_index(self, figure_object):
        if not isinstance(figure_object, dict):
            return None
        object_id = str(figure_object.get("id", "") or "")
        if (
            str(self._selected_generated_plot_series_object_id or "") != object_id
            or self._selected_generated_plot_series_handle_index is None
        ):
            return None
        point_index = int(self._selected_generated_plot_series_handle_index)
        inline_data = self._materialize_generated_plot_series_inline_data(figure_object)
        if not isinstance(inline_data, dict):
            return None
        x_values = list(inline_data.get("x", []) or [])
        y_values = list(inline_data.get("y", []) or [])
        if point_index < 0 or point_index >= min(len(x_values), len(y_values)):
            return None
        return point_index
