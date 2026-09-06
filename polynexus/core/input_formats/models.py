"""Immutable contracts for layered raw-format inspection."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import hashlib
import json
import math
from types import MappingProxyType
from typing import Any


FORMAT_INSPECTION_STATUSES = frozenset(
    {"ready", "needs_mapping", "needs_reader", "unknown", "blocked"}
)
READER_AVAILABILITY = frozenset({"available", "missing", "external", "unknown"})
CANONICAL_CONVERSION_STATES = frozenset(
    {"candidate", "available", "unavailable", "blocked"}
)
SCIENTIFIC_MAPPING_STATES = frozenset({"unassessed", "observed", "confirmed"})


def _public(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Format contracts reject non-finite floats")
        return value
    if isinstance(value, Mapping):
        return {str(key): _public(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_public(item) for item in value]
    raise TypeError(f"Unsupported format contract value: {type(value).__name__}")


def _freeze(value: Any) -> Any:
    public = _public(value)
    if isinstance(public, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in public.items()})
    if isinstance(public, list):
        return tuple(_freeze(item) for item in public)
    return public


def _hash(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(
        _public(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _strings(value: Sequence[str], name: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes, bytearray)):
        raise TypeError(f"{name} must be a sequence of strings")
    normalized = tuple(str(item) for item in value)
    if any(not item for item in normalized):
        raise ValueError(f"{name} items must not be empty")
    return normalized


@dataclass(frozen=True)
class FormatPluginDescriptor:
    """Declarative reader capability; it never loads executable plugin code."""

    plugin_id: str
    version: str
    container_kind: str
    techniques: tuple[str, ...]
    extensions: tuple[str, ...]
    reader_availability: str
    canonical_conversion: str
    next_actions: tuple[str, ...] = ()
    description: str = ""

    def __post_init__(self) -> None:
        for name in ("plugin_id", "version", "container_kind"):
            value = str(getattr(self, name)).strip()
            if not value:
                raise ValueError(f"{name} must not be empty")
            object.__setattr__(self, name, value)
        object.__setattr__(self, "techniques", _strings(self.techniques, "techniques"))
        object.__setattr__(
            self,
            "extensions",
            tuple(
                sorted(
                    {
                        str(item).strip().casefold()
                        if str(item).strip().startswith(".")
                        else f".{str(item).strip().casefold()}"
                        for item in self.extensions
                    }
                )
            ),
        )
        if self.reader_availability not in READER_AVAILABILITY:
            raise ValueError("Unsupported reader availability")
        if self.canonical_conversion not in CANONICAL_CONVERSION_STATES:
            raise ValueError("Unsupported canonical conversion state")
        object.__setattr__(self, "next_actions", _strings(self.next_actions, "next_actions"))
        object.__setattr__(self, "description", str(self.description))

    def to_dict(self) -> dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "version": self.version,
            "container_kind": self.container_kind,
            "techniques": list(self.techniques),
            "extensions": list(self.extensions),
            "reader_availability": self.reader_availability,
            "canonical_conversion": self.canonical_conversion,
            "next_actions": list(self.next_actions),
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> FormatPluginDescriptor:
        if not isinstance(payload, Mapping):
            raise TypeError("Format plugin descriptor must be a mapping")
        return cls(
            plugin_id=str(payload["plugin_id"]),
            version=str(payload["version"]),
            container_kind=str(payload["container_kind"]),
            techniques=tuple(payload.get("techniques", ())),
            extensions=tuple(payload.get("extensions", ())),
            reader_availability=str(payload["reader_availability"]),
            canonical_conversion=str(payload["canonical_conversion"]),
            next_actions=tuple(payload.get("next_actions", ())),
            description=str(payload.get("description", "")),
        )


@dataclass(frozen=True)
class FormatInspection:
    """A content-bound, deterministic projection of raw-format readiness."""

    inspection_id: str
    source_sha256: str
    source_kind: str
    declared_technique: str
    extension: str
    container_kind: str
    status: str
    plugin_id: str | None
    reader_availability: str
    canonical_conversion: str
    scientific_mapping: str = "unassessed"
    observed_facts: Mapping[str, Any] = field(default_factory=dict)
    reason_codes: tuple[str, ...] = ()
    next_actions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "source_sha256",
            "source_kind",
            "declared_technique",
            "extension",
            "container_kind",
        ):
            object.__setattr__(self, name, str(getattr(self, name)))
        if self.status not in FORMAT_INSPECTION_STATUSES:
            raise ValueError("Unsupported format inspection status")
        if self.reader_availability not in READER_AVAILABILITY:
            raise ValueError("Unsupported reader availability")
        if self.canonical_conversion not in CANONICAL_CONVERSION_STATES:
            raise ValueError("Unsupported canonical conversion state")
        if self.scientific_mapping not in SCIENTIFIC_MAPPING_STATES:
            raise ValueError("Unsupported scientific mapping state")
        if self.plugin_id is not None:
            plugin_id = str(self.plugin_id).strip()
            if not plugin_id:
                raise ValueError("plugin_id must be non-empty or null")
            object.__setattr__(self, "plugin_id", plugin_id)
        object.__setattr__(self, "observed_facts", _freeze(self.observed_facts))
        object.__setattr__(self, "reason_codes", _strings(self.reason_codes, "reason_codes"))
        object.__setattr__(self, "next_actions", _strings(self.next_actions, "next_actions"))
        expected = _hash(self._identity_payload())
        if self.inspection_id != expected:
            raise ValueError("Format inspection ID does not match its content")

    @classmethod
    def create(cls, **values: Any) -> FormatInspection:
        identity = {
            "source_sha256": str(values.get("source_sha256", "")),
            "source_kind": str(values["source_kind"]),
            "declared_technique": str(values.get("declared_technique", "unknown")),
            "extension": str(values.get("extension", "")),
            "container_kind": str(values["container_kind"]),
            "status": str(values["status"]),
            "plugin_id": values.get("plugin_id"),
            "reader_availability": str(values["reader_availability"]),
            "canonical_conversion": str(values["canonical_conversion"]),
            "scientific_mapping": str(values.get("scientific_mapping", "unassessed")),
            "observed_facts": values.get("observed_facts", {}),
            "reason_codes": tuple(values.get("reason_codes", ())),
            "next_actions": tuple(values.get("next_actions", ())),
        }
        return cls(inspection_id=_hash(identity), **identity)

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "source_sha256": self.source_sha256,
            "source_kind": self.source_kind,
            "declared_technique": self.declared_technique,
            "extension": self.extension,
            "container_kind": self.container_kind,
            "status": self.status,
            "plugin_id": self.plugin_id,
            "reader_availability": self.reader_availability,
            "canonical_conversion": self.canonical_conversion,
            "scientific_mapping": self.scientific_mapping,
            "observed_facts": self.observed_facts,
            "reason_codes": self.reason_codes,
            "next_actions": self.next_actions,
        }

    def to_dict(self) -> dict[str, Any]:
        return {"inspection_id": self.inspection_id, **_public(self._identity_payload())}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> FormatInspection:
        if not isinstance(payload, Mapping):
            raise TypeError("Format inspection must be a mapping")
        return cls(
            inspection_id=str(payload["inspection_id"]),
            source_sha256=str(payload.get("source_sha256", "")),
            source_kind=str(payload["source_kind"]),
            declared_technique=str(payload.get("declared_technique", "unknown")),
            extension=str(payload.get("extension", "")),
            container_kind=str(payload["container_kind"]),
            status=str(payload["status"]),
            plugin_id=(str(payload["plugin_id"]) if payload.get("plugin_id") is not None else None),
            reader_availability=str(payload["reader_availability"]),
            canonical_conversion=str(payload["canonical_conversion"]),
            scientific_mapping=str(payload.get("scientific_mapping", "unassessed")),
            observed_facts=payload.get("observed_facts", {}),
            reason_codes=tuple(payload.get("reason_codes", ())),
            next_actions=tuple(payload.get("next_actions", ())),
        )
