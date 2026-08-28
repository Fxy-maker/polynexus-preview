"""Technique-neutral inventory of fields emitted by deterministic results."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from numbers import Real
from typing import Any


@dataclass(frozen=True)
class ResultField:
    """One discoverable result field, without changing its provider value."""

    path: str
    kind: str
    present: bool = True
    value: Any = None
    item_count: int | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "path": self.path,
            "kind": self.kind,
            "present": self.present,
        }
        if self.kind == "scalar" and self.present:
            payload["value"] = self.value
        if self.kind == "series" and self.present:
            payload["item_count"] = self.item_count or 0
        return payload


def build_result_field_inventory(
    metrics: Mapping[str, Any],
    *,
    declared_paths: Sequence[str] = (),
) -> tuple[ResultField, ...]:
    """List scalar/series leaves and explicitly declared missing fields.

    This is an observation of an already-computed result. It performs no
    numerical calculation and deliberately does not infer units or scientific
    meaning from field names.
    """

    if not isinstance(metrics, Mapping):
        raise TypeError("result metrics must be a mapping")
    declared = tuple(str(path).strip() for path in declared_paths)
    if any(not path for path in declared):
        raise ValueError("declared result field paths must not be empty")

    fields: dict[str, ResultField] = {}

    def walk(value: Any, path: str) -> None:
        if isinstance(value, Mapping):
            if not value:
                fields[path] = ResultField(path=path, kind="object")
                return
            for key, child in value.items():
                key_text = str(key).strip()
                if not key_text:
                    continue
                walk(child, f"{path}.{key_text}" if path else key_text)
            return
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            fields[path] = ResultField(path=path, kind="series", item_count=len(value))
            return
        if isinstance(value, (str, bool, Real)) or value is None:
            fields[path] = ResultField(path=path, kind="scalar", value=value)
            return
        fields[path] = ResultField(path=path, kind="object")

    for key, value in metrics.items():
        key_text = str(key).strip()
        if key_text:
            walk(value, key_text)

    for path in declared:
        if path not in fields:
            fields[path] = ResultField(path=path, kind="missing", present=False)
    return tuple(fields[path] for path in sorted(fields))


__all__ = ["ResultField", "build_result_field_inventory"]
