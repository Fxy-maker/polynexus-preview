"""Frozen, JSON-safe contracts for deterministic direct analysis runs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, fields, is_dataclass
from hashlib import sha256
import json
import math
from numbers import Real
import os
from pathlib import Path
import re
import stat
from types import MappingProxyType
from typing import Any

from ..artifacts import directory_manifest_entries, directory_manifest_sha256, raw_artifact_id
from ..canonical_experiments.models import CanonicalExperiment, CapabilityItemResult


COMPUTE_STATUSES = frozenset({"ready", "needs_input", "failed", "completed"})
_FORBIDDEN_COMPUTE_RESULT_KEY_NAMES = frozenset(
    {
        "analysis_evidence",
        "evidence",
        "evidence_package",
        "writing_eligibility",
        "writing_status",
        "manuscript_role",
        "manuscript_candidate",
        "manuscript_status",
        "review_required",
        "review_notes",
    }
)


def _string_value(value: Any, field_name: str, *, allow_empty: bool = False) -> str:
    if isinstance(value, Path):
        value = str(value)
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string or path")
    if not allow_empty and not value:
        raise ValueError(f"{field_name} must not be empty")
    return value


def _freeze_strings(value: Sequence[str] | None, field_name: str) -> tuple[str, ...]:
    if (
        value is None
        or isinstance(value, (str, bytes, bytearray))
        or not isinstance(value, Sequence)
    ):
        raise TypeError(f"{field_name} must be a sequence of strings")
    return tuple(_string_value(item, f"{field_name} item") for item in value)


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


def _normalized_compute_key(value: str) -> str:
    camel_separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return "_".join(camel_separated.casefold().replace("-", "_").replace("_", " ").split())


def _is_forbidden_compute_result_key(key: object) -> bool:
    if not isinstance(key, str):
        return False
    # Exact aliases preserve valid compute fields such as preview and chart_preview.
    return _normalized_compute_key(key) in _FORBIDDEN_COMPUTE_RESULT_KEY_NAMES


def _normalized_technique(value: str) -> str:
    return " ".join(value.casefold().split())


def _scrub_compute_result_projection(value: Any) -> Any:
    """Remove non-compute fields from the public compute-only result projection.

    This boundary applies only to ``ComputeResult`` public fields, never raw
    artifact facts or canonical dataset payloads that retain scientific metadata.
    """
    if isinstance(value, Mapping):
        return {
            key: _scrub_compute_result_projection(item)
            for key, item in value.items()
            if not _is_forbidden_compute_result_key(key)
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(_scrub_compute_result_projection(item) for item in value)
    return value


def _json_value(value: Any) -> Any:
    """Return a fresh standard-library JSON value from a frozen contract value."""
    if is_dataclass(value):
        return {
            field_info.name: _json_value(getattr(value, field_info.name))
            for field_info in fields(value)
        }
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


def _is_reparse_point(path_stat: os.stat_result) -> bool:
    reparse_point = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(getattr(path_stat, "st_file_attributes", 0) & reparse_point)


def _directory_manifest_sha256(path: Path) -> str:
    try:
        return directory_manifest_sha256(directory_manifest_entries(path))
    except OSError as exc:
        raise ValueError(str(exc)) from exc


def _artifact_format(path: Path) -> str:
    return "directory" if path.is_dir() else path.suffix.removeprefix(".").lower() or "unknown"


def _invalid_path_marker(path: object) -> str:
    try:
        type_name = type(path).__name__
    except Exception:
        type_name = "unknown"
    return f"<invalid-path:{type_name}>"


def _safe_path_reference(path: object) -> str:
    """Return a stable JSON-safe path reference without exposing object reprs."""
    if isinstance(path, str):
        return path
    try:
        path_value = os.fspath(path)
    except Exception:
        return _invalid_path_marker(path)
    return path_value if isinstance(path_value, str) else _invalid_path_marker(path)


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
        object.__setattr__(self, "artifact_id", _string_value(self.artifact_id, "artifact_id"))
        object.__setattr__(self, "path", _string_value(self.path, "path"))
        object.__setattr__(self, "technique", _string_value(self.technique, "technique"))
        object.__setattr__(self, "format", _string_value(self.format, "format", allow_empty=True))
        object.__setattr__(self, "sha256", _string_value(self.sha256, "sha256", allow_empty=True))
        object.__setattr__(self, "observed_facts", _freeze_mapping(self.observed_facts))

    @classmethod
    def from_path(
        cls,
        path: str | Path,
        *,
        technique: str,
        observed_facts: Mapping[str, Any] | None = None,
    ) -> RawArtifact:
        unresolved_source = Path(path).expanduser()
        unresolved_stat = unresolved_source.lstat()
        if unresolved_source.is_symlink() or _is_reparse_point(unresolved_stat):
            raise ValueError("Raw artifact paths reject a symlink or reparse point")
        source = unresolved_source.resolve(strict=True)
        content_hash = (
            _directory_manifest_sha256(source) if source.is_dir() else _file_sha256(source)
        )
        artifact_format = _artifact_format(source)
        frozen_facts = _freeze_mapping(observed_facts)
        artifact_id = raw_artifact_id(
            source,
            technique=technique,
            format=artifact_format,
            sha256=content_hash,
            observed_facts=frozen_facts,
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
    def missing(cls, path: object, *, technique: str) -> RawArtifact:
        try:
            candidate = Path(path).expanduser()
            candidate_stat = candidate.lstat()
            if candidate.is_symlink() or _is_reparse_point(candidate_stat):
                artifact_path = str(candidate)
                artifact_format = ""
            else:
                candidate = candidate.resolve(strict=False)
                artifact_path = str(candidate)
                artifact_format = _artifact_format(candidate)
        except FileNotFoundError:
            candidate = Path(path).expanduser().resolve(strict=False)
            artifact_path = str(candidate)
            artifact_format = _artifact_format(candidate)
        except Exception:
            artifact_path = _safe_path_reference(path)
            artifact_format = ""
        artifact_id = _canonical_hash(
            {
                "kind": "missing_raw_artifact",
                "path": artifact_path,
                "technique": technique,
                "format": artifact_format,
            }
        )
        return cls(
            artifact_id=artifact_id,
            path=artifact_path,
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
        object.__setattr__(self, "dataset_id", _string_value(self.dataset_id, "dataset_id"))
        object.__setattr__(
            self, "source_artifact_id", _string_value(self.source_artifact_id, "source_artifact_id")
        )
        object.__setattr__(self, "technique", _string_value(self.technique, "technique"))
        object.__setattr__(self, "template_id", _string_value(self.template_id, "template_id"))
        object.__setattr__(self, "payload", _freeze_mapping(self.payload))
        object.__setattr__(self, "warnings", _freeze_strings(self.warnings, "warnings"))

    @classmethod
    def direct_envelope(cls, artifact: RawArtifact) -> CanonicalDataset:
        if not artifact.sha256:
            raise ValueError("A direct envelope requires an artifact content hash")
        is_directory = artifact.format == "directory"
        template_id = "raw-directory-envelope.v1" if is_directory else "raw-file-envelope.v1"
        payload = {
            "kind": "raw_directory" if is_directory else "raw_file",
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
        object.__setattr__(self, "plan_id", _string_value(self.plan_id, "plan_id"))
        object.__setattr__(self, "dataset_id", _string_value(self.dataset_id, "dataset_id"))
        object.__setattr__(self, "technique", _string_value(self.technique, "technique"))
        object.__setattr__(self, "output_dir", _string_value(self.output_dir, "output_dir"))
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
        frozen_metrics = _freeze_mapping(_scrub_compute_result_projection(self.metrics))
        frozen_figures = _freeze_mapping(_scrub_compute_result_projection(self.figures))
        if any(not isinstance(value, str) for value in frozen_figures.values()):
            raise TypeError("Compute result figure references must be strings")
        object.__setattr__(self, "metrics", frozen_metrics)
        object.__setattr__(self, "figures", frozen_figures)
        object.__setattr__(
            self,
            "metadata",
            _freeze_mapping(_scrub_compute_result_projection(self.metadata)),
        )
        object.__setattr__(self, "warnings", _freeze_strings(self.warnings, "warnings"))

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
    canonical_template: CanonicalExperiment | None = None
    capability_items: tuple[CapabilityItemResult, ...] = ()
    reasons: tuple[str, ...] = ()
    legacy_result: Any = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.status, str):
            raise TypeError("status must be a string")
        if self.status not in COMPUTE_STATUSES:
            raise ValueError(f"Unsupported compute status: {self.status}")
        if not isinstance(self.artifact, RawArtifact):
            raise TypeError("artifact must be a RawArtifact")
        if self.dataset is not None and not isinstance(self.dataset, CanonicalDataset):
            raise TypeError("dataset must be a CanonicalDataset")
        if self.plan is not None and not isinstance(self.plan, AnalysisPlan):
            raise TypeError("plan must be an AnalysisPlan")
        if self.result is not None and not isinstance(self.result, ComputeResult):
            raise TypeError("result must be a ComputeResult")
        if self.canonical_template is not None and not isinstance(
            self.canonical_template, CanonicalExperiment
        ):
            raise TypeError("canonical_template must be a CanonicalExperiment")
        object.__setattr__(self, "capability_items", tuple(self.capability_items))
        if not all(isinstance(item, CapabilityItemResult) for item in self.capability_items):
            raise TypeError("capability_items must contain CapabilityItemResult values")
        object.__setattr__(self, "reasons", _freeze_strings(self.reasons, "reasons"))
        if self.dataset is not None and self.plan is not None:
            linkage_mismatches: list[str] = []
            if self.artifact.artifact_id != self.dataset.source_artifact_id:
                linkage_mismatches.append("artifact/dataset")
            if self.plan.dataset_id != self.dataset.dataset_id:
                linkage_mismatches.append("plan/dataset")
            if _normalized_technique(self.plan.technique) != _normalized_technique(
                self.dataset.technique
            ):
                linkage_mismatches.append("plan/dataset technique")
            if _normalized_technique(self.artifact.technique) != _normalized_technique(
                self.dataset.technique
            ):
                linkage_mismatches.append("artifact/dataset technique")
            if linkage_mismatches:
                raise ValueError(
                    "Compute run provenance linkage mismatch: " + ", ".join(linkage_mismatches)
                )
        if self.canonical_template is not None:
            if self.canonical_template.source_artifact_id != self.artifact.artifact_id:
                raise ValueError("Compute run canonical template must use the run artifact")
            if _normalized_technique(self.canonical_template.payload.get("technique", self.artifact.technique)) != _normalized_technique(self.artifact.technique):
                raise ValueError("Compute run canonical template technique mismatch")
        has_execution_context = self.dataset is not None or self.plan is not None
        if self.status == "completed":
            if self.dataset is None or self.plan is None or self.result is None:
                raise ValueError("Completed compute runs require dataset, plan, and result")
        elif self.status == "ready":
            if self.dataset is None or self.plan is None or self.result is not None or self.capability_items:
                raise ValueError("Ready compute runs require dataset and plan without a result")
        elif self.status == "failed":
            if self.result is not None or (
                self.capability_items and self.canonical_template is None
            ):
                raise ValueError("Failed compute runs cannot include a result")
            if (self.dataset is None) != (self.plan is None):
                raise ValueError(
                    "Failed compute runs require both dataset and plan when retaining provenance"
                )
        elif has_execution_context or self.result is not None or self.capability_items:
            raise ValueError(f"{self.status} compute runs cannot include dataset, plan, or result")

    @classmethod
    def completed(
        cls,
        *,
        artifact: RawArtifact,
        dataset: CanonicalDataset,
        plan: AnalysisPlan,
        result: ComputeResult,
        canonical_template: CanonicalExperiment | None = None,
        capability_items: tuple[CapabilityItemResult, ...] = (),
        reasons: tuple[str, ...] = (),
        legacy_result: Any = None,
    ) -> ComputeRun:
        return cls(
            status="completed",
            artifact=artifact,
            dataset=dataset,
            plan=plan,
            result=result,
            canonical_template=canonical_template,
            capability_items=capability_items,
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
