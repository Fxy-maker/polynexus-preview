from __future__ import annotations

GENERATED_LINE_BODY_HIT_RADIUS_PX = 10.0
GENERATED_LINE_ENDPOINT_HIT_RADIUS_PX = 14.0
GENERATED_SCATTER_POINT_HIT_RADIUS_PX = 14.0
GENERATED_LINE_SERIES_BODY_HIT_RADIUS_PX = 10.0
GENERATED_MARKER_POINT_HIT_MAX_RADIUS_PX = 20.0


class ChartEditorGeneratedHitTestingMixin:
    def _generated_line_drag_start(self, event, object_id):
        figure_object = self._generated_figure_object_by_id(object_id)
        if not figure_object or str(figure_object.get("type", "") or "") != "line":
            return None
        line_artist = self._generated_line_artist(object_id)
        if line_artist is None:
            return None
        axes = getattr(event, "inaxes", None)
        if axes is None:
            return None
        try:
            x_data = list(line_artist.get_xdata())
            y_data = list(line_artist.get_ydata())
        except Exception:
            return None
        if len(x_data) < 2 or len(y_data) < 2:
            return None
        pixel_points = line_artist.get_transform().transform(list(zip(x_data[:2], y_data[:2])))
        event_x = float(getattr(event, "x", 0.0) or 0.0)
        event_y = float(getattr(event, "y", 0.0) or 0.0)
        distance = self._distance_to_segment_pixels(
            event_x,
            event_y,
            float(pixel_points[0][0]),
            float(pixel_points[0][1]),
            float(pixel_points[1][0]),
            float(pixel_points[1][1]),
        )
        if distance is None or distance > float(GENERATED_LINE_BODY_HIT_RADIUS_PX):
            return None
        coordinates = self._generated_event_data_coordinates(event)
        if coordinates is None:
            return None
        geometry = self._generated_object_geometry_config(figure_object)
        return {
            "object_id": str(object_id or ""),
            "kind": "line-body",
            "dirty": False,
            "press_data": coordinates,
            "geometry_mode": str(geometry.get("mode", "segment") or "segment"),
            "origin_geometry": {
                "x1": self._optional_float(figure_object.get("x1")),
                "y1": self._optional_float(figure_object.get("y1")),
                "x2": self._optional_float(figure_object.get("x2")),
                "y2": self._optional_float(figure_object.get("y2")),
            },
        }

    def _generated_line_endpoint_hit(self, event, figure_object):
        if (
            not isinstance(figure_object, dict)
            or str(figure_object.get("type", "") or "") != "line"
        ):
            return None
        line_artist = self._generated_line_artist(str(figure_object.get("id", "") or ""))
        axes = getattr(event, "inaxes", None)
        if line_artist is None or axes is None:
            return None
        try:
            x_data = list(line_artist.get_xdata())
            y_data = list(line_artist.get_ydata())
        except Exception:
            return None
        if len(x_data) < 2 or len(y_data) < 2:
            return None
        pixel_points = line_artist.get_transform().transform(list(zip(x_data[:2], y_data[:2])))
        match = self._nearest_pixel_point_match(
            pixel_points,
            event,
            max_radius=GENERATED_LINE_ENDPOINT_HIT_RADIUS_PX,
        )
        if match is None:
            return None
        best_index, _distance = match
        return int(best_index)

    def _distance_to_segment_pixels(self, px, py, x1, y1, x2, y2):
        distance, _projection = self._segment_distance_projection_pixels(px, py, x1, y1, x2, y2)
        return distance

    def _segment_distance_projection_pixels(self, px, py, x1, y1, x2, y2):
        dx = float(x2) - float(x1)
        dy = float(y2) - float(y1)
        if dx == 0.0 and dy == 0.0:
            distance = ((float(px) - float(x1)) ** 2 + (float(py) - float(y1)) ** 2) ** 0.5
            return distance, 0.0
        length_squared = dx * dx + dy * dy
        projection = ((float(px) - float(x1)) * dx + (float(py) - float(y1)) * dy) / length_squared
        projection = max(0.0, min(1.0, projection))
        nearest_x = float(x1) + projection * dx
        nearest_y = float(y1) + projection * dy
        distance = ((float(px) - nearest_x) ** 2 + (float(py) - nearest_y) ** 2) ** 0.5
        return distance, projection

    def _generated_plot_series_handle_hit(self, event, object_id):
        figure_object = self._generated_figure_object_by_id(object_id)
        if not figure_object or str(figure_object.get("type", "") or "") != "plot_series":
            return None
        hit_info = self._generated_plot_series_drag_hit(event, object_id, figure_object)
        if hit_info is None:
            return None
        return int(hit_info["handle_index"])

    def _generated_plot_series_drag_hit(self, event, object_id, figure_object):
        handle_hit = self._generated_point_handle_hit(event, object_id)
        if handle_hit is not None:
            return {
                "handle_index": int(handle_hit),
                "nearest_point_hit": False,
            }
        point_hit = self._generated_plot_series_point_hit(event, object_id, figure_object)
        if point_hit is not None:
            return {
                "handle_index": int(point_hit),
                "nearest_point_hit": False,
            }
        segment_hit = self._generated_plot_series_segment_hit(event, object_id, figure_object)
        if segment_hit is None:
            return None
        return {
            "handle_index": int(segment_hit),
            "nearest_point_hit": True,
        }

    def _generated_plot_series_point_hit(self, event, object_id, figure_object):
        if not isinstance(figure_object, dict):
            return None
        chart_kind = str(figure_object.get("chart_kind", "") or "")
        if chart_kind in {"heatmap", "bar", "barh", "image_grid"}:
            return None
        marker_value = self._generated_plot_series_marker_value(figure_object)
        max_radius = 12.0 if marker_value else 8.0
        axes = getattr(event, "inaxes", None)
        if axes is None:
            axes = self._figure.axes[0] if self._figure and self._figure.axes else None
        if axes is None:
            return None
        plot_points = self._generated_plot_series_points(object_id, figure_object)
        if not plot_points:
            return None
        pixel_offsets = axes.transData.transform(
            [(x_coord, y_coord) for _index, x_coord, y_coord in plot_points]
        )
        max_radius = self._generated_plot_series_point_hit_radius(
            figure_object,
            pixel_offsets,
            default_radius=max_radius,
        )
        best_match = self._nearest_pixel_point_match(pixel_offsets, event, max_radius=max_radius)
        if best_match is None:
            return None
        best_index, _distance = best_match
        return int(plot_points[int(best_index)][0])

    def _generated_plot_series_segment_hit(self, event, object_id, figure_object):
        if not isinstance(figure_object, dict):
            return None
        chart_kind = str(figure_object.get("chart_kind", "") or "")
        if chart_kind in {"heatmap", "bar", "barh", "image_grid", "scatter"}:
            return None
        marker_value = self._generated_plot_series_marker_value(figure_object)
        if marker_value:
            return None
        axes = getattr(event, "inaxes", None)
        if axes is None:
            axes = self._figure.axes[0] if self._figure and self._figure.axes else None
        if axes is None:
            return None
        plot_points = self._generated_plot_series_points(object_id, figure_object)
        if len(plot_points) < 2:
            return None
        pixel_points = axes.transData.transform(
            [(x_coord, y_coord) for _index, x_coord, y_coord in plot_points]
        )
        max_radius = self._generated_plot_series_segment_hit_radius(
            pixel_points,
            default_radius=GENERATED_LINE_SERIES_BODY_HIT_RADIUS_PX,
        )
        best_match = self._nearest_pixel_segment_match(pixel_points, event, max_radius=max_radius)
        if best_match is None:
            return None
        segment_index, projection, _distance = best_match
        if int(segment_index) < 0 or int(segment_index) >= len(plot_points) - 1:
            return None
        if float(projection) >= 0.5:
            return int(plot_points[int(segment_index) + 1][0])
        return int(plot_points[int(segment_index)][0])

    def _generated_point_handle_hit(self, event, object_id):
        handle_artist = self._generated_selection_handle_artist(object_id)
        axes = getattr(event, "inaxes", None)
        if handle_artist is None or axes is None:
            return None
        try:
            offsets = handle_artist.get_offsets()
        except Exception:
            return None
        if len(offsets) <= 0:
            return None
        pixel_offsets = axes.transData.transform(offsets)
        best_match = self._nearest_pixel_point_match(pixel_offsets, event, max_radius=12.0)
        if best_match is None:
            return None
        best_index, _distance = best_match
        handle_indices = getattr(handle_artist, "_pn_handle_indices", None)
        if (
            isinstance(handle_indices, (list, tuple))
            and 0 <= int(best_index) < len(handle_indices)
        ):
            try:
                return int(handle_indices[int(best_index)])
            except (TypeError, ValueError):
                pass
        return int(best_index)

    def _nearest_pixel_point_match(self, pixel_offsets, event, max_radius):
        event_x = float(getattr(event, "x", 0.0) or 0.0)
        event_y = float(getattr(event, "y", 0.0) or 0.0)
        best_index = None
        best_distance = None
        for index, (pixel_x, pixel_y) in enumerate(pixel_offsets):
            distance = (float(pixel_x) - event_x) ** 2 + (float(pixel_y) - event_y) ** 2
            if best_distance is None or distance < best_distance:
                best_distance = distance
                best_index = index
        if best_distance is None or best_distance > float(max_radius) ** 2:
            return None
        return best_index, best_distance

    def _nearest_pixel_segment_match(self, pixel_points, event, max_radius):
        if len(pixel_points) < 2:
            return None
        event_x = float(getattr(event, "x", 0.0) or 0.0)
        event_y = float(getattr(event, "y", 0.0) or 0.0)
        best_index = None
        best_projection = 0.0
        best_distance = None
        for index in range(len(pixel_points) - 1):
            distance, projection = self._segment_distance_projection_pixels(
                event_x,
                event_y,
                float(pixel_points[index][0]),
                float(pixel_points[index][1]),
                float(pixel_points[index + 1][0]),
                float(pixel_points[index + 1][1]),
            )
            if best_distance is None or distance < best_distance:
                best_index = index
                best_projection = projection
                best_distance = distance
        if best_distance is None or best_distance > float(max_radius):
            return None
        return best_index, best_projection, best_distance

    def _generated_plot_series_point_hit_radius(self, figure_object, pixel_points, default_radius):
        chart_kind = str(figure_object.get("chart_kind", "") or "")
        style = (
            figure_object.get("style", {})
            if isinstance(figure_object, dict)
            and isinstance(figure_object.get("style"), dict)
            else {}
        )
        marker_size = self._optional_float(style.get("marker_size"))
        if chart_kind == "scatter":
            base_radius = float(GENERATED_SCATTER_POINT_HIT_RADIUS_PX)
            return self._marker_point_hit_radius(marker_size, base_radius)
        marker_value = self._generated_plot_series_marker_value(figure_object)
        if marker_value:
            if marker_size is None:
                marker_size = 6.0
            return self._marker_point_hit_radius(marker_size, 0.0)
        spacing = self._generated_plot_series_adjacent_pixel_spacing(pixel_points)
        if spacing is None:
            return float(default_radius)
        return min(float(default_radius), max(3.5, float(spacing) * 0.8))

    def _marker_point_hit_radius(self, marker_size, default_radius):
        radius = float(default_radius)
        marker_size_value = self._optional_float(marker_size)
        if marker_size_value is None:
            return radius
        dpi = self._optional_float(getattr(self, "_dpi", None))
        if dpi is None or dpi <= 0.0:
            dpi = 150.0
        marker_radius_pixels = (float(marker_size_value) * float(dpi) / 72.0) * 0.5 + 2.0
        return min(
            float(GENERATED_MARKER_POINT_HIT_MAX_RADIUS_PX),
            max(radius, float(marker_radius_pixels)),
        )

    def _generated_plot_series_segment_hit_radius(self, pixel_points, default_radius):
        spacing = self._generated_plot_series_adjacent_pixel_spacing(pixel_points)
        if spacing is None:
            return float(default_radius)
        return min(float(default_radius), max(3.0, float(spacing) * 0.55))

    def _generated_plot_series_adjacent_pixel_spacing(self, pixel_points):
        if len(pixel_points) < 2:
            return None
        distances = []
        for index in range(len(pixel_points) - 1):
            dx = float(pixel_points[index + 1][0]) - float(pixel_points[index][0])
            dy = float(pixel_points[index + 1][1]) - float(pixel_points[index][1])
            distance = (dx * dx + dy * dy) ** 0.5
            if distance > 0.0:
                distances.append(distance)
        if not distances:
            return None
        distances.sort()
        middle = len(distances) // 2
        if len(distances) % 2:
            return float(distances[middle])
        return float(distances[middle - 1] + distances[middle]) / 2.0

    def _generated_plot_series_points(self, object_id, figure_object):
        rendered_points = self._generated_plot_series_rendered_points(object_id)
        if rendered_points:
            return rendered_points
        inline_data = figure_object.get("data", {})
        data_sources = {}
        if not (
            isinstance(inline_data, dict)
            and inline_data.get("x")
            and inline_data.get("y")
        ):
            data_sources = self._load_generated_document_data_sources()
        x_values, y_values = self._generated_object_xy(figure_object, data_sources)
        if not x_values or not y_values:
            return []
        plot_points = []
        for index, (x_value, y_value) in enumerate(zip(x_values, y_values)):
            x_coord = self._optional_float(x_value)
            y_coord = self._optional_float(y_value)
            if x_coord is None or y_coord is None:
                continue
            plot_points.append((index, float(x_coord), float(y_coord)))
        return plot_points

    def _generated_plot_series_rendered_points(self, object_id):
        if self._figure is None or not self._figure.axes:
            return []
        axes = self._figure.axes[0]
        for artist in axes.collections:
            if self._figure_render_adapter.object_id_for_artist(artist) != object_id:
                continue
            try:
                offsets = artist.get_offsets()
            except Exception:
                continue
            plot_points = []
            for index, offset in enumerate(offsets):
                if len(offset) < 2:
                    continue
                x_coord = self._optional_float(offset[0])
                y_coord = self._optional_float(offset[1])
                if x_coord is None or y_coord is None:
                    continue
                plot_points.append((index, float(x_coord), float(y_coord)))
            if plot_points:
                return plot_points
        for artist in axes.lines:
            if self._figure_render_adapter.object_id_for_artist(artist) != object_id:
                continue
            try:
                x_values = list(artist.get_xdata())
                y_values = list(artist.get_ydata())
            except Exception:
                continue
            plot_points = []
            for index, (x_value, y_value) in enumerate(zip(x_values, y_values)):
                x_coord = self._optional_float(x_value)
                y_coord = self._optional_float(y_value)
                if x_coord is None or y_coord is None:
                    continue
                plot_points.append((index, float(x_coord), float(y_coord)))
            if plot_points:
                return plot_points
        return []

    def _generated_selection_handle_artist(self, object_id):
        if self._figure is None or not self._figure.axes:
            return None
        handle_gid = f"pn-selection-handles:{str(object_id or '')}"
        for artist in self._figure.axes[0].collections:
            if artist.get_gid() == handle_gid:
                return artist
        return None
