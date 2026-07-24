"""Atomic, document-only commands for Origin-style figure edits."""

from __future__ import annotations

import math
from copy import deepcopy
from collections.abc import Mapping, Sequence
from typing import Any
from uuid import uuid4

from .figure_edit_capabilities import (
    EditCommand,
    EditResult,
    capabilities_for,
    is_valid_color,
    is_known_object_type,
)
from .figures.legend_geometry import canonicalize_legend_style


_UNSET = object()
_GEOMETRY_KEYS = {
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
    "left",
    "top",
}
_STYLE_CAPABILITIES = {
    "color": "color",
    "line_width": "line_width",
    "line_style": "line_style",
    "marker": "marker",
    "marker_size": "marker_size",
    "font_size": "font_size",
}


def _success(*affected_ids: str, message: str = "") -> EditResult:
    return EditResult(True, message=message, affected_ids=tuple(affected_ids))


def _noop(*affected_ids: str, message: str = "") -> EditResult:
    return EditResult(False, message=message, affected_ids=tuple(affected_ids))


def _failure(error_code: str, message: str, *affected_ids: str) -> EditResult:
    return EditResult(False, error_code=error_code, message=message, affected_ids=tuple(affected_ids))


def _objects(document: object, *, create: bool = False) -> list[dict] | None:
    if not isinstance(document, dict):
        return None
    value = document.get("objects")
    if value is None and create:
        document["objects"] = []
        value = document["objects"]
    if not isinstance(value, list):
        return None
    return value


def _object_id(payload: object) -> str:
    if not isinstance(payload, dict):
        return ""
    value = payload.get("id", payload.get("object_id", ""))
    return str(value).strip() if value is not None else ""


def _find_object(document: object, object_id: object) -> tuple[int, dict] | None:
    objects = _objects(document)
    wanted = str(object_id or "").strip()
    if objects is None or not wanted:
        return None
    for index, payload in enumerate(objects):
        if isinstance(payload, dict) and _object_id(payload) == wanted:
            return index, payload
    return None


def _editable_object(
    document: object,
    object_id: object,
    capability: str,
    *,
    allow_locked_crop: bool = False,
) -> tuple[EditResult | None, tuple[int, dict] | None]:
    found = _find_object(document, object_id)
    wanted = str(object_id or "").strip()
    if found is None:
        return _failure("object_not_found", f"Object '{wanted}' was not found.", wanted), None
    _, payload = found
    capabilities = capabilities_for(payload)
    legend_geometry_style = (
        capability == "style"
        and str(payload.get("type", "") or "") == "legend"
    )
    if capabilities.locked and not (allow_locked_crop and capabilities.crop):
        return _failure("locked", f"Object '{wanted}' is locked.", wanted), None
    if not getattr(capabilities, capability) and not legend_geometry_style:
        return (
            _failure(
                "capability_not_supported",
                f"Object '{wanted}' does not support {capability} edits.",
                wanted,
            ),
            None,
        )
    return None, found


