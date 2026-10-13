"""Canonical admission contracts for exploration inputs.

Exploration requests are not allowed to invent a source identity.  This module
turns an already validated canonical object plus its content-addressed raw
artifact into a small immutable admission record that can be checked again by
the runner and persisted with the request.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from polynexus.core.ai_platform.capabilities import normalize_technique
from polynexus.core.ai_platform.contracts import canonical_json_hash
from polynexus.core.canonical_experiments.models import CanonicalExperiment
from polynexus.core.compute.models import CanonicalDataset, RawArtifact


def _sha256(value: object, label: str) -> str:
    text = str(value).strip().lower()
    if len(text) != 64 or any(char not in "0123456789abcdef" for char in text):
        raise ValueError(f"{label} must be a 64-character hexadecimal SHA-256")
    return text


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _freeze(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _public(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _public(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_public(item) for item in value]
    if isinstance(value, list):
        return [_public(item) for item in value]
    return value


@dataclass(frozen=True)
class CanonicalAdmission:
    """Content-addressed admission for one validated canonical input."""

    canonical_kind: str
    canonical_id: str
    template_id: str
    source_artifact_id: str
    source_content_hash: str
    technique: str
    canonical_content_hash: str
    axis_provenance: Mapping[str, Any] = field(default_factory=dict)
    calibration_identity: Mapping[str, Any] = field(default_factory=dict)
    dependency_ids: tuple[str, ...] = ()
    admission_hash: str = ""
    schema_version: str = "1"

    SCHEMA_VERSION = "1"

    def __post_init__(self) -> None:
        if self.schema_version != self.SCHEMA_VERSION:
            raise ValueError("Unsupported canonical admission schema_version")
        if self.canonical_kind not in {"dataset", "experiment"}:
            raise ValueError("canonical_kind must be dataset or experiment")
        for name in ("canonical_id", "template_id", "source_artifact_id"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} must be nonempty")
        object.__setattr__(self, "source_content_hash", _sha256(self.source_content_hash, "source_content_hash"))
        object.__setattr__(self, "canonical_content_hash", _sha256(self.canonical_content_hash, "canonical_content_hash"))
        technique = normalize_technique(self.technique)
        if not technique:
            raise ValueError("canonical admission technique must be nonempty")
        object.__setattr__(self, "technique", technique)
        if not isinstance(self.axis_provenance, Mapping):
            raise TypeError("axis_provenance must be a mapping")
        if not isinstance(self.calibration_identity, Mapping):
            raise TypeError("calibration_identity must be a mapping")
        object.__setattr__(self, "axis_provenance", _freeze(self.axis_provenance))
        object.__setattr__(self, "calibration_identity", _freeze(self.calibration_identity))
        if isinstance(self.dependency_ids, (str, bytes, bytearray)):
            raise TypeError("dependency_ids must be a sequence")
        dependencies = tuple(dict.fromkeys(str(item).strip() for item in self.dependency_ids))
        if any(not item for item in dependencies):
            raise ValueError("dependency_ids must contain nonempty IDs")
        object.__setattr__(self, "dependency_ids", dependencies)
        expected = canonical_json_hash(self._identity_payload())
        if self.admission_hash and self.admission_hash != expected:
            raise ValueError("canonical admission hash does not match its content")
        object.__setattr__(self, "admission_hash", expected)

    @classmethod
    def from_objects(
        cls,
        canonical: CanonicalDataset | CanonicalExperiment,
        raw_artifact: RawArtifact,
        *,
        axis_provenance: Mapping[str, Any] | None = None,
        calibration_identity: Mapping[str, Any] | None = None,
        dependency_ids: Sequence[str] = (),
    ) -> "CanonicalAdmission":
        if type(raw_artifact) is not RawArtifact:
            raise TypeError("canonical admission requires the exact RawArtifact type")
        if not raw_artifact.sha256:
            raise ValueError("canonical admission requires a hashed raw artifact")
        if type(canonical) is CanonicalDataset:
            kind = "dataset"
            canonical_id = canonical.dataset_id
            template_id = canonical.template_id
            source_artifact_id = canonical.source_artifact_id
            technique = canonical.technique
            canonical_hash = canonical.dataset_id
        elif type(canonical) is CanonicalExperiment:
            kind = "experiment"
            canonical_id = canonical.content_hash
            template_id = canonical.template_id
            source_artifact_id = canonical.source_artifact_id
            technique = canonical.payload.get("technique", raw_artifact.technique)
            canonical_hash = canonical.content_hash
        else:
            raise TypeError("canonical admission requires CanonicalDataset or CanonicalExperiment")
        if source_artifact_id != raw_artifact.artifact_id:
            raise ValueError("canonical source artifact does not match raw artifact")
        if normalize_technique(technique) != normalize_technique(raw_artifact.technique):
            raise ValueError("canonical technique does not match raw artifact")
        return cls(
            canonical_kind=kind,
            canonical_id=str(canonical_id),
            template_id=str(template_id),
            source_artifact_id=str(raw_artifact.artifact_id),
            source_content_hash=str(raw_artifact.sha256),
            technique=str(technique),
            canonical_content_hash=str(canonical_hash),
            axis_provenance={} if axis_provenance is None else axis_provenance,
            calibration_identity={} if calibration_identity is None else calibration_identity,
            dependency_ids=tuple(dependency_ids),
        )

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "canonical_kind": self.canonical_kind,
            "canonical_id": self.canonical_id,
            "template_id": self.template_id,
            "source_artifact_id": self.source_artifact_id,
            "source_content_hash": self.source_content_hash,
            "technique": self.technique,
            "canonical_content_hash": self.canonical_content_hash,
            "axis_provenance": _public(self.axis_provenance),
            "calibration_identity": _public(self.calibration_identity),
            "dependency_ids": list(self.dependency_ids),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._identity_payload(), "admission_hash": self.admission_hash}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CanonicalAdmission":
        if not isinstance(value, Mapping):
            raise TypeError("canonical admission must be a mapping")
        return cls(
            canonical_kind=value["canonical_kind"],
            canonical_id=value["canonical_id"],
            template_id=value["template_id"],
            source_artifact_id=value["source_artifact_id"],
            source_content_hash=value["source_content_hash"],
            technique=value["technique"],
            canonical_content_hash=value["canonical_content_hash"],
            axis_provenance=value.get("axis_provenance", {}),
            calibration_identity=value.get("calibration_identity", {}),
            dependency_ids=tuple(value.get("dependency_ids", ())),
            admission_hash=value.get("admission_hash", ""),
            schema_version=value.get("schema_version", ""),
        )


class CanonicalAdmissionRegistry:
    """Small immutable-by-identity registry used by the runner admission gate."""

    def __init__(self, admissions: Sequence[CanonicalAdmission] = ()) -> None:
        self._by_id: dict[str, CanonicalAdmission] = {}
        for admission in admissions:
            self.register(admission)

    def register(self, admission: CanonicalAdmission) -> None:
        if type(admission) is not CanonicalAdmission:
            raise TypeError("canonical admission registry requires exact CanonicalAdmission values")
        existing = self._by_id.get(admission.admission_hash)
        if existing is not None and existing != admission:
            raise ValueError("canonical admission identity is already registered")
        self._by_id[admission.admission_hash] = admission

    def resolve(self, admission_hash: str) -> CanonicalAdmission | None:
        return self._by_id.get(str(admission_hash))

    @property
    def admissions(self) -> tuple[CanonicalAdmission, ...]:
        return tuple(self._by_id[key] for key in sorted(self._by_id))


__all__ = ["CanonicalAdmission", "CanonicalAdmissionRegistry"]
