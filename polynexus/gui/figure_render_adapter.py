"""Generated figure rendering plus artist/object mapping."""

from __future__ import annotations

import math
from copy import deepcopy
from types import SimpleNamespace

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle


class FigureRenderAdapter:
    _PICK_RADIUS = 10.0

    def __init__(self):
        self._artist_to_object_id: dict[int, str] = {}
        self._artist_to_render_order: dict[int, int] = {}
        self._object_id_to_artists: dict[str, list[object]] = {}
        self._registered_artists: list[object] = []
        self._hover_highlight_snapshots: list[tuple[object, dict]] = []

    def reset_artist_map(self) -> None:
        self._artist_to_object_id = {}
        self._artist_to_render_order = {}
        self._object_id_to_artists = {}
        self._registered_artists = []
        self._hover_highlight_snapshots = []

    def register_artists(self, object_id: str, artists, render_order: int = 0) -> list[object]:
        object_id = str(object_id or "")
        normalized: list[object] = []
        if not isinstance(artists, (list, tuple)):
            artists = [artists]
        for artist in artists:
            if artist is None:
                continue
            normalized.append(artist)
            self._register_artist_mapping(object_id, artist, render_order)
        return normalized

    def highlight_selection(self, artists) -> None:
        if not isinstance(artists, (list, tuple)):
            artists = [artists]
        self._highlight_selected([artist for artist in artists if artist is not None])

    def highlight_hover(self, artists) -> None:
        self.clear_hover_highlight()
        if not isinstance(artists, (list, tuple)):
            artists = [artists]
        artists = [artist for artist in artists if artist is not None]
        if not artists:
            return
        self._hover_highlight_snapshots = [
            (artist, self._snapshot_artist_state(artist))
            for artist in artists
        ]
        self._highlight_hover_artists(artists)

    def clear_hover_highlight(self) -> bool:
        if not self._hover_highlight_snapshots:
            return False
        for artist, state in self._hover_highlight_snapshots:
            self._restore_artist_state(artist, state)
        self._hover_highlight_snapshots = []
        return True

    def artists_for_object_id(self, object_id: str) -> list[object]:
        return list(self._object_id_to_artists.get(str(object_id or ""), []))

    def add_selection_handles(self, ax, figure_object: dict, *, selected_handle_index=None):
        if not isinstance(figure_object, dict):
            return []
        object_id = str(figure_object.get("id", "") or "")
        if not object_id:
            return []
        object_type = str(figure_object.get("type", "") or "")
        chart_kind = str(figure_object.get("chart_kind", "") or "")
        style = figure_object.get("style", {}) if isinstance(figure_object.get("style"), dict) else {}

        handle_points: list[tuple[float, float]] = []
        handle_indices: list[int] = []
        if object_type in {"line", "arrow", "curve"}:
            x1 = self._optional_float(figure_object.get("x1"))
            y1 = self._optional_float(figure_object.get("y1"))
            x2 = self._optional_float(figure_object.get("x2"))
            y2 = self._optional_float(figure_object.get("y2"))
            if x1 is not None and y1 is not None:
                handle_points.append((x1, y1))
                handle_indices.append(0)
            if x2 is not None and y2 is not None:
                handle_points.append((x2, y2))
                handle_indices.append(1)
            if object_type == "curve":
                control_x = self._optional_float(figure_object.get("control_x"))
                control_y = self._optional_float(figure_object.get("control_y"))
                if control_x is not None and control_y is not None:
                    handle_points.append((control_x, control_y))
                    handle_indices.append(2)
        elif object_type == "rectangle":
            bounds = (
                figure_object.get("bounds", {})
                if isinstance(figure_object.get("bounds"), dict)
                else figure_object
            )
            x = self._optional_float(bounds.get("x"))
            y = self._optional_float(bounds.get("y"))
            width = self._optional_float(bounds.get("width"))
            height = self._optional_float(bounds.get("height"))
            if None not in {x, y, width, height}:
                right = float(x) + float(width)
                top = float(y) + float(height)
                handle_points.extend(
                    [
                        (float(x), float(y)),
                        (right, float(y)),
                        (right, top),
                        (float(x), top),
                    ]
                )
                handle_indices.extend([0, 1, 2, 3])
        elif object_type == "plot_series" and chart_kind not in {"heatmap", "bar", "barh", "image_grid"}:
            plot_series_points = self._plot_series_indexed_handle_points(figure_object)
            marker = str(style.get("marker", "") or "")
            if marker or chart_kind == "scatter":
                for point_index, x_coord, y_coord in plot_series_points:
                    handle_points.append((x_coord, y_coord))
                    handle_indices.append(int(point_index))
            elif selected_handle_index is not None:
                try:
                    point_index = int(selected_handle_index)
                except (TypeError, ValueError):
                    point_index = -1
                for handle_index, x_coord, y_coord in plot_series_points:
                    if int(handle_index) != point_index:
                        continue
                    handle_points.append((x_coord, y_coord))
                    handle_indices.append(int(handle_index))
                    break

        if not handle_points:
            return []

        xs, ys = zip(*handle_points)
        handles = ax.scatter(
            xs,
            ys,
            s=64,
            facecolors="#FFFFFF",
            edgecolors="#D55E00",
            linewidths=2.0,
            zorder=10_000,
        )
        handles.set_gid(f"pn-selection-handles:{object_id}")
        setattr(handles, "_pn_handle_indices", list(handle_indices))
        overlay_artists = [handles]
        if (
            object_type in {"line", "curve", "plot_series"}
            and selected_handle_index is not None
            and len(handle_points) > 1
        ):
            try:
                current_handle_index = handle_indices.index(int(selected_handle_index))
            except (TypeError, ValueError):
                current_handle_index = -1
            if 0 <= current_handle_index < len(handle_points):
                current_handle = ax.scatter(
                    [handle_points[current_handle_index][0]],
                    [handle_points[current_handle_index][1]],
                    s=92,
                    facecolors="none",
                    edgecolors="#D55E00",
                    linewidths=2.2,
                    zorder=10_001,
                )
                current_handle.set_gid(f"pn-current-handle:{object_id}")
                overlay_artists.append(current_handle)
        return overlay_artists

    def add_selection_frame(self, ax, figure_object: dict) -> list[object]:
        """Add a transient visual frame around an editable figure object."""
        if not isinstance(figure_object, dict):
            return []
        object_id = str(figure_object.get("id", "") or "")
        if not object_id:
            return []

        object_type = str(figure_object.get("type", "") or "")
        frame_kwargs = {
            "color": "#0072B2",
            "linestyle": "--",
            "linewidth": 1.5,
            "zorder": 10_000,
        }

        def finite_optional_float(value):
            parsed = self._optional_float(value)
            return parsed if parsed is not None and math.isfinite(parsed) else None

        if object_type in {"line", "arrow", "curve"}:
            geometry_keys = ("x1", "y1", "x2", "y2")
            if object_type == "curve":
                geometry_keys += ("control_x", "control_y")
            values = [finite_optional_float(figure_object.get(key)) for key in geometry_keys]
            if any(value is None for value in values):
                return []
            points = list(zip(values[::2], values[1::2]))
            xs = [float(point[0]) for point in points]
            ys = [float(point[1]) for point in points]
            left, right = min(xs), max(xs)
            bottom, top = min(ys), max(ys)
            frame = Line2D(
                [left, right, right, left, left],
                [bottom, bottom, top, top, bottom],
                **frame_kwargs,
            )
            ax.add_line(frame)
        elif object_type in {"text", "plot_series"}:
            frame = self._artist_selection_frame(ax, object_id, figure_object, frame_kwargs)
            if frame is None:
                return []
            ax.add_patch(frame)
        elif object_type == "rectangle":
            bounds = (
                figure_object.get("bounds", {})
                if isinstance(figure_object.get("bounds"), dict)
                else figure_object
            )
            x = finite_optional_float(bounds.get("x"))
            y = finite_optional_float(bounds.get("y"))
            width = finite_optional_float(bounds.get("width"))
            height = finite_optional_float(bounds.get("height"))
            if None in {x, y, width, height}:
                return []
            frame = Rectangle(
                (float(x), float(y)),
                float(width),
                float(height),
                fill=False,
                edgecolor=frame_kwargs["color"],
                linestyle=frame_kwargs["linestyle"],
                linewidth=frame_kwargs["linewidth"],
                zorder=frame_kwargs["zorder"],
            )
            ax.add_patch(frame)
        else:
            return []

        frame.set_gid(f"pn-selection-frame:{object_id}")
        return [frame]

    def _artist_selection_frame(self, ax, object_id: str, figure_object: dict, frame_kwargs: dict):
        for artist in self.artists_for_object_id(object_id):
            if not hasattr(artist, "get_window_extent"):
                continue
            figure = getattr(artist, "figure", None) or getattr(ax, "figure", None)
            canvas = getattr(figure, "canvas", None)
            renderer = None
            if canvas is not None and hasattr(canvas, "get_renderer"):
                try:
                    renderer = canvas.get_renderer()
                except (AttributeError, RuntimeError):
                    renderer = None
            if renderer is None and figure is not None:
                try:
                    canvas = FigureCanvasAgg(figure)
                    canvas.draw()
                    renderer = canvas.get_renderer()
                except (AttributeError, RuntimeError, ValueError):
                    renderer = None
            if renderer is None:
                continue
            try:
                window_bbox = artist.get_window_extent(renderer)
                data_bbox = ax.transData.inverted().transform_bbox(window_bbox)
                values = (
                    data_bbox.x0,
                    data_bbox.y0,
                    data_bbox.width,
                    data_bbox.height,
                )
            except (AttributeError, RuntimeError, ValueError):
                continue
            if all(math.isfinite(float(value)) for value in values):
                return Rectangle(
                    (float(values[0]), float(values[1])),
                    float(values[2]),
                    float(values[3]),
                    fill=False,
                    edgecolor=frame_kwargs["color"],
                    linestyle=frame_kwargs["linestyle"],
                    linewidth=frame_kwargs["linewidth"],
                    zorder=frame_kwargs["zorder"],
                )

        bounds = (
            figure_object.get("bounds", {})
            if isinstance(figure_object.get("bounds"), dict)
            else figure_object
        )
        x = self._optional_float(bounds.get("x"))
        y = self._optional_float(bounds.get("y"))
        width = self._optional_float(bounds.get("width"))
        height = self._optional_float(bounds.get("height"))
        if None in {x, y, width, height} or not all(
            math.isfinite(float(value)) for value in (x, y, width, height)
        ):
            return None
        return Rectangle(
            (float(x), float(y)),
            float(width),
            float(height),
            fill=False,
            edgecolor=frame_kwargs["color"],
            linestyle=frame_kwargs["linestyle"],
            linewidth=frame_kwargs["linewidth"],
            zorder=frame_kwargs["zorder"],
        )

    def render_document(
        self,
        *,
        document: dict,
        objects: list[dict],
        figsize: tuple[float, float],
        dpi: int,
        background: str,
        render_object,
        apply_axes_style,
        selected_object_id: str = "",
    ):
        self.reset_artist_map()
        fig = Figure(figsize=figsize, dpi=dpi, facecolor=background)
        ax = fig.add_subplot(111)
        artist_map: dict[str, list[object]] = {}

        rendered_count = 0
        visible_count = 0
        ordered_objects = sorted(
            [
                obj
                for obj in objects
                if isinstance(obj, dict)
            ],
            key=lambda item: int(item.get("z_index", 0) or 0),
        )
        for index, obj in enumerate(ordered_objects):
            if obj.get("type") == "legend":
                continue
            if obj.get("visible") is False or obj.get("deleted") is True:
                continue
            visible_count += 1
            artists = render_object(ax, obj, index) or []
            if not artists:
                continue
            rendered_count += 1
            object_id = str(obj.get("id", "") or "")
            for artist in self.register_artists(object_id, artists, render_order=index):
                artist_map.setdefault(object_id, []).append(artist)

        if rendered_count <= 0 and visible_count > 0:
            return None, {}

        apply_axes_style(ax)
        legend = ax.get_legend()
        if legend is not None:
            legend_artists = [legend, legend.get_frame(), *legend.get_lines(), *legend.get_texts()]
            for artist in legend_artists:
                self._register_artist_mapping("legend", artist, len(ordered_objects) + 1)
            artist_map["legend"] = legend_artists

        self._highlight_selected(artist_map.get(str(selected_object_id or ""), []))
        fig.tight_layout()
        return fig, artist_map

    def object_id_for_artist(self, artist) -> str:
        return str(self._artist_to_object_id.get(id(artist), "") or "")

    def object_id_for_pick_event(self, event) -> str:
        object_ids = self.object_ids_for_pick_event(event)
        if object_ids:
            return object_ids[0]
        artist = getattr(event, "artist", None)
        return self.object_id_for_artist(artist)

    def object_ids_for_pick_event(self, event) -> list[str]:
        artist = getattr(event, "artist", None)
        fallback_object_id = self.object_id_for_artist(artist)
        mouseevent = getattr(event, "mouseevent", None)
        return self.object_ids_for_mouseevent(
            mouseevent,
            fallback_object_id=fallback_object_id,
        )

    def object_ids_for_mouseevent(
        self,
        mouseevent,
        *,
        fallback_object_id: str = "",
    ) -> list[str]:
        if mouseevent is None:
            return [fallback_object_id] if fallback_object_id else []

        candidates: dict[str, tuple[int, float]] = {}
        for candidate_artist in self._registered_artists:
            if candidate_artist is None:
                continue
            contains_event = self._mouseevent_for_artist(candidate_artist, mouseevent)
            contains = self._artist_contains_mouseevent(candidate_artist, contains_event)
            if not contains:
                continue
            object_id = self.object_id_for_artist(candidate_artist)
            if not object_id:
                continue
            render_order = int(self._artist_to_render_order.get(id(candidate_artist), -1))
            zorder = float(
                candidate_artist.get_zorder() if hasattr(candidate_artist, "get_zorder") else 0.0
            )
            previous = candidates.get(object_id)
            score = (render_order, zorder)
            if previous is None or score > previous:
                candidates[object_id] = score

        if not candidates:
            return [fallback_object_id] if fallback_object_id else []

        return [
            object_id
            for object_id, _score in sorted(
                candidates.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ]

    def _mouseevent_for_artist(self, artist, mouseevent):
        figure = artist.get_figure(root=True) if hasattr(artist, "get_figure") else None
        canvas = figure.canvas if figure is not None else getattr(mouseevent, "canvas", None)
        return SimpleNamespace(
            canvas=canvas,
            x=getattr(mouseevent, "x", None),
            y=getattr(mouseevent, "y", None),
            xdata=getattr(mouseevent, "xdata", None),
            ydata=getattr(mouseevent, "ydata", None),
            inaxes=getattr(mouseevent, "inaxes", None),
        )

    def _artist_contains_mouseevent(self, artist, mouseevent) -> bool:
        try:
            contains, _details = artist.contains(mouseevent)
        except Exception:
            return False
        if contains:
            return True
        return self._artist_contains_with_pick_slop(artist, mouseevent)

    def _artist_contains_with_pick_slop(self, artist, mouseevent) -> bool:
        if not self._artist_supports_bbox_hit_slop(artist):
            return False
        artist_axes = getattr(artist, "axes", None)
        event_axes = getattr(mouseevent, "inaxes", None)
        if artist_axes is not None and event_axes is not None and artist_axes is not event_axes:
            return False
        renderer = None
        canvas = getattr(mouseevent, "canvas", None)
        if canvas is not None and hasattr(canvas, "get_renderer"):
            try:
                renderer = canvas.get_renderer()
            except Exception:
                renderer = None
        if renderer is None:
            figure = artist.get_figure(root=True) if hasattr(artist, "get_figure") else None
            figure_canvas = getattr(figure, "canvas", None) if figure is not None else None
            if figure_canvas is not None and hasattr(figure_canvas, "get_renderer"):
                try:
                    renderer = figure_canvas.get_renderer()
                except Exception:
                    renderer = None
        if renderer is None or not hasattr(artist, "get_window_extent"):
            return False
        try:
            bounds = artist.get_window_extent(renderer)
        except Exception:
            return False
        if bounds is None:
            return False
        pick_radius = self._artist_pick_slop_pixels(artist)
        if pick_radius <= 0.0:
            return False
        try:
            expanded = bounds.padded(float(pick_radius))
        except Exception:
            return False
        event_x = getattr(mouseevent, "x", None)
        event_y = getattr(mouseevent, "y", None)
        if event_x is None or event_y is None:
            return False
        return bool(expanded.contains(float(event_x), float(event_y)))

    def _artist_supports_bbox_hit_slop(self, artist) -> bool:
        from matplotlib.image import AxesImage
        from matplotlib.patches import Patch

        return isinstance(artist, (Patch, AxesImage))

    def _artist_pick_slop_pixels(self, artist) -> float:
        pick_slop = float(self._PICK_RADIUS)
        if hasattr(artist, "get_pickradius"):
            try:
                pickradius = artist.get_pickradius()
            except Exception:
                pickradius = None
            if isinstance(pickradius, (int, float)):
                pick_slop = float(pickradius)
        elif hasattr(artist, "get_picker"):
            try:
                picker = artist.get_picker()
            except Exception:
                picker = None
            if isinstance(picker, (int, float)):
                pick_slop = float(picker)
        return max(0.0, pick_slop)

    def _register_artist_mapping(self, object_id: str, artist, render_order: int) -> None:
        self._artist_to_object_id[id(artist)] = object_id
        self._artist_to_render_order[id(artist)] = int(render_order)
        self._object_id_to_artists.setdefault(object_id, []).append(artist)
        self._registered_artists.append(artist)
        self._enable_artist_picking(artist)

    def _enable_artist_picking(self, artist) -> None:
        try:
            artist.set_picker(self._PICK_RADIUS)
        except Exception:
            try:
                artist.set_picker(True)
            except Exception:
                return
        if hasattr(artist, "set_pickradius"):
            try:
                artist.set_pickradius(self._PICK_RADIUS)
            except Exception:
                pass

    def _snapshot_artist_state(self, artist) -> dict:
        state: dict[str, object] = {}
        if hasattr(artist, "get_zorder"):
            try:
                state["zorder"] = float(artist.get_zorder() or 0.0)
            except Exception:
                pass
        if hasattr(artist, "get_path_effects"):
            try:
                state["path_effects"] = list(artist.get_path_effects())
            except Exception:
                pass
        if hasattr(artist, "get_edgecolor"):
            try:
                state["edgecolor"] = deepcopy(artist.get_edgecolor())
            except Exception:
                pass
        if hasattr(artist, "get_linewidth"):
            try:
                state["linewidth"] = artist.get_linewidth()
            except Exception:
                pass
        if hasattr(artist, "get_linewidths"):
            try:
                state["linewidths"] = deepcopy(artist.get_linewidths())
            except Exception:
                pass
        if hasattr(artist, "get_color") and hasattr(artist, "get_text"):
            try:
                state["color"] = artist.get_color()
            except Exception:
                pass
        return state

    def _restore_artist_state(self, artist, state: dict) -> None:
        if "zorder" in state and hasattr(artist, "set_zorder"):
            try:
                artist.set_zorder(state["zorder"])
            except Exception:
                pass
        if "path_effects" in state and hasattr(artist, "set_path_effects"):
            try:
                artist.set_path_effects(state["path_effects"])
            except Exception:
                pass
        if "edgecolor" in state and hasattr(artist, "set_edgecolor"):
            try:
                artist.set_edgecolor(state["edgecolor"])
            except Exception:
                pass
        if "linewidth" in state and hasattr(artist, "set_linewidth"):
            try:
                artist.set_linewidth(state["linewidth"])
            except Exception:
                pass
        if "linewidths" in state and hasattr(artist, "set_linewidths"):
            try:
                artist.set_linewidths(state["linewidths"])
            except Exception:
                pass
        if "color" in state and hasattr(artist, "set_color") and hasattr(artist, "get_text"):
            try:
                artist.set_color(state["color"])
            except Exception:
                pass

    def _highlight_selected(self, artists: list[object]) -> None:
        from matplotlib import patheffects

        highlight_color = "#D55E00"
        for artist in artists:
            if hasattr(artist, "get_zorder") and hasattr(artist, "set_zorder"):
                try:
                    artist.set_zorder(float(artist.get_zorder() or 0.0) + 10.0)
                except Exception:
                    pass
            if hasattr(artist, "set_path_effects"):
                try:
                    base_width = 1.0
                    if hasattr(artist, "get_linewidth"):
                        base_width = float(artist.get_linewidth() or 1.0)
                    artist.set_path_effects(
                        [
                            patheffects.Stroke(
                                linewidth=max(base_width + 2.0, 2.5),
                                foreground=highlight_color,
                            ),
                            patheffects.Normal(),
                        ]
                    )
                except Exception:
                    pass
            if hasattr(artist, "set_edgecolor") and hasattr(artist, "set_linewidths"):
                try:
                    artist.set_edgecolor(highlight_color)
                    linewidths = artist.get_linewidths()
                    base_width = 1.0
                    if len(linewidths):
                        base_width = float(linewidths[0] or 1.0)
                    artist.set_linewidths([max(base_width + 1.5, 2.5)])
                except Exception:
                    pass
            if hasattr(artist, "set_color") and hasattr(artist, "get_text"):
                try:
                    artist.set_color(highlight_color)
                except Exception:
                    pass
        if artists:
            frame = artists[1] if len(artists) > 1 else None
            if frame is not None and hasattr(frame, "set_edgecolor"):
                try:
                    frame.set_edgecolor(highlight_color)
                    frame.set_linewidth(2.0)
                except Exception:
                    pass

    def _highlight_hover_artists(self, artists: list[object]) -> None:
        from matplotlib import patheffects

        hover_color = "#E69F00"
        for artist in artists:
            if hasattr(artist, "get_zorder") and hasattr(artist, "set_zorder"):
                try:
                    artist.set_zorder(float(artist.get_zorder() or 0.0) + 6.0)
                except Exception:
                    pass
            if hasattr(artist, "set_path_effects"):
                try:
                    base_width = 1.0
                    if hasattr(artist, "get_linewidth"):
                        base_width = float(artist.get_linewidth() or 1.0)
                    artist.set_path_effects(
                        [
                            patheffects.Stroke(
                                linewidth=max(base_width + 1.5, 2.0),
                                foreground=hover_color,
                            ),
                            patheffects.Normal(),
                        ]
                    )
                except Exception:
                    pass
            if hasattr(artist, "set_edgecolor") and hasattr(artist, "set_linewidths"):
                try:
                    artist.set_edgecolor(hover_color)
                    linewidths = artist.get_linewidths()
                    base_width = 1.0
                    if len(linewidths):
                        base_width = float(linewidths[0] or 1.0)
                    artist.set_linewidths([max(base_width + 1.0, 2.0)])
                except Exception:
                    pass
            if hasattr(artist, "set_color") and hasattr(artist, "get_text"):
                try:
                    artist.set_color(hover_color)
                except Exception:
                    pass
        if artists:
            frame = artists[1] if len(artists) > 1 else None
            if frame is not None and hasattr(frame, "set_edgecolor"):
                try:
                    base_width = 1.0
                    if hasattr(frame, "get_linewidth"):
                        base_width = float(frame.get_linewidth() or 1.0)
                    frame.set_edgecolor(hover_color)
                    frame.set_linewidth(max(base_width + 1.0, 1.5))
                except Exception:
                    pass

    def _plot_series_handle_points(self, figure_object: dict) -> list[tuple[float, float]]:
        return [
            (x_coord, y_coord)
            for _index, x_coord, y_coord in self._plot_series_indexed_handle_points(figure_object)
        ]

    def _plot_series_indexed_handle_points(
        self, figure_object: dict
    ) -> list[tuple[int, float, float]]:
        inline_data = figure_object.get("data", {})
        if not isinstance(inline_data, dict):
            return []
        x_values = inline_data.get("x", inline_data.get("x_values", []))
        y_values = inline_data.get("y", inline_data.get("y_values", []))
        if not x_values or not y_values:
            return []
        points: list[tuple[int, float, float]] = []
        for point_index, (x_value, y_value) in enumerate(zip(x_values, y_values)):
            x_coord = self._optional_float(x_value)
            y_coord = self._optional_float(y_value)
            if x_coord is None or y_coord is None:
                continue
            points.append((int(point_index), x_coord, y_coord))
        return points

    def _optional_float(self, value):
        try:
            if value is None or value == "":
                return None
            return float(value)
        except (TypeError, ValueError):
            return None