def _valid_number(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(float(value))


def _restore_style(document: object, snapshot: object, object_id: str) -> EditResult:
    found = _find_object(document, object_id)
    if found is None:
        return _failure("object_not_found", f"Object '{object_id}' was not found.", object_id)
    if not isinstance(snapshot, dict) or "had_style" not in snapshot:
        return _failure("invalid_snapshot", "The style snapshot is invalid.", object_id)
    payload = found[1]
    had_style = bool(snapshot["had_style"])
    previous = deepcopy(snapshot.get("style"))
    current_had_style = "style" in payload
    if current_had_style == had_style and payload.get("style") == previous:
        return _noop(object_id, message="Style is already restored.")
    if had_style:
        payload["style"] = previous
    else:
        payload.pop("style", None)
    return _success(object_id)


class AddObjectCommand:
    def __init__(self, object_payload: dict | None = None, *, index: int | None = None):
        self.object_payload = deepcopy(object_payload)
        self.index = index

    def apply(self, document: dict) -> tuple[EditResult, object]:
        if not isinstance(self.object_payload, dict):
            return _failure("invalid_payload", "An object dictionary is required."), None
        objects = _objects(document)
        if objects is None and isinstance(document, dict) and "objects" not in document:
            objects = []
        if objects is None:
            return _failure("invalid_document", "Document objects must be a list."), None
        payload = deepcopy(self.object_payload)
        object_id = _object_id(payload)
        if not object_id:
            return _failure("invalid_payload", "An object id is required."), None
        if _find_object(document, object_id) is not None:
            return _failure("object_exists", f"Object '{object_id}' already exists.", object_id), None
        insertion_index = len(objects) if self.index is None else self.index
        if isinstance(insertion_index, bool) or not isinstance(insertion_index, int):
            return _failure("invalid_index", "The insertion index must be an integer.", object_id), None
        if not 0 <= insertion_index <= len(objects):
            return _failure("invalid_index", "The insertion index is outside the object list.", object_id), None
        if "objects" not in document:
            document["objects"] = objects
        objects.insert(insertion_index, payload)
        return _success(object_id), {"index": insertion_index, "object": payload}

    def revert(self, document: dict, snapshot: object) -> EditResult:
        if not isinstance(snapshot, dict) or not isinstance(snapshot.get("object"), dict):
            return _failure("invalid_snapshot", "The add snapshot is invalid.")
        object_id = _object_id(snapshot["object"])
        found = _find_object(document, object_id)
        if found is None:
            return _failure("object_not_found", f"Object '{object_id}' was not found.", object_id)
        objects = _objects(document)
        if objects is None:
            return _failure("invalid_document", "Document objects must be a list.", object_id)
        del objects[found[0]]
        return _success(object_id)


class DeleteObjectCommand:
    def __init__(self, object_id: str):
        self.object_id = str(object_id or "").strip()

    def apply(self, document: dict) -> tuple[EditResult, object]:
        error, found = _editable_object(document, self.object_id, "deletable")
        if error is not None:
            return error, None
        assert found is not None
        index, payload = found
        objects = _objects(document)
        assert objects is not None
        snapshot = {"index": index, "object": deepcopy(payload)}
        del objects[index]
        return _success(self.object_id), snapshot

    def revert(self, document: dict, snapshot: object) -> EditResult:
        if not isinstance(snapshot, dict) or not isinstance(snapshot.get("object"), dict):
            return _failure("invalid_snapshot", "The delete snapshot is invalid.", self.object_id)
        objects = _objects(document)
        if objects is None:
            return _failure("invalid_document", "Document objects must be a list.", self.object_id)
        if _find_object(document, self.object_id) is not None:
            return _failure("object_exists", f"Object '{self.object_id}' already exists.", self.object_id)
        index = snapshot.get("index")
        if isinstance(index, bool) or not isinstance(index, int):
            return _failure("invalid_snapshot", "The delete index is invalid.", self.object_id)
        objects.insert(max(0, min(index, len(objects))), deepcopy(snapshot["object"]))
        return _success(self.object_id)


class UpdateStyleCommand:
    def __init__(self, object_id: str, updates: Mapping[str, Any] | None = None):
        self.object_id = str(object_id or "").strip()
        self.updates = deepcopy(dict(updates)) if isinstance(updates, Mapping) else updates

    def apply(self, document: dict) -> tuple[EditResult, object]:
        error, found = _editable_object(document, self.object_id, "style")
        if error is not None:
            return error, None
        assert found is not None
        _, payload = found
        if not isinstance(self.updates, dict) or not self.updates:
            return _failure("invalid_payload", "Style updates must be a non-empty mapping.", self.object_id), None

        for key, value in self.updates.items():
            if value is None:
                continue
            capability_name = _STYLE_CAPABILITIES.get(str(key))
            capabilities = capabilities_for(payload)
            legend_geometry_style = str(payload.get("type", "") or "") == "legend" and str(
                key
            ) in {"loc", "bbox_to_anchor"}
            if (
                capability_name is not None
                and not getattr(capabilities, capability_name)
                and not legend_geometry_style
            ):
                return (
                    _failure(
                        "capability_not_supported",
                        f"Object '{self.object_id}' does not support style field '{key}'.",
                        self.object_id,
                    ),
                    None,
                )
            if str(key) == "color" and not is_valid_color(value):
                return _failure("invalid_color", f"'{value}' is not a valid color.", self.object_id), None

        previous_style = deepcopy(payload.get("style"))
        had_style = "style" in payload
        style = payload.get("style")
        if not isinstance(style, dict):
            style = {}
        next_style = deepcopy(style)
        for key, value in self.updates.items():
            if value is not None:
                next_style[key] = deepcopy(value)
        if str(payload.get("type", "") or "") == "legend":
            next_style = canonicalize_legend_style(next_style)
        if next_style == style and had_style:
            return _noop(self.object_id, message="Style already has the requested values."), None
        if not next_style and not had_style:
            return _noop(self.object_id, message="Style already has the requested values."), None
        payload["style"] = next_style
        return _success(self.object_id), {"had_style": had_style, "style": previous_style}

    def revert(self, document: dict, snapshot: object) -> EditResult:
        return _restore_style(document, snapshot, self.object_id)


class UpdateTextCommand:
    def __init__(self, object_id: str, text: object = _UNSET, *, new_text: object = _UNSET):
        self.object_id = str(object_id or "").strip()
        self.text = new_text if new_text is not _UNSET else text

    def apply(self, document: dict) -> tuple[EditResult, object]:
        error, found = _editable_object(document, self.object_id, "text")
        if error is not None:
            return error, None
        assert found is not None
        _, payload = found
        if self.text is _UNSET or not isinstance(self.text, str):
            return _failure("invalid_payload", "Text must be a string.", self.object_id), None
        if payload.get("text") == self.text:
            return _noop(self.object_id, message="Text already has the requested value."), None
        snapshot = {"had_text": "text" in payload, "text": deepcopy(payload.get("text"))}
        payload["text"] = self.text
        return _success(self.object_id), snapshot

    def revert(self, document: dict, snapshot: object) -> EditResult:
        found = _find_object(document, self.object_id)
        if found is None:
            return _failure("object_not_found", f"Object '{self.object_id}' was not found.", self.object_id)
        if not isinstance(snapshot, dict) or "had_text" not in snapshot:
            return _failure("invalid_snapshot", "The text snapshot is invalid.", self.object_id)
        payload = found[1]
        had_text = bool(snapshot["had_text"])
        old_text = deepcopy(snapshot.get("text"))
        if ("text" in payload) == had_text and payload.get("text") == old_text:
            return _noop(self.object_id, message="Text is already restored.")
        if had_text:
            payload["text"] = old_text
        else:
            payload.pop("text", None)
        return _success(self.object_id)


class UpdateGeometryCommand:
    def __init__(self, object_id: str, updates: Mapping[str, Any] | None = None):
        self.object_id = str(object_id or "").strip()
        self.updates = deepcopy(dict(updates)) if isinstance(updates, Mapping) else updates

    def apply(self, document: dict) -> tuple[EditResult, object]:
        error, found = _editable_object(document, self.object_id, "geometry")
        if error is not None:
            return error, None
        assert found is not None
        _, payload = found
        if not isinstance(self.updates, dict) or not self.updates:
            return _failure("invalid_payload", "Geometry updates must be a non-empty mapping.", self.object_id), None
        if any(key not in _GEOMETRY_KEYS for key in self.updates):
            bad_key = next(key for key in self.updates if key not in _GEOMETRY_KEYS)
            return _failure("invalid_field", f"'{bad_key}' is not a geometry field.", self.object_id), None
        if any(not _valid_number(value) for value in self.updates.values()):
            return _failure("invalid_geometry", "Geometry values must be finite numbers.", self.object_id), None

        container_key = None
        if isinstance(payload.get("geometry"), dict):
            container_key = "geometry"
        elif isinstance(payload.get("bounds"), dict):
            container_key = "bounds"
        container = payload.get(container_key) if container_key else payload
        assert isinstance(container, dict)
        top_level_previous = {
            key: deepcopy(payload[key]) for key in self.updates if key in payload and container_key
        }
        previous = {
            "container_key": container_key,
            "container": (
                deepcopy(container)
                if container_key
                else {key: deepcopy(payload[key]) for key in self.updates if key in payload}
            ),
            "present": tuple(key for key in self.updates if key in payload),
            "top_level": top_level_previous,
        }
        next_values = {key: deepcopy(value) for key, value in self.updates.items()}
        changed = any(container.get(key) != value for key, value in next_values.items())
        if container_key:
            changed = changed or any(payload.get(key) != value for key, value in next_values.items() if key in payload)
        if not changed:
            return _noop(self.object_id, message="Geometry already has the requested values."), None
        container.update(next_values)
        if container_key:
            for key, value in next_values.items():
                if key in payload:
                    payload[key] = deepcopy(value)
        return _success(self.object_id), previous

    def revert(self, document: dict, snapshot: object) -> EditResult:
        found = _find_object(document, self.object_id)
        if found is None:
            return _failure("object_not_found", f"Object '{self.object_id}' was not found.", self.object_id)
        if not isinstance(snapshot, dict) or "container_key" not in snapshot:
            return _failure("invalid_snapshot", "The geometry snapshot is invalid.", self.object_id)
        payload = found[1]
        container_key = snapshot.get("container_key")
        if container_key is None:
            current = {key: deepcopy(payload.get(key)) for key in self.updates if key in payload}
            old = snapshot.get("container")
            if not isinstance(old, dict):
                return _failure("invalid_snapshot", "The geometry snapshot is invalid.", self.object_id)
            present = set(snapshot.get("present", old))
            if all(
                (key in payload) == (key in present) and current.get(key) == old.get(key)
                for key in self.updates
            ):
                return _noop(self.object_id, message="Geometry is already restored.")
            for key in self.updates:
                if key in present:
                    payload[key] = deepcopy(old[key])
                else:
                    payload.pop(key, None)
            return _success(self.object_id)
        old_container = snapshot.get("container")
        if not isinstance(old_container, dict):
            return _failure("invalid_snapshot", "The geometry snapshot is invalid.", self.object_id)
        current_container = payload.get(container_key)
        top_level_snapshot = snapshot.get("top_level", {})
        if not isinstance(top_level_snapshot, dict):
            return _failure("invalid_snapshot", "The geometry top-level snapshot is invalid.", self.object_id)
        top_level_restored = all(payload.get(key) == value for key, value in top_level_snapshot.items())
        if isinstance(current_container, dict) and current_container == old_container and top_level_restored:
            return _noop(self.object_id, message="Geometry is already restored.")
        if not isinstance(current_container, dict):
            payload[container_key] = deepcopy(old_container)
        elif current_container != old_container:
            payload[container_key] = deepcopy(old_container)
        for key, value in top_level_snapshot.items():
            payload[key] = deepcopy(value)
        return _success(self.object_id)


class UpdatePlotSeriesDataCommand:
    """Replace editable inline plot-series points as one undoable change."""

    def __init__(
        self,
        object_id: str,
        x_values: Sequence[Any] | None = None,
        y_values: Sequence[Any] | None = None,
    ):
        self.object_id = str(object_id or "").strip()
        self.x_values = deepcopy(list(x_values or []))
        self.y_values = deepcopy(list(y_values or []))

    def apply(self, document: dict) -> tuple[EditResult, object]:
        error, found = _editable_object(document, self.object_id, "geometry")
        if error is not None:
            return error, None
        assert found is not None
        _, payload = found
        if not self.x_values or not self.y_values or len(self.x_values) != len(self.y_values):
            return _failure(
                "invalid_payload",
                "Plot-series x and y data must be non-empty and have equal length.",
                self.object_id,
            ), None
        if any(not _valid_number(value) for value in [*self.x_values, *self.y_values]):
            return _failure(
                "invalid_geometry",
                "Plot-series data values must be finite numbers.",
                self.object_id,
            ), None
        previous = deepcopy(payload.get("data"))
        if previous == {"x": self.x_values, "y": self.y_values}:
            return _noop(self.object_id, message="Plot-series data is unchanged."), None
        had_data = "data" in payload
        payload["data"] = {"x": deepcopy(self.x_values), "y": deepcopy(self.y_values)}
        return _success(self.object_id), {
            "had_data": had_data,
            "data": previous,
        }

    def revert(self, document: dict, snapshot: object) -> EditResult:
        found = _find_object(document, self.object_id)
        if found is None:
            return _failure(
                "object_not_found",
                f"Object '{self.object_id}' was not found.",
                self.object_id,
            )
        if not isinstance(snapshot, dict) or "had_data" not in snapshot:
            return _failure("invalid_snapshot", "The plot-series data snapshot is invalid.", self.object_id)
        payload = found[1]
        if snapshot["had_data"]:
            payload["data"] = deepcopy(snapshot.get("data"))
        else:
            payload.pop("data", None)
        return _success(self.object_id)


class MoveLayerCommand:
    def __init__(
        self,
        object_id: str,
        new_index: int | None = None,
        *,
        target_index: int | None = None,
        direction: str | None = None,
    ):
        self.object_id = str(object_id or "").strip()
        self.new_index = target_index if target_index is not None else new_index
        self.direction = str(direction or "").strip().lower()

    def apply(self, document: dict) -> tuple[EditResult, object]:
        error, found = _editable_object(document, self.object_id, "reorderable")
        if error is not None:
            return error, None
        assert found is not None
        index, _ = found
        objects = _objects(document)
        assert objects is not None
        target = self.new_index
        if target is None and self.direction in {"up", "down", "front", "back"}:
            if self.direction == "up":
                target = index - 1
            elif self.direction == "down":
                target = index + 1
            elif self.direction == "front":
                target = len(objects) - 1
            else:
                target = 0
        if isinstance(target, bool) or not isinstance(target, int):
            return _failure("invalid_index", "A target layer index is required.", self.object_id), None
        if not 0 <= target < len(objects):
            return _failure("invalid_index", "The target layer index is outside the object list.", self.object_id), None
        if target == index:
            return _noop(self.object_id, message="Object is already at that layer."), None
        snapshot = {"objects": deepcopy(objects)}
        selected = objects.pop(index)
        objects.insert(target, selected)
        if any(isinstance(payload, dict) and "z_index" in payload for payload in objects):
            for z_index, payload in enumerate(objects):
                if isinstance(payload, dict) and "z_index" in payload:
                    payload["z_index"] = z_index
        return _success(self.object_id), snapshot

    def revert(self, document: dict, snapshot: object) -> EditResult:
        objects = _objects(document)
        if objects is None:
            return _failure("invalid_document", "Document objects must be a list.", self.object_id)
        if not isinstance(snapshot, dict) or not isinstance(snapshot.get("objects"), list):
            return _failure("invalid_snapshot", "The layer snapshot is invalid.", self.object_id)
        old_objects = deepcopy(snapshot["objects"])
        if objects == old_objects:
            return _noop(self.object_id, message="Layer order is already restored.")
        objects[:] = old_objects
        return _success(self.object_id)


class SetVisibilityCommand:
    def __init__(self, object_id: str, visible: bool):
        self.object_id = str(object_id or "").strip()
        self.visible = visible

    def apply(self, document: dict) -> tuple[EditResult, object]:
        found = _find_object(document, self.object_id)
        if found is None:
            return _failure("object_not_found", f"Object '{self.object_id}' was not found.", self.object_id), None
        if not isinstance(self.visible, bool):
            return _failure("invalid_payload", "Visibility must be a boolean.", self.object_id), None
        payload = found[1]
        capabilities = capabilities_for(payload)
        if capabilities.locked:
            return _failure("locked", f"Object '{self.object_id}' is locked.", self.object_id), None
        if not is_known_object_type(payload):
            return _failure(
                "capability_not_supported",
                f"Object '{self.object_id}' does not support visibility edits.",
                self.object_id,
            ), None
        current = payload.get("visible", True)
        if current == self.visible and ("visible" in payload or self.visible is True):
            return _noop(self.object_id, message="Visibility already has the requested value."), None
        snapshot = {"had_visible": "visible" in payload, "visible": deepcopy(payload.get("visible"))}
        payload["visible"] = self.visible
        return _success(self.object_id), snapshot

    def revert(self, document: dict, snapshot: object) -> EditResult:
        found = _find_object(document, self.object_id)
        if found is None:
            return _failure("object_not_found", f"Object '{self.object_id}' was not found.", self.object_id)
        if not isinstance(snapshot, dict) or "had_visible" not in snapshot:
            return _failure("invalid_snapshot", "The visibility snapshot is invalid.", self.object_id)
        payload = found[1]
        had_visible = bool(snapshot["had_visible"])
        old_value = deepcopy(snapshot.get("visible"))
        if ("visible" in payload) == had_visible and payload.get("visible") == old_value:
            return _noop(self.object_id, message="Visibility is already restored.")
        if had_visible:
            payload["visible"] = old_value
        else:
            payload.pop("visible", None)
        return _success(self.object_id)


class SetLockCommand:
    """Toggle an editable object's lock state through the command session."""

    def __init__(self, object_id: str, locked: bool):
        self.object_id = str(object_id or "").strip()
        self.locked = locked

    def apply(self, document: dict) -> tuple[EditResult, object]:
        found = _find_object(document, self.object_id)
        if found is None:
            return _failure("object_not_found", f"Object '{self.object_id}' was not found.", self.object_id), None
        if not isinstance(self.locked, bool):
            return _failure("invalid_payload", "Lock state must be a boolean.", self.object_id), None
        payload = found[1]
        if not is_known_object_type(payload) or str(payload.get("type", "")) == "image_background":
            return _failure(
                "capability_not_supported",
                f"Object '{self.object_id}' does not support locking.",
                self.object_id,
            ), None
        current = bool(payload.get("locked", False))
        if current == self.locked and ("locked" in payload or not self.locked):
            return _noop(self.object_id, message="Lock state already has the requested value."), None
        snapshot = {"had_locked": "locked" in payload, "locked": deepcopy(payload.get("locked"))}
        payload["locked"] = self.locked
        return _success(self.object_id), snapshot

    def revert(self, document: dict, snapshot: object) -> EditResult:
        found = _find_object(document, self.object_id)
        if found is None:
            return _failure("object_not_found", f"Object '{self.object_id}' was not found.", self.object_id)
        if not isinstance(snapshot, dict) or "had_locked" not in snapshot:
            return _failure("invalid_snapshot", "The lock snapshot is invalid.", self.object_id)
        payload = found[1]
        had_locked = bool(snapshot["had_locked"])
        old_value = deepcopy(snapshot.get("locked"))
        if ("locked" in payload) == had_locked and payload.get("locked") == old_value:
            return _noop(self.object_id, message="Lock state is already restored.")
        if had_locked:
            payload["locked"] = old_value
        else:
            payload.pop("locked", None)
        return _success(self.object_id)


class ReplaceObjectCommand:
    """Commit one already-previewed object state as a single history entry."""

    def __init__(self, object_id: str, object_payload: Mapping[str, Any]):
        self.object_id = str(object_id or "").strip()
        self.object_payload = deepcopy(dict(object_payload)) if isinstance(object_payload, Mapping) else None

    def apply(self, document: dict) -> tuple[EditResult, object]:
        found = _find_object(document, self.object_id)
        if found is None:
            return _failure("object_not_found", f"Object '{self.object_id}' was not found.", self.object_id), None
        if not isinstance(self.object_payload, dict) or str(self.object_payload.get("id", "")) != self.object_id:
            return _failure("invalid_payload", "Replacement object id does not match.", self.object_id), None
        if capabilities_for(found[1]).locked:
            return _failure("locked", f"Object '{self.object_id}' is locked.", self.object_id), None
        if found[1] == self.object_payload:
            return _noop(self.object_id, message="Object already has the requested state."), None
        snapshot = {"object": deepcopy(found[1])}
        found[1].clear()
        found[1].update(deepcopy(self.object_payload))
        return _success(self.object_id), snapshot

    def revert(self, document: dict, snapshot: object) -> EditResult:
        found = _find_object(document, self.object_id)
        if found is None:
            return _failure("object_not_found", f"Object '{self.object_id}' was not found.", self.object_id)
        if not isinstance(snapshot, dict) or not isinstance(snapshot.get("object"), dict):
            return _failure("invalid_snapshot", "The replacement snapshot is invalid.", self.object_id)
        if found[1] == snapshot["object"]:
            return _noop(self.object_id, message="Object is already restored.")
        found[1].clear()
        found[1].update(deepcopy(snapshot["object"]))
        return _success(self.object_id)


class ReplaceDocumentCommand:
    """Commit a validated whole-document transformation as one edit."""

    def __init__(self, document: Mapping[str, Any]):
        self.document = deepcopy(dict(document)) if isinstance(document, Mapping) else None

    def apply(self, document: dict) -> tuple[EditResult, object]:
        if not isinstance(self.document, dict):
            return _failure("invalid_payload", "Replacement document must be a mapping."), None
        if not isinstance(document, dict):
            return _failure("invalid_document", "The figure document must be a mapping."), None
        if document == self.document:
            return _noop(message="Document already has the requested state."), None
        snapshot = {"document": deepcopy(document)}
        document.clear()
        document.update(deepcopy(self.document))
        return _success(message="Document replaced."), snapshot

    def revert(self, document: dict, snapshot: object) -> EditResult:
        if not isinstance(document, dict) or not isinstance(snapshot, dict):
            return _failure("invalid_snapshot", "The document snapshot is invalid.")
        previous = snapshot.get("document")
        if not isinstance(previous, dict):
            return _failure("invalid_snapshot", "The document snapshot is invalid.")
        if document == previous:
            return _noop(message="Document is already restored.")
        document.clear()
        document.update(deepcopy(previous))
        return _success(message="Document restored.")


def _batch_objects(document: dict, object_ids: Sequence[str]):
    objects = _objects(document)
    if objects is None:
        return _failure("invalid_document", "Document objects must be a list."), None
    wanted = tuple(dict.fromkeys(str(value or "").strip() for value in object_ids if str(value or "").strip()))
    if len(wanted) < 2:
        return _failure("selection_required", "At least two objects are required."), None
    found = []
    for object_id in wanted:
        item = _find_object(document, object_id)
        if item is None:
            return _failure("object_not_found", f"Object '{object_id}' was not found.", object_id), None
        payload = item[1]
        if capabilities_for(payload).locked:
            return _failure("locked", f"Object '{object_id}' is locked.", object_id), None
        if not is_known_object_type(payload) or not capabilities_for(payload).geometry:
            return _failure("capability_not_supported", f"Object '{object_id}' cannot be batched.", object_id), None
        found.append((object_id, payload))
    return None, found


def _geometry_bounds(payload: dict):
    container = payload.get("geometry") if isinstance(payload.get("geometry"), dict) else None
    if container is None and isinstance(payload.get("bounds"), dict):
        container = payload["bounds"]
    if container is None:
        container = payload
    if all(key in container for key in ("x", "y", "width", "height")):
        x = float(container["x"])
        y = float(container["y"])
        width = float(container["width"])
        height = float(container["height"])
        return container, x, y, x + width, y + height
    if all(key in container for key in ("x1", "y1", "x2", "y2")):
        x1, x2 = float(container["x1"]), float(container["x2"])
        y1, y2 = float(container["y1"]), float(container["y2"])
        return container, min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)
    return None


