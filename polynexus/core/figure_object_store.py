"""Helpers for generated figure document object access and mutation."""

from __future__ import annotations

from copy import deepcopy


class FigureObjectStore:
    """Small mutation layer around generated figure document objects."""

    def __init__(self, document: dict):
        self._document = document if isinstance(document, dict) else {}

    def objects(self) -> list[dict]:
        objects = self._document.get("objects", [])
        return objects if isinstance(objects, list) else []

    def visible_objects(self) -> list[dict]:
        return [
            obj
            for obj in self.objects()
            if isinstance(obj, dict)
            and obj.get("type") != "image_background"
            and obj.get("deleted") is not True
        ]

    def get(self, object_id: str) -> dict | None:
        object_id = str(object_id or "")
        for obj in self.visible_objects():
            if str(obj.get("id", "") or "") == object_id:
                return obj
        return None

    def get_including_deleted(self, object_id: str) -> dict | None:
        object_id = str(object_id or "")
        for obj in self.objects():
            if isinstance(obj, dict) and str(obj.get("id", "") or "") == object_id:
                return obj
        return None

    def rename(self, object_id: str, name: str) -> bool:
        obj = self.get(object_id)
        next_name = str(name or "").strip()
        if obj is None or not next_name:
            return False
        if str(obj.get("name", "") or "") == next_name:
            return False
        obj["name"] = next_name
        return True

    def update_style(self, object_id: str, updates: dict) -> bool:
        obj = self.get(object_id)
        if obj is None or not isinstance(updates, dict):
            return False
        style = obj.setdefault("style", {})
        if not isinstance(style, dict):
            style = {}
            obj["style"] = style
        changed = False
        for key, value in deepcopy(updates).items():
            if value is None:
                continue
            if style.get(key) == value:
                continue
            style[key] = value
            changed = True
        return changed

    def set_visible(self, object_id: str, visible: bool) -> bool:
        obj = self.get_including_deleted(object_id)
        if obj is None:
            return False
        next_visible = bool(visible)
        if obj.get("visible", True) is next_visible:
            return False
        obj["visible"] = next_visible
        return True

    def soft_delete(self, object_id: str) -> bool:
        obj = self.get(object_id)
        if obj is None:
            return False
        obj["deleted"] = True
        obj["visible"] = False
        return True

    def restore(self, object_id: str) -> bool:
        obj = self.get_including_deleted(object_id)
        if obj is None:
            return False
        obj["deleted"] = False
        obj["visible"] = True
        return True

    def update_geometry(self, object_id: str, updates: dict) -> bool:
        obj = self.get(object_id)
        if obj is None or not isinstance(updates, dict):
            return False
        changed = False
        for key, value in deepcopy(updates).items():
            if value is None:
                continue
            if obj.get(key) == value:
                continue
            obj[key] = value
            changed = True
        return changed

    def ensure_legend_object(self) -> bool:
        objects = self.objects()
        layout = self._document.get("layout", {})
        panels = layout.get("panels", []) if isinstance(layout, dict) else []
        lifecycle_panel = None
        if isinstance(panels, list) and panels:
            if len(panels) == 1 and isinstance(panels[0], dict):
                lifecycle_panel = panels[0]

        existing_legend = next(
            (
                obj
                for obj in objects
                if isinstance(obj, dict)
                and str(obj.get("type", "") or "") == "legend"
            ),
            None,
        )
        if existing_legend is not None:
            if lifecycle_panel is not None:
                existing_legend.setdefault(
                    "panel_id",
                    str(lifecycle_panel.get("panel_id") or ""),
                )
            return False
        named_visible_series = [
            obj
            for obj in objects
            if isinstance(obj, dict)
            and str(obj.get("type", "") or "") == "plot_series"
            and obj.get("visible", True) is not False
            and obj.get("deleted") is not True
            and str(obj.get("name", "") or "").strip()
        ]
        if len(named_visible_series) < 2:
            return False
        legend = {
            "id": "legend",
            "type": "legend",
            "name": "Legend",
            "visible": True,
            "locked": False,
            "z_index": len(objects),
            "style": {
                "loc": "upper right",
                "ncol": 2 if len(named_visible_series) > 3 else 1,
            },
        }
        if lifecycle_panel is not None:
            legend["panel_id"] = str(lifecycle_panel.get("panel_id") or "")
        objects.append(legend)
        return True

    def move(self, object_id: str, *, to_front: bool) -> bool:
        objects = self.objects()
        object_id = str(object_id or "")
        if not object_id or not objects:
            return False
        selected_index = next(
            (
                index
                for index, obj in enumerate(objects)
                if isinstance(obj, dict) and str(obj.get("id", "") or "") == object_id
            ),
            -1,
        )
        if selected_index < 0:
            return False
        original_ids = [
            str(obj.get("id", "") or "") if isinstance(obj, dict) else ""
            for obj in objects
        ]
        selected = objects[selected_index]
        remaining = objects[:selected_index] + objects[selected_index + 1 :]
        if to_front:
            insert_at = next(
                (
                    index
                    for index, obj in enumerate(remaining)
                    if isinstance(obj, dict) and obj.get("type") == "legend"
                ),
                len(remaining),
            )
        else:
            insert_at = next(
                (
                    index
                    for index, obj in enumerate(remaining)
                    if isinstance(obj, dict) and obj.get("type") != "image_background"
                ),
                len(remaining),
            )
        reordered = remaining[:insert_at] + [selected] + remaining[insert_at:]
        reordered_ids = [
            str(obj.get("id", "") or "") if isinstance(obj, dict) else ""
            for obj in reordered
        ]
        if reordered_ids == original_ids:
            return False
        objects[:] = reordered
        for index, obj in enumerate(objects):
            if isinstance(obj, dict):
                obj["z_index"] = index
        return True

    def replace(self, object_id: str, snapshot: dict) -> bool:
        object_id = str(object_id or "")
        if not object_id or not isinstance(snapshot, dict):
            return False
        objects = self.objects()
        for index, obj in enumerate(objects):
            if isinstance(obj, dict) and str(obj.get("id", "") or "") == object_id:
                objects[index] = deepcopy(snapshot)
                return True
        return False

    def set_plot_series_inline_data(
        self, object_id: str, x_values: list[float], y_values: list[float]
    ) -> bool:
        obj = self.get(object_id)
        if obj is None or str(obj.get("type", "") or "") != "plot_series":
            return False
        next_data = {"x": list(x_values or []), "y": list(y_values or [])}
        if not next_data["x"] or not next_data["y"]:
            return False
        if obj.get("data") == next_data:
            return False
        obj["data"] = next_data
        return True
