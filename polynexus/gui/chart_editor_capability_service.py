"""Pure capability descriptors for the chart editor's visible mode contract."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EditorCapabilityDescriptor:
    """What a user can safely do in one editor surface."""

    mode_key: str
    capability_key: str
    editable_objects: bool
    annotations: bool
    crop: bool
    export: bool


_DESCRIPTORS = {
    "EDITOR_MODE_OBJECT": EditorCapabilityDescriptor(
        "EDITOR_MODE_OBJECT",
        "EDITOR_CAPABILITIES_OBJECT",
        editable_objects=True,
        annotations=True,
        crop=False,
        export=True,
    ),
    "EDITOR_MODE_STATIC": EditorCapabilityDescriptor(
        "EDITOR_MODE_STATIC",
        "EDITOR_CAPABILITIES_STATIC",
        editable_objects=False,
        annotations=True,
        crop=True,
        export=True,
    ),
    "EDITOR_MODE_PREVIEW": EditorCapabilityDescriptor(
        "EDITOR_MODE_PREVIEW",
        "EDITOR_CAPABILITIES_PREVIEW",
        editable_objects=False,
        annotations=False,
        crop=False,
        export=True,
    ),
}


def descriptor_for_editor_mode(mode_key: str) -> EditorCapabilityDescriptor | None:
    return _DESCRIPTORS.get(str(mode_key or "").strip())


__all__ = ["EditorCapabilityDescriptor", "descriptor_for_editor_mode"]