def _shift_geometry(payload: dict, container: dict, dx: float, dy: float) -> None:
    for axis, delta in (("x", dx), ("y", dy)):
        if axis in container:
            container[axis] = round(float(container[axis]) + delta, 12)
        elif axis == "x" and "x1" in container and "x2" in container:
            container["x1"] = round(float(container["x1"]) + dx, 12)
            container["x2"] = round(float(container["x2"]) + dx, 12)
        elif axis == "y" and "y1" in container and "y2" in container:
            container["y1"] = round(float(container["y1"]) + dy, 12)
            container["y2"] = round(float(container["y2"]) + dy, 12)
    for key in ("x", "y", "x1", "y1", "x2", "y2"):
        if key in payload and key in container:
            payload[key] = deepcopy(container[key])


class AlignObjectsCommand:
    """Align several editable objects in one undoable document operation."""

    def __init__(self, object_ids: Sequence[str], mode: str):
        self.object_ids = tuple(str(value or "").strip() for value in object_ids if str(value or "").strip())
        self.mode = str(mode or "").strip().lower()

    def apply(self, document: dict) -> tuple[EditResult, object]:
        if self.mode not in {"left", "center", "right", "top", "middle", "bottom"}:
            return _failure("invalid_alignment", "Unsupported alignment mode."), None
        error, found = _batch_objects(document, self.object_ids)
        if error is not None:
            return error, None
        assert found is not None
        bounds = [(object_id, payload, _geometry_bounds(payload)) for object_id, payload in found]
        if any(item[2] is None for item in bounds):
            return _failure("invalid_geometry", "Every selected object needs editable bounds."), None
        snapshots = {"objects": deepcopy(_objects(document))}
        values = [item[2] for item in bounds]
        assert all(value is not None for value in values)
        target = {
            "left": min(value[1] for value in values),
            "center": (min(value[1] for value in values) + max(value[3] for value in values)) / 2,
            "right": max(value[3] for value in values),
            "top": min(value[2] for value in values),
            "middle": (min(value[2] for value in values) + max(value[4] for value in values)) / 2,
            "bottom": max(value[4] for value in values),
        }[self.mode]
        for _object_id, payload, geometry in bounds:
            assert geometry is not None
            anchor = {
                "left": geometry[1],
                "center": (geometry[1] + geometry[3]) / 2,
                "right": geometry[3],
                "top": geometry[2],
                "middle": (geometry[2] + geometry[4]) / 2,
                "bottom": geometry[4],
            }[self.mode]
            delta = target - anchor
            _shift_geometry(payload, geometry[0], delta if self.mode in {"left", "center", "right"} else 0.0, delta if self.mode in {"top", "middle", "bottom"} else 0.0)
        if _objects(document) == snapshots["objects"]:
            return _noop(*self.object_ids, message="Objects are already aligned."), None
        return _success(*self.object_ids), snapshots

    def revert(self, document: dict, snapshot: object) -> EditResult:
        objects = _objects(document)
        if objects is None or not isinstance(snapshot, dict) or not isinstance(snapshot.get("objects"), list):
            return _failure("invalid_snapshot", "The alignment snapshot is invalid.", *self.object_ids)
        if objects == snapshot["objects"]:
            return _noop(*self.object_ids, message="Alignment is already restored.")
        objects[:] = deepcopy(snapshot["objects"])
        return _success(*self.object_ids)


