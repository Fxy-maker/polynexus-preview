"""Frozen, JSON-safe contracts for deterministic direct analysis runs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, fields, is_dataclass
from hashlib import sha256
import json
import math
from numbers import Real
from pathlib import Path
from types import MappingProxyType
from typing import Any


COMPUTE_STATUSES = frozenset({"ready", "needs_input", "failed", "completed"})


def _freeze_json(value: Any) -> Any:
    """Validate and recursively freeze values accepted by the public contracts."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Real):
        numeric_value = float(value)
        if not math.isfinite(numeric_value):
            raise ValueError("Compute contracts reject non-finite floats")
        return numeric_value
    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("Compute contract mapping keys must be strings")
            frozen[key] = _freeze_json(item)
        return MappingProxyType(frozen)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(_freeze_json(item) for item in value)
    raise TypeError(f"Unsupported compute contract value: {type(value).__name__}")


def _freeze_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    frozen = _freeze_json({} if value is None else value)
    if not isinstance(frozen, Mapping):
        raise TypeError("Expected a mapping")
    return frozen


def _json_value(value: Any) -> Any:
    """Return a fresh standard-library JSON value from a frozen contract value."""
    if is_dataclass(value):
        return {field_info.name: _json_value(getattr(value, field_info.name)) for field_info in fields(value)}
    if isinstance(value, Mapping):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    return value


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(
        _json_value(_freeze_json(value)),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _directory_manifest_sha256(path: Path) -> str:
    entries = [
        {"path": child.relative_to(path).as_posix(), "sha256": _file_sha256(child)}
        for child in sorted(path.rglob("*"), key=lambda item: item.relative_to(path).as_posix())
        if child.is_file()
    ]
    return _canonical_hash({"kind": "directory_manifest", "entries": entries})


def _artifact_format(path: Path) -> str:
    return "directory" if path.is_dir() else path.suffix.removeprefix(".").lower() or "unknown"


@dataclass(frozen=True)
class RawArtifact:
    """A content-addressed raw input or an unresolved candidate reference."""

    artifact_id: str
    path: str
    technique: str
    format: str
    sha256: str
    observed_facts: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "observed_facts", _freeze_mapping(self.observed_facts))

    @classmethod
    def from_path(
        cls,
        path: str | Path,
        *,
        technique: str,
        observed_facts: Mapping[str, Any] | None = None,
    ) -> RawArtifact:
        source = Path(path).expanduser().resolve(strict=True)
        content_hash = _directory_manifest_sha256(source) if source.is_dir() else _file_sha256(source)
        artifact_format = _artifact_format(source)
        frozen_facts = _freeze_mapping(observed_facts)
        artifact_id = _canonical_hash(
            {
                "kind": "raw_artifact",
                "path": str(source),
                "technique": technique,
                "format": artifact_format,
                "sha256": content_hash,
                "observed_facts": frozen_facts,
            }
        )
        return cls(
            artifact_id=artifact_id,
            path=str(source),
            technique=technique,
            format=artifact_format,
            sha256=content_hash,
            observed_facts=frozen_facts,
        )

    @classmethod
    def missing(cls, path: str | Path, *, technique: str) -> RawArtifact:
        candidate = Path(path).expanduser().resolve(strict=False)
        artifact_format = _artifact_format(candidate)
        artifact_id = _canonical_hash(
            {
                "kind": "missing_raw_artifact",
                "path": str(candidate),
                "technique": technique,
                "format": artifact_format,
            }
        )
        return cls(
            artifact_id=artifact_id,
            path=str(candidate),
            technique=technique,
            format=artifact_format,
            sha256="",
            observed_facts={},
        )


@dataclass(frozen=True)
class CanonicalDataset:
    """A canonical dataset envelope with an explicit raw-artifact provenance link."""

    dataset_id: str
    source_artifact_id: str
    technique: str
    template_id: str
    payload: Mapping[str, Any]
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", _freeze_mapping(self.payload))
        object.__setattr__(self, "warnings", tuple(str(item) for item in self.warnings))

    @classmethod
    def direct_envelope(cls, artifact: RawArtifact) -> CanonicalDataset:
        if not artifact.sha256:
            raise ValueError("A direct envelope requires an artifact content hash")
        if artifact.format == "directory":
            raise ValueError("A direct envelope requires a raw file artifact")
        template_id = "direct_raw_file_v1"
        payload = {
            "kind": "raw_file",
            "path": artifact.path,
            "format": artifact.format,
            "sha256": artifact.sha256,
            "observed_facts": artifact.observed_facts,
        }
        dataset_id = _canonical_hash(
            {
                "kind": "canonical_dataset",
                "source_artifact_id": artifact.artifact_id,
                "technique": artifact.technique,
                "template_id": template_id,
                "payload": payload,
                "warnings": (),
            }
        )
        return cls(
            dataset_id=dataset_id,
            source_artifact_id=artifact.artifact_id,
            technique=artifact.technique,
            template_id=template_id,
            payload=payload,
        )


