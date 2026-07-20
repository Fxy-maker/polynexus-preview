"""Stable document and asset-manifest differences for figure comparison."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class RevisionChange:
    path: str
    before: Any = None
    after: Any = None
    status: str = "changed"


@dataclass(frozen=True)
class RevisionDiff:
    document_changes: tuple[RevisionChange, ...] = ()
    asset_changes: tuple[RevisionChange, ...] = ()

    @property
    def changed(self) -> bool:
        return bool(self.document_changes or self.asset_changes)


_VOLATILE_KEYS = frozenset({"created_at", "updated_at"})


def _flatten(value: Any, path: str = "") -> dict[str, Any]:
    if isinstance(value, Mapping):
        result = {}
        for key in sorted(value, key=str):
            key_text = str(key)
            if key_text in _VOLATILE_KEYS:
                continue
            child_path = f"{path}.{key_text}" if path else key_text
            result.update(_flatten(value[key], child_path))
        return result
    if isinstance(value, (list, tuple)):
        result = {}
        for index, item in enumerate(value):
            result.update(_flatten(item, f"{path}[{index}]"))
        return result
    return {path: value}


def build_revision_diff(
    left_document: Mapping[str, Any],
    right_document: Mapping[str, Any],
    *,
    left_assets: Mapping[str, str] | None = None,
    right_assets: Mapping[str, str] | None = None,
) -> RevisionDiff:
    left = _flatten(left_document)
    right = _flatten(right_document)
    document_changes = tuple(
        RevisionChange(path, left.get(path), right.get(path))
        for path in sorted(set(left) | set(right))
        if left.get(path) != right.get(path)
    )

    left_assets = dict(left_assets or {})
    right_assets = dict(right_assets or {})
    asset_changes = []
    for path in sorted(set(left_assets) | set(right_assets)):
        if path not in left_assets:
            asset_changes.append(RevisionChange(path, None, right_assets[path], "added"))
        elif path not in right_assets:
            asset_changes.append(RevisionChange(path, left_assets[path], None, "removed"))
        elif left_assets[path] != right_assets[path]:
            asset_changes.append(
                RevisionChange(path, left_assets[path], right_assets[path], "changed")
            )
    return RevisionDiff(document_changes, tuple(asset_changes))


__all__ = ["RevisionChange", "RevisionDiff", "build_revision_diff"]