class DistributeObjectsCommand:
    """Distribute three or more editable objects with equal bounding-box gaps."""

    def __init__(self, object_ids: Sequence[str], mode: str):
        self.object_ids = tuple(str(value or "").strip() for value in object_ids if str(value or "").strip())
        self.mode = str(mode or "").strip().lower()

    def apply(self, document: dict) -> tuple[EditResult, object]:
        if self.mode not in {"horizontal", "vertical"}:
            return _failure("invalid_distribution", "Unsupported distribution mode."), None
        if len(tuple(dict.fromkeys(self.object_ids))) < 3:
            return _failure(
                "selection_required",
                "At least three objects are required for distribution.",
                *self.object_ids,
            ), None
        error, found = _batch_objects(document, self.object_ids)
        if error is not None:
            return error, None
        assert found is not None
        measured = [(object_id, payload, _geometry_bounds(payload)) for object_id, payload in found]
        if any(item[2] is None for item in measured):
            return _failure(
                "invalid_geometry",
                "Every selected object needs editable bounds.",
                *self.object_ids,
            ), None

        snapshots = {"objects": deepcopy(_objects(document))}
        axis_index = 1 if self.mode == "horizontal" else 2
        end_index = 3 if self.mode == "horizontal" else 4
        ordered = sorted(measured, key=lambda item: item[2][axis_index])
        outer_start = ordered[0][2][axis_index]
        outer_end = max(item[2][end_index] for item in ordered)
        total_size = sum(item[2][end_index] - item[2][axis_index] for item in ordered)
        gap = (outer_end - outer_start - total_size) / (len(ordered) - 1)
        cursor = outer_start
        for _object_id, payload, geometry in ordered:
            current_start = geometry[axis_index]
            delta = cursor - current_start
            _shift_geometry(
                payload,
                geometry[0],
                delta if self.mode == "horizontal" else 0.0,
                delta if self.mode == "vertical" else 0.0,
            )
            cursor += geometry[end_index] - current_start + gap

        if _objects(document) == snapshots["objects"]:
            return _noop(*self.object_ids, message="Objects are already distributed."), None
        return _success(*self.object_ids), snapshots

    def revert(self, document: dict, snapshot: object) -> EditResult:
        objects = _objects(document)
        if objects is None or not isinstance(snapshot, dict) or not isinstance(snapshot.get("objects"), list):
            return _failure("invalid_snapshot", "The distribution snapshot is invalid.", *self.object_ids)
        if objects == snapshot["objects"]:
            return _noop(*self.object_ids, message="Distribution is already restored.")
        objects[:] = deepcopy(snapshot["objects"])
        return _success(*self.object_ids)


