from __future__ import annotations

from copy import deepcopy

from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, PathPatch, Rectangle
from matplotlib.path import Path
from matplotlib.text import Text

from ...core.figure_text_geometry import text_box_anchor
from .editor_geometry import Box

class ChartEditorGeneratedPreviewMixin:
    """Own editor-only artists used while a generated gesture is in progress."""

    def _generated_preview_state(self) -> list[object]:
        artists = getattr(self, "_generated_draw_preview_artists", None)
        if not isinstance(artists, list):
            artists = []
            self._generated_draw_preview_artists = artists
        return artists

    def _generated_preview_axis(self):
        figure = getattr(self, "_figure", None)
        axes = getattr(figure, "axes", ()) if figure is not None else ()
        return axes[0] if axes else None

    def _capture_generated_viewport(self):
        figure = getattr(self, "_figure", None)
        if figure is None:
            return None
        axes = list(getattr(figure, "axes", ()) or ())
        snapshot = {
            "figure": figure,
            "figure_size": tuple(float(value) for value in figure.get_size_inches()),
            "axes": [
                {
                    "xlim": tuple(float(value) for value in axis.get_xlim()),
                    "ylim": tuple(float(value) for value in axis.get_ylim()),
                    "xscale": str(axis.get_xscale() or "linear"),
                    "yscale": str(axis.get_yscale() or "linear"),
                }
                for axis in axes
            ],
            "selected_object_id": str(
                getattr(self, "_selected_figure_object_id", "") or ""
            ),
        }
        self._generated_viewport_snapshot = snapshot
        return snapshot

    def _restore_generated_viewport(self, snapshot=None):
        snapshot = snapshot or getattr(self, "_generated_viewport_snapshot", None)
        if not isinstance(snapshot, dict):
            return False
        figure = getattr(self, "_figure", None)
        if figure is None:
            return False
        size = snapshot.get("figure_size")
        if isinstance(size, (list, tuple)) and len(size) >= 2:
            try:
                figure.set_size_inches(float(size[0]), float(size[1]), forward=False)
            except (TypeError, ValueError):
                pass
        restored = False
        for axis, axis_snapshot in zip(
            list(getattr(figure, "axes", ()) or ()),
            snapshot.get("axes", ()),
        ):
            if not isinstance(axis_snapshot, dict):
                continue
            try:
                axis.set_xscale(str(axis_snapshot.get("xscale", "linear") or "linear"))
                axis.set_yscale(str(axis_snapshot.get("yscale", "linear") or "linear"))
                axis.set_xlim(axis_snapshot["xlim"])
                axis.set_ylim(axis_snapshot["ylim"])
            except (KeyError, TypeError, ValueError, RuntimeError):
                continue
            restored = True
        return restored

    def _clear_generated_preview_artists(self, *, redraw: bool = True) -> bool:
        artists = self._generated_preview_state()
        had_artists = bool(artists)
        for artist in artists:
            try:
                artist.remove()
            except (AttributeError, ValueError, RuntimeError):
                continue
        artists.clear()
        if redraw:
            canvas = getattr(self, "_canvas", None)
            if canvas is not None:
                canvas.draw_idle()
        return had_artists

    def _clear_generated_draw_preview(self, *, redraw: bool = True) -> bool:
        return self._clear_generated_preview_artists(redraw=redraw)

    def _begin_generated_draw_preview(self, start_data, start_display=None):
        self._clear_generated_draw_preview(redraw=False)
        self._generated_draw_preview_start = tuple(start_data)
        self._generated_draw_preview_start_display = start_display
        self._capture_generated_viewport()

    def _preview_style(self, figure_object=None):
        style = {}
        if isinstance(figure_object, dict) and isinstance(figure_object.get("style"), dict):
            style.update(figure_object["style"])
        active_style = getattr(self, "_active_draw_style", None)
        if callable(active_style):
            style = {**style, **active_style()}
        return {
            "color": style.get("color", "#D55E00"),
            "linewidth": float(style.get("line_width", 2.0) or 2.0),
            "alpha": min(1.0, max(0.25, float(style.get("alpha", 0.85) or 0.85))),
        }

    @staticmethod
    def _preview_points(start_data, end_data):
        x1, y1 = (float(start_data[0]), float(start_data[1]))
        x2, y2 = (float(end_data[0]), float(end_data[1]))
        return x1, y1, x2, y2

    @staticmethod
    def _generated_curve_control_point(start_data, end_data):
        x1, y1 = (float(start_data[0]), float(start_data[1]))
        x2, y2 = (float(end_data[0]), float(end_data[1]))
        dx = x2 - x1
        dy = y2 - y1
        length = (dx * dx + dy * dy) ** 0.5
        if length <= 1e-9:
            return x1, y1
        bend = max(0.12, min(0.35, length * 0.35))
        normal_x = -dy / length
        normal_y = dx / length
        if normal_y < 0.0:
            normal_x *= -1.0
            normal_y *= -1.0
        return (x1 + x2) / 2.0 + normal_x * bend, (y1 + y2) / 2.0 + normal_y * bend

    @staticmethod
    def _generated_persisted_geometry(figure_object):
        if not isinstance(figure_object, dict):
            return {}
        for key in ("geometry", "bounds"):
            value = figure_object.get(key)
            if isinstance(value, dict):
                return deepcopy(value)
        return {
            key: deepcopy(figure_object[key])
            for key in (
                "x",
                "y",
                "width",
                "height",
                "x1",
                "y1",
                "x2",
                "y2",
                "control_x",
                "control_y",
            )
            if key in figure_object
        }

    def _make_generated_draw_preview_artist(self, tool, start_data, end_data):
        axis = self._generated_preview_axis()
        if axis is None:
            return None
        x1, y1, x2, y2 = self._preview_points(start_data, end_data)
        style = self._preview_style()
        common = {
            "color": style["color"],
            "linewidth": style["linewidth"],
            "alpha": style["alpha"],
            "linestyle": "--",
            "zorder": 20_000,
        }
        if tool == "line":
            artist = Line2D([x1, x2], [y1, y2], **common)
            axis.add_line(artist)
        elif tool == "arrow":
            artist = FancyArrowPatch(
                (x1, y1),
                (x2, y2),
                arrowstyle="->",
                mutation_scale=12,
                **common,
            )
            axis.add_patch(artist)
        elif tool == "curve":
            control_x, control_y = self._generated_curve_control_point(start_data, end_data)
            artist = PathPatch(
                Path(
                    [(x1, y1), (control_x, control_y), (x2, y2)],
                    [Path.MOVETO, Path.CURVE3, Path.CURVE3],
                ),
                fill=False,
                edgecolor=style["color"],
                linewidth=style["linewidth"],
                alpha=style["alpha"],
                linestyle="--",
                zorder=20_000,
            )
            axis.add_patch(artist)
        elif tool in {"rectangle", "text"}:
            artist = Rectangle(
                (min(x1, x2), min(y1, y2)),
                abs(x2 - x1),
                abs(y2 - y1),
                fill=False,
                edgecolor=style["color"],
                linewidth=style["linewidth"],
                alpha=style["alpha"],
                linestyle="--",
                zorder=20_000,
            )
            axis.add_patch(artist)
        else:
            return None
        artist.set_gid(f"pn-preview:{tool}")
        return artist

    def _update_generated_draw_preview(self, tool, start_data, end_data):
        self._clear_generated_draw_preview(redraw=False)
        artist = self._make_generated_draw_preview_artist(tool, start_data, end_data)
        if artist is not None:
            self._generated_preview_state().append(artist)
        canvas = getattr(self, "_canvas", None)
        if canvas is not None:
            canvas.draw_idle()
        return artist is not None

    def _generated_drag_preview_mode(self, object_id=""):
        drag_state = getattr(self, "_generated_handle_drag_state", None)
        return (
            drag_state
            if isinstance(drag_state, dict)
            and (
                not object_id
                or str(drag_state.get("object_id", "") or "") == str(object_id or "")
            )
            else None
        )

    def _update_generated_drag_preview(self, object_id, geometry, *, object_type=""):
        """Update existing artists without touching the document or history."""

        state = self._generated_drag_preview_mode(object_id)
        if state is None or not isinstance(geometry, dict):
            return False
        figure_object = self._generated_figure_object_by_id(object_id)
        if not isinstance(figure_object, dict):
            return False
        object_type = object_type or str(figure_object.get("type", "") or "")
        state["preview_geometry"] = deepcopy(geometry)
        artists = list(self._figure_render_adapter.artists_for_object_id(object_id))
        if object_type in {"line", "line-body"}:
            x1 = geometry.get("x1")
            y1 = geometry.get("y1")
            x2 = geometry.get("x2")
            y2 = geometry.get("y2")
            for artist in artists:
                if not isinstance(artist, Line2D) or x1 is None or y1 is None:
                    continue
                if x2 is None:
                    artist.set_data([x1, x1], [y1, y1])
                elif y2 is None:
                    artist.set_data([x1, x2], [y1, y1])
                else:
                    artist.set_data([x1, x2], [y1, y2])
        elif object_type == "curve":
            x1 = geometry.get("x1")
            y1 = geometry.get("y1")
            x2 = geometry.get("x2")
            y2 = geometry.get("y2")
            if None not in {x1, y1, x2, y2}:
                control_x = geometry.get("control_x", (float(x1) + float(x2)) / 2.0)
                control_y = geometry.get("control_y", (float(y1) + float(y2)) / 2.0)
                path = Path(
                    [(x1, y1), (control_x, control_y), (x2, y2)],
                    [Path.MOVETO, Path.CURVE3, Path.CURVE3],
                )
                for artist in artists:
                    if isinstance(artist, PathPatch):
                        artist.set_path(path)
        elif object_type == "text":
            x_value = geometry.get("x")
            y_value = geometry.get("y")
            if x_value is not None and y_value is not None:
                width = geometry.get("width", figure_object.get("width", 0.0))
                height = geometry.get("height", figure_object.get("height", 0.0))
                anchor = text_box_anchor(
                    float(x_value),
                    float(y_value),
                    float(width or 0.0),
                    float(height or 0.0),
                    horizontal_alignment=figure_object.get("horizontal_alignment"),
                    vertical_alignment=figure_object.get("vertical_alignment"),
                )
                for artist in artists:
                    if isinstance(artist, Text):
                        artist.set_position(anchor)
        elif object_type == "rectangle":
            bounds = geometry
            if isinstance(figure_object.get("bounds"), dict):
                bounds = geometry.get("bounds", geometry)
            x = bounds.get("x")
            y = bounds.get("y")
            width = bounds.get("width")
            height = bounds.get("height")
            if None not in {x, y, width, height}:
                for artist in artists:
                    if isinstance(artist, Rectangle):
                        artist.set_xy((float(x), float(y)))
                        artist.set_width(float(width))
                        artist.set_height(float(height))
        elif object_type == "plot_series":
            x_values = geometry.get("x_values", ())
            y_values = geometry.get("y_values", ())
            for artist in artists:
                if isinstance(artist, Line2D):
                    artist.set_data(x_values, y_values)
                elif hasattr(artist, "set_offsets"):
                    artist.set_offsets(list(zip(x_values, y_values)))
        elif object_type == "legend":
            anchor = geometry.get("bbox_to_anchor")
            axes = self._generated_preview_axis()
            legend = self._generated_legend_artist()
            if (
                legend is not None
                and axes is not None
                and isinstance(anchor, (list, tuple))
                and len(anchor) >= 2
            ):
                legend.set_loc("upper left")
                legend.set_bbox_to_anchor(
                    (float(anchor[0]), float(anchor[1])),
                    transform=axes.transAxes,
                )
        self._update_generated_drag_handle_artists(object_id, geometry, object_type)
        self._update_generated_selection_frame(object_id, geometry, object_type)
        self._sync_generated_drag_preview_controls(geometry, object_type)
        state["preview_artists"] = artists
        self._generated_handle_preview_artists = artists
        canvas = getattr(self, "_canvas", None)
        if canvas is not None:
            canvas.draw_idle()
        return True

    def _update_generated_selection_frame(self, object_id, geometry, object_type):
        if object_type not in {"text", "rectangle"}:
            return
        box = Box.from_payload(geometry)
        if box is None:
            return
        expected_gid = f"pn-selection-frame:{object_id}"
        figure = getattr(self, "_figure", None)
        for axis in list(getattr(figure, "axes", ()) or ()):
            for artist in axis.patches:
                if str(getattr(artist, "get_gid", lambda: "")() or "") != expected_gid:
                    continue
                if isinstance(artist, Rectangle):
                    artist.set_xy((box.x, box.y))
                    artist.set_width(box.width)
                    artist.set_height(box.height)

    def _sync_generated_drag_preview_controls(self, geometry, object_type):
        set_value = getattr(self, "_set_control_value_silently", None)
        if not callable(set_value):
            return
        values = {}
        if object_type in {"line", "line-body"}:
            values = {
                "_annotation_x_spin": geometry.get("x1"),
                "_annotation_y_spin": geometry.get("y1"),
                "_annotation_w_spin": geometry.get("x2"),
                "_annotation_h_spin": geometry.get("y2"),
            }
        elif object_type == "curve":
            values = {
                "_annotation_x_spin": geometry.get("x1"),
                "_annotation_y_spin": geometry.get("y1"),
                "_annotation_w_spin": geometry.get("x2"),
                "_annotation_h_spin": geometry.get("y2"),
                "_annotation_curve_control_x_spin": geometry.get("control_x"),
                "_annotation_curve_control_y_spin": geometry.get("control_y"),
            }
        elif object_type == "rectangle":
            values = {
                "_annotation_x_spin": geometry.get("x"),
                "_annotation_y_spin": geometry.get("y"),
                "_annotation_w_spin": geometry.get("width"),
                "_annotation_h_spin": geometry.get("height"),
            }
        elif object_type == "plot_series":
            state = self._generated_drag_preview_mode()
            index = int((state or {}).get("handle_index", 0) or 0)
            x_values = list(geometry.get("x_values", ()) or ())
            y_values = list(geometry.get("y_values", ()) or ())
            if 0 <= index < min(len(x_values), len(y_values)):
                values = {
                    "_annotation_x_spin": x_values[index],
                    "_annotation_y_spin": y_values[index],
                }
        for attribute, value in values.items():
            control = getattr(self, attribute, None)
            if control is not None and value is not None:
                set_value(control, value)

    def _update_generated_drag_handle_artists(self, object_id, geometry, object_type):
        if object_type == "line":
            points = []
            if geometry.get("x1") is not None and geometry.get("y1") is not None:
                points.append((geometry["x1"], geometry["y1"]))
            if geometry.get("x2") is not None and geometry.get("y2") is not None:
                points.append((geometry["x2"], geometry["y2"]))
        elif object_type == "curve":
            x1, y1 = geometry.get("x1"), geometry.get("y1")
            x2, y2 = geometry.get("x2"), geometry.get("y2")
            if None in {x1, y1, x2, y2}:
                return
            points = [
                (x1, y1),
                (x2, y2),
                (
                    geometry.get("control_x", (float(x1) + float(x2)) / 2.0),
                    geometry.get("control_y", (float(y1) + float(y2)) / 2.0),
                ),
            ]
        elif object_type in {"rectangle", "text"}:
            box = Box.from_payload(geometry)
            if box is None:
                return
            right = box.x + box.width
            top = box.y + box.height
            points = [(box.x, box.y), (right, box.y), (right, top), (box.x, top)]
        elif object_type == "plot_series":
            x_values = list(geometry.get("x_values", ()) or ())
            y_values = list(geometry.get("y_values", ()) or ())
            points = list(zip(x_values, y_values))
            if not points:
                return
        else:
            return
        selected_index = int(
            (getattr(self, "_generated_handle_drag_state", {}) or {}).get(
                "handle_index", 0
            )
            or 0
        )
        figure = getattr(self, "_figure", None)
        for axis in list(getattr(figure, "axes", ()) or ()):
            for artist in axis.collections:
                gid = str(getattr(artist, "get_gid", lambda: "")() or "")
                if gid == f"pn-selection-handles:{object_id}":
                    indices = getattr(artist, "_pn_handle_indices", list(range(len(points))))
                    artist.set_offsets(
                        [points[index] for index in indices if 0 <= index < len(points)]
                    )
                elif gid == f"pn-current-handle:{object_id}" and 0 <= selected_index < len(points):
                    artist.set_offsets([points[selected_index]])

    def _clear_generated_drag_preview(self, *, redraw: bool = False):
        self._generated_handle_preview_artists = []
        state = getattr(self, "_generated_handle_drag_state", None)
        if isinstance(state, dict):
            state.pop("preview_geometry", None)
            state.pop("preview_artists", None)
        if redraw:
            canvas = getattr(self, "_canvas", None)
            if canvas is not None:
                canvas.draw_idle()