@dataclass(frozen=True)
class AnalysisPlan:
    """An immutable request to execute a direct analysis against a dataset."""

    plan_id: str
    dataset_id: str
    technique: str
    output_dir: str
    pipeline_options: Mapping[str, Any]
    parameter_sources: Mapping[str, str]

    def __post_init__(self) -> None:
        frozen_options = _freeze_mapping(self.pipeline_options)
        frozen_sources = _freeze_mapping(self.parameter_sources)
        if any(not isinstance(value, str) for value in frozen_sources.values()):
            raise TypeError("Analysis plan parameter sources must be strings")
        object.__setattr__(self, "pipeline_options", frozen_options)
        object.__setattr__(self, "parameter_sources", frozen_sources)

    @classmethod
    def direct(
        cls,
        dataset: CanonicalDataset,
        *,
        output_dir: str | Path,
        pipeline_options: Mapping[str, Any] | None = None,
    ) -> AnalysisPlan:
        options = _freeze_mapping(pipeline_options)
        parameter_sources = {name: "user" for name in options}
        rendered_output_dir = str(Path(output_dir).expanduser().resolve(strict=False))
        plan_id = _canonical_hash(
            {
                "kind": "direct_analysis_plan",
                "dataset_id": dataset.dataset_id,
                "technique": dataset.technique,
                "output_dir": rendered_output_dir,
                "pipeline_options": options,
                "parameter_sources": parameter_sources,
            }
        )
        return cls(
            plan_id=plan_id,
            dataset_id=dataset.dataset_id,
            technique=dataset.technique,
            output_dir=rendered_output_dir,
            pipeline_options=options,
            parameter_sources=parameter_sources,
        )


@dataclass(frozen=True)
class ComputeResult:
    """JSON-safe direct projection of calculated metrics and display assets."""

    metrics: Mapping[str, Any] = field(default_factory=dict)
    figures: Mapping[str, str] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        frozen_metrics = _freeze_mapping(self.metrics)
        frozen_figures = _freeze_mapping(self.figures)
        if any(not isinstance(value, str) for value in frozen_figures.values()):
            raise TypeError("Compute result figure references must be strings")
        object.__setattr__(self, "metrics", frozen_metrics)
        object.__setattr__(self, "figures", frozen_figures)
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))
        object.__setattr__(self, "warnings", tuple(str(item) for item in self.warnings))

    @classmethod
    def from_legacy_result(cls, value: Any) -> ComputeResult:
        metrics = getattr(value, "parameters", {})
        figures = getattr(value, "figures", {})
        metadata = getattr(value, "metadata", {})
        validation_warnings = getattr(value, "validation_warnings", ())
        quality_flags = getattr(value, "quality_flags", {})
        validation_summary = getattr(value, "validation_summary", "")

        warnings = [str(item) for item in validation_warnings]
        if isinstance(quality_flags, Mapping):
            warnings.extend(
                f"quality_flag:{name}:{flag}"
                for name, flag in quality_flags.items()
                if str(flag).upper() != "OK"
            )
        if validation_summary and str(validation_summary) != "All checks passed":
            warnings.append(str(validation_summary))
        return cls(
            metrics=metrics if isinstance(metrics, Mapping) else {},
            figures=figures if isinstance(figures, Mapping) else {},
            metadata=metadata if isinstance(metadata, Mapping) else {},
            warnings=tuple(warnings),
        )


@dataclass(frozen=True)
class ComputeRun:
    """The complete direct-run record shared by later CLI and GUI routes."""

    status: str
    artifact: RawArtifact
    dataset: CanonicalDataset | None = None
    plan: AnalysisPlan | None = None
    result: ComputeResult | None = None
    reasons: tuple[str, ...] = ()
    legacy_result: Any = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.status not in COMPUTE_STATUSES:
            raise ValueError(f"Unsupported compute status: {self.status}")
        object.__setattr__(self, "reasons", tuple(str(item) for item in self.reasons))
        has_execution_context = self.dataset is not None or self.plan is not None
        if self.status == "completed":
            if self.dataset is None or self.plan is None or self.result is None:
                raise ValueError("Completed compute runs require dataset, plan, and result")
        elif self.status == "ready":
            if self.dataset is None or self.plan is None or self.result is not None:
                raise ValueError("Ready compute runs require dataset and plan without a result")
        elif has_execution_context or self.result is not None:
            raise ValueError(f"{self.status} compute runs cannot include dataset, plan, or result")

    @classmethod
    def completed(
        cls,
        *,
        artifact: RawArtifact,
        dataset: CanonicalDataset,
        plan: AnalysisPlan,
        result: ComputeResult,
        reasons: tuple[str, ...] = (),
        legacy_result: Any = None,
    ) -> ComputeRun:
        return cls(
            status="completed",
            artifact=artifact,
            dataset=dataset,
            plan=plan,
            result=result,
            reasons=reasons,
            legacy_result=legacy_result,
        )

    def to_dict(self) -> dict[str, Any]:
        return _json_value(
            {
                field_info.name: getattr(self, field_info.name)
                for field_info in fields(self)
                if field_info.name != "legacy_result"
            }
        )