class GroupObjectsCommand:
    def __init__(self, object_ids: Sequence[str], group_id: str | None = None):
        self.object_ids = tuple(str(value or "").strip() for value in object_ids if str(value or "").strip())
        self.group_id = str(group_id or f"group-{uuid4().hex[:10]}")

    def apply(self, document: dict) -> tuple[EditResult, object]:
        error, found = _batch_objects(document, self.object_ids)
        if error is not None:
            return error, None
        assert found is not None
        snapshots = {"objects": deepcopy(_objects(document))}
        for _object_id, payload in found:
            payload["group_id"] = self.group_id
        if _objects(document) == snapshots["objects"]:
            return _noop(*self.object_ids, message="Objects are already grouped."), None
        return _success(*self.object_ids), snapshots

    def revert(self, document: dict, snapshot: object) -> EditResult:
        objects = _objects(document)
        if objects is None or not isinstance(snapshot, dict) or not isinstance(snapshot.get("objects"), list):
            return _failure("invalid_snapshot", "The group snapshot is invalid.", *self.object_ids)
        objects[:] = deepcopy(snapshot["objects"])
        return _success(*self.object_ids)


class UngroupObjectsCommand:
    def __init__(self, object_ids: Sequence[str]):
        self.object_ids = tuple(str(value or "").strip() for value in object_ids if str(value or "").strip())

    def apply(self, document: dict) -> tuple[EditResult, object]:
        error, found = _batch_objects(document, self.object_ids)
        if error is not None:
            return error, None
        assert found is not None
        if not any("group_id" in payload for _object_id, payload in found):
            return _noop(*self.object_ids, message="No selected object belongs to a group."), None
        snapshot = {"objects": deepcopy(_objects(document))}
        for _object_id, payload in found:
            payload.pop("group_id", None)
        return _success(*self.object_ids), snapshot

    def revert(self, document: dict, snapshot: object) -> EditResult:
        objects = _objects(document)
        if objects is None or not isinstance(snapshot, dict) or not isinstance(snapshot.get("objects"), list):
            return _failure("invalid_snapshot", "The ungroup snapshot is invalid.", *self.object_ids)
        objects[:] = deepcopy(snapshot["objects"])
        return _success(*self.object_ids)


