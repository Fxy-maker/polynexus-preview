"""Stable, JSON-safe contracts for the optional Suite runtime."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class SuiteComponent:
    component_id: str
    version: str
    destination: str
    required_files: tuple[str, ...]
    source: str
    sha256: str
    core_range: str = ""
    handoff_schema: str = "v1"

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["required_files"] = list(self.required_files)
        return value


@dataclass(frozen=True)
class SuiteManifest:
    schema_version: int
    components: tuple[SuiteComponent, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "components": [item.to_dict() for item in self.components],
        }


@dataclass(frozen=True)
class SuiteComponentStatus:
    component_id: str
    status: str
    version: str = ""
    destination: str = ""
    reason_codes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["reason_codes"] = list(self.reason_codes)
        return value


@dataclass(frozen=True)
class SuiteStatus:
    status: str
    codex_skills_dir: str
    core_version: str
    components: tuple[SuiteComponentStatus, ...] = ()
    reason_codes: tuple[str, ...] = ()
    codex_home: str = ""
    codex_detected: bool = False

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["components"] = [item.to_dict() for item in self.components]
        value["reason_codes"] = list(self.reason_codes)
        return value
