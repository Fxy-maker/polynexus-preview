from __future__ import annotations

from ...core.figure_text_geometry import is_axes_text_box


class ChartEditorGeneratedPressTargetMixin:
    def _generated_selected_handle_drag_state_for_press(self, event, object_id):
        figure_object = self._generated_figure_object_by_id(object_id)
        if not figure_object:
            return None
        object_type = str(figure_object.get("type", "") or "")
        if object_type == "line":
            handle_hit = self._generated_line_handle_hit(event, object_id)
            if handle_hit is None:
                return None
            return {
                "object_id": str(object_id or ""),
                "kind": "line",
                "handle_index": int(handle_hit),
                "dirty": False,
            }
        if object_type == "curve":
            handle_hit = self._generated_point_handle_hit(event, object_id)
            if handle_hit is None:
                return self._generated_annotation_body_drag_start(event, object_id)
            return {
                "object_id": str(object_id or ""),
                "kind": "curve",
                "handle_index": int(handle_hit),
                "dirty": False,
            }
        if object_type == "rectangle":
            handle_hit = self._generated_point_handle_hit(event, object_id)
            if handle_hit is None:
                return self._generated_annotation_body_drag_start(event, object_id)
            return {
                "object_id": str(object_id or ""),
                "kind": "rectangle",
                "handle_index": int(handle_hit),
                "dirty": False,
            }
        if object_type == "plot_series":
            handle_hit = self._generated_point_handle_hit(event, object_id)
            if handle_hit is None:
                return None
            return {
                "object_id": str(object_id or ""),
                "kind": "plot_series",
                "handle_index": int(handle_hit),
                "nearest_point_hit": False,
                "dirty": False,
            }
        if object_type == "legend":
            handle_hit = self._generated_point_handle_hit(event, object_id)
            if handle_hit is not None:
                return {
                    "object_id": str(object_id or ""),
                    "kind": "legend-resize",
                    "handle_index": int(handle_hit),
                    "dirty": False,
                }
            return self._generated_legend_drag_start(event, object_id)
        if object_type == "text":
            if not is_axes_text_box(figure_object):
                handle_hit = self._generated_point_handle_hit(event, object_id)
                if handle_hit is not None:
                    return {
                        "object_id": str(object_id or ""),
                        "kind": "text",
                        "handle_index": int(handle_hit),
                        "dirty": False,
                    }
                return self._generated_annotation_body_drag_start(event, object_id)
            body = self._generated_annotation_body_drag_start(event, object_id)
            if body is not None:
                return body
            handle_hit = self._generated_point_handle_hit(event, object_id)
            if handle_hit is not None:
                return {
                    "object_id": str(object_id or ""),
                    "kind": "text",
                    "handle_index": int(handle_hit),
                    "dirty": False,
                }
            return None
        return None

    def _generated_drag_state_for_press(self, event, object_id):
        figure_object = self._generated_figure_object_by_id(object_id)
        if not figure_object:
            return None
        object_type = str(figure_object.get("type", "") or "")
        if object_type == "line":
            handle_hit = self._generated_line_handle_hit(event, object_id)
            if handle_hit is not None:
                return {
                    "object_id": str(object_id or ""),
                    "kind": "line",
                    "handle_index": int(handle_hit),
                    "dirty": False,
                }
            return self._generated_line_drag_start(event, object_id)
        if object_type == "curve":
            handle_hit = self._generated_point_handle_hit(event, object_id)
            if handle_hit is None:
                return self._generated_annotation_body_drag_start(event, object_id)
            return {
                "object_id": str(object_id or ""),
                "kind": "curve",
                "handle_index": int(handle_hit),
                "dirty": False,
            }
        if object_type == "rectangle":
            handle_hit = self._generated_point_handle_hit(event, object_id)
            if handle_hit is None:
                return self._generated_annotation_body_drag_start(event, object_id)
            return {
                "object_id": str(object_id or ""),
                "kind": "rectangle",
                "handle_index": int(handle_hit),
                "dirty": False,
            }
        if object_type == "plot_series":
            hit_info = self._generated_plot_series_drag_hit(event, object_id, figure_object)
            if hit_info is None:
                return None
            return {
                "object_id": str(object_id or ""),
                "kind": "plot_series",
                "handle_index": int(hit_info["handle_index"]),
                "nearest_point_hit": bool(hit_info.get("nearest_point_hit")),
                "dirty": False,
            }
        if object_type == "legend":
            return self._generated_legend_drag_start(event, object_id)
        if object_type == "text":
            return self._generated_annotation_body_drag_start(event, object_id)
        return None

    def _generated_press_drag_target(self, event, exclude_object_id=""):
        exclude_object_id = str(exclude_object_id or "")
        adapter = getattr(self, "_generated_interaction_adapter", None)
        if not exclude_object_id and adapter is not None:
            target = adapter.hit_test(event)
            if target is not None:
                drag_state = self._generated_drag_state_for_press(
                    event,
                    target.object_id,
                )
                if drag_state is not None:
                    drag_state["hit_target"] = target
                    return target.object_id, drag_state
        seen: set[str] = set()
        for object_id in self._generated_press_drag_object_ids():
            object_id = str(object_id or "")
            if not object_id or object_id == exclude_object_id or object_id in seen:
                continue
            seen.add(object_id)
            drag_state = self._generated_drag_state_for_press(event, object_id)
            if drag_state is not None:
                return object_id, drag_state
        return None

    def _generated_press_drag_object_ids(self):
        objects = [
            obj
            for obj in self._generated_figure_objects()
            if isinstance(obj, dict)
            and obj.get("visible", True) is not False
            and obj.get("deleted") is not True
        ]
        legend_ids = [
            str(obj.get("id", "") or "")
            for obj in objects
            if str(obj.get("type", "") or "") == "legend"
        ]
        other_ids = [
            str(obj.get("id", "") or "")
            for obj in sorted(
                [obj for obj in objects if str(obj.get("type", "") or "") != "legend"],
                key=lambda item: int(item.get("z_index", 0) or 0),
                reverse=True,
            )
        ]
        return [object_id for object_id in [*legend_ids, *other_ids] if object_id]