class PasteObjectCommand:
    def __init__(
        self,
        object_payload: dict | str | None = None,
        *,
        source_id: str | None = None,
        new_object_id: str | None = None,
        object_id: str | None = None,
        index: int | None = None,
    ):
        self.object_payload = deepcopy(object_payload)
        self.source_id = str(source_id or "").strip()
        self.new_object_id = str(
            new_object_id if new_object_id is not None else (object_id or "")
        ).strip()
        self.index = index

    def _source(self, document: dict) -> dict | None:
        if isinstance(self.object_payload, dict):
            return deepcopy(self.object_payload)
        source_id = self.source_id or (
            str(self.object_payload).strip() if isinstance(self.object_payload, str) else ""
        )
        found = _find_object(document, source_id)
        return deepcopy(found[1]) if found is not None else None

    def apply(self, document: dict) -> tuple[EditResult, object]:
        source = self._source(document)
        if source is None:
            return _failure("object_not_found", "The object to paste was not found."), None
        objects = _objects(document)
        if objects is None and isinstance(document, dict) and "objects" not in document:
            objects = []
        if objects is None:
            return _failure("invalid_document", "Document objects must be a list."), None
        original_id = _object_id(source)
        if not original_id and not self.new_object_id:
            return _failure("invalid_payload", "The pasted object requires an id."), None
        target_id = self.new_object_id or f"{original_id}-copy"
        if not target_id:
            return _failure("invalid_payload", "The pasted object requires an id."), None
        if not self.new_object_id:
            suffix = 2
            candidate = target_id
            while _find_object(document, candidate) is not None:
                candidate = f"{original_id}-copy-{suffix}"
                suffix += 1
            target_id = candidate
        elif _find_object(document, target_id) is not None:
            return _failure("object_exists", f"Object '{target_id}' already exists.", target_id), None
        pasted = deepcopy(source)
        pasted["id"] = target_id
        insertion_index = len(objects) if self.index is None else self.index
        if isinstance(insertion_index, bool) or not isinstance(insertion_index, int):
            return _failure("invalid_index", "The insertion index must be an integer.", target_id), None
        if not 0 <= insertion_index <= len(objects):
            return _failure("invalid_index", "The insertion index is outside the object list.", target_id), None
        if "objects" not in document:
            document["objects"] = objects
        objects.insert(insertion_index, pasted)
        return _success(target_id), {"index": insertion_index, "object": pasted}

    def revert(self, document: dict, snapshot: object) -> EditResult:
        if not isinstance(snapshot, dict) or not isinstance(snapshot.get("object"), dict):
            return _failure("invalid_snapshot", "The paste snapshot is invalid.")
        object_id = _object_id(snapshot["object"])
        found = _find_object(document, object_id)
        if found is None:
            return _failure("object_not_found", f"Object '{object_id}' was not found.", object_id)
        objects = _objects(document)
        assert objects is not None
        del objects[found[0]]
        return _success(object_id)


