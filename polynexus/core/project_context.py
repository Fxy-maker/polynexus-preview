"""Optional, project-local context supplied by Codex/ARS.

The context is deliberately small and non-authoritative.  It records explicit
parameters that a deterministic provider may consume; it never identifies a
material from filenames and never supplies scientific conclusions.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from types import MappingProxyType
from typing import Any


def _freeze(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("project_context_invalid")
        return value
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    raise ValueError("project_context_invalid")


def _public(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _public(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_public(item) for item in value]
    return value


def _hash(value: Mapping[str, Any]) -> str:
    payload = json.dumps(_public(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ProjectContext:
    """Validated optional project context with deterministic provenance."""

    snapshot: Mapping[str, Any]
    sha256: str
    source: str = "absent"

    def __post_init__(self) -> None:
        frozen = _freeze(self.snapshot)
        if not isinstance(frozen, Mapping):
            raise ValueError("project_context_invalid")
        object.__setattr__(self, "snapshot", frozen)
        expected = _hash(frozen)
        if self.sha256 and self.sha256 != expected:
            raise ValueError("project_context_invalid")
        object.__setattr__(self, "sha256", expected)
        object.__setattr__(self, "source", str(self.source))

    @classmethod
    def load(cls, value: object = None) -> "ProjectContext":
        if value is None:
            return cls({}, "", "absent")
        source = "mapping"
        payload: Any = value
        if isinstance(value, (str, Path)):
            path = Path(value).expanduser()
            if path.is_dir():
                path = path / ".polynexus" / "project-context.json"
            if not path.exists():
                return cls({}, "", "absent")
            source = str(path.resolve())
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                raise ValueError("project_context_invalid") from exc
        if not isinstance(payload, Mapping):
            raise ValueError("project_context_invalid")
        if payload and payload.get("schema") != "project-context.v1":
            raise ValueError("project_context_invalid")
        normalized = {str(key): item for key, item in payload.items()}
        if "material" in normalized and not isinstance(normalized["material"], Mapping):
            raise ValueError("project_context_invalid")
        techniques = normalized.get("techniques", {})
        if not isinstance(techniques, Mapping):
            raise ValueError("project_context_invalid")
        dsc = techniques.get("dsc", {})
        if dsc is not None and not isinstance(dsc, Mapping):
            raise ValueError("project_context_invalid")
        if isinstance(dsc, Mapping) and "reference_enthalpy_Jg" in dsc:
            value_jg = dsc["reference_enthalpy_Jg"]
            if isinstance(value_jg, bool) or not isinstance(value_jg, (int, float)) or not math.isfinite(float(value_jg)) or float(value_jg) <= 0:
                raise ValueError("project_context_invalid")
        frozen = _freeze(normalized)
        return cls(frozen, "", source)

    @property
    def dsc_reference_enthalpy(self) -> float | None:
        techniques = self.snapshot.get("techniques", {})
        dsc = techniques.get("dsc", {}) if isinstance(techniques, Mapping) else {}
        value = dsc.get("reference_enthalpy_Jg") if isinstance(dsc, Mapping) else None
        return None if value is None else float(value)

    @property
    def dsc_reference_source(self) -> str | None:
        techniques = self.snapshot.get("techniques", {})
        dsc = techniques.get("dsc", {}) if isinstance(techniques, Mapping) else {}
        value = dsc.get("reference_enthalpy_source") if isinstance(dsc, Mapping) else None
        return None if value in (None, "") else str(value)

    def to_dict(self) -> dict[str, Any]:
        return {"snapshot": _public(self.snapshot), "sha256": self.sha256, "source": self.source}
