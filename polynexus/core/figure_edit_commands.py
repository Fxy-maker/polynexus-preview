"""Atomic, document-only commands for Origin-style figure edits."""

from __future__ import annotations

import math
from copy import deepcopy
from collections.abc import Mapping, Sequence
from typing import Any

from .figure_edit_capabilities import (
    EditCommand,
    EditResult,
    capabilities_for,
    is_valid_color,
    is_known_object_type,
)


_UNSET = object()
_GEOMETRY_KEYS = {"x", "y", "width", "height", "x1", "y1", "x2", "y2", "left", "top"}
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
    "CropCanvasCommand",
    "DeleteObjectCommand",
    "EditCommand",
    "EditResult",
    "MoveLayerCommand",
    "PasteObjectCommand",
    "SetLockCommand",
    "SetVisibilityCommand",
    "UpdateGeometryCommand",
    "UpdateStyleCommand",
    "UpdateTextCommand",
]