class CropCanvasCommand:
    def __init__(
        self,
        crop: Mapping[str, Any] | Sequence[Any] | str | None = None,
        *args: object,
        object_id: str | None = None,
        bounds: Mapping[str, Any] | Sequence[Any] | None = None,
    ):
        if isinstance(crop, str) and args and object_id is None:
            object_id = crop
            crop = args[0] if len(args) == 1 else None
        self.crop = deepcopy(bounds if bounds is not None else crop)
        self.object_id = str(object_id or "").strip()

    @staticmethod
    def _normalized_crop(value: object) -> dict | None:
        if isinstance(value, Mapping):
            candidate = dict(value)
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and len(value) == 4:
            candidate = dict(zip(("x", "y", "width", "height"), value))
        else:
            return None
        required = ("x", "y", "width", "height")
        if any(key not in candidate or not _valid_number(candidate[key]) for key in required):
            return None
        if float(candidate["width"]) <= 0 or float(candidate["height"]) <= 0:
            return None
        return deepcopy(candidate)

    def apply(self, document: dict) -> tuple[EditResult, object]:
        if not isinstance(document, dict):
            return _failure("invalid_document", "The figure document must be a mapping."), None
        crop = self._normalized_crop(self.crop)
        if crop is None:
            return _failure("invalid_crop", "Crop bounds must contain finite x, y, width, and height."), None
        if self.object_id:
            error, _ = _editable_object(document, self.object_id, "crop", allow_locked_crop=True)
            if error is not None:
                return error, None
        canvas = document.get("canvas") if isinstance(document, dict) else None
        if canvas is None:
            canvas = {}
        if not isinstance(canvas, dict):
            return _failure("invalid_document", "Document canvas must be a mapping."), None
        if canvas.get("crop") == crop:
            return _noop(self.object_id, message="Canvas already has the requested crop."), None
        snapshot = {"had_canvas": "canvas" in document, "canvas": deepcopy(canvas)}
        if "canvas" not in document:
            document["canvas"] = canvas
        document["canvas"]["crop"] = crop
        return _success(self.object_id, message="Canvas crop updated."), snapshot

    def revert(self, document: dict, snapshot: object) -> EditResult:
        if not isinstance(snapshot, dict) or "had_canvas" not in snapshot:
            return _failure("invalid_snapshot", "The crop snapshot is invalid.")
        if not bool(snapshot["had_canvas"]):
            if "canvas" not in document:
                return _noop(message="Canvas crop is already restored.")
            document.pop("canvas", None)
            return _success(self.object_id, message="Canvas crop restored.")
        old_canvas = snapshot.get("canvas")
        if not isinstance(old_canvas, dict):
            return _failure("invalid_snapshot", "The crop canvas snapshot is invalid.")
        if document.get("canvas") == old_canvas:
            return _noop(self.object_id, message="Canvas crop is already restored.")
        document["canvas"] = deepcopy(old_canvas)
        return _success(self.object_id, message="Canvas crop restored.")


__all__ = [
    "AddObjectCommand",
    "AlignObjectsCommand",
    "DistributeObjectsCommand",
    "CropCanvasCommand",
    "DeleteObjectCommand",
    "EditCommand",
    "EditResult",
    "MoveLayerCommand",
    "GroupObjectsCommand",
    "PasteObjectCommand",
    "SetLockCommand",
    "ReplaceObjectCommand",
    "ReplaceDocumentCommand",
    "SetVisibilityCommand",
    "UngroupObjectsCommand",
    "UpdateGeometryCommand",
    "UpdatePlotSeriesDataCommand",
    "UpdateStyleCommand",
    "UpdateTextCommand",
]
