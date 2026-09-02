"""Frozen, JSON-safe contracts for deterministic direct analysis runs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, fields, is_dataclass, replace
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
from .method_sensitivity import MethodSensitivity, sensitivities_from_metrics
from .capability_catalog import default_capability_catalog


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


def _coerce_computation_state(value: Any):
    """Normalize the shared four-axis state without importing the AI package eagerly."""

    if value is None:
        return None
    # Importing the leaf module keeps the compute package independent from the
    # AI-platform execution helpers (which may themselves be imported by
    # callers during application startup).
    from ..ai_platform.contracts import ComputationState

    if type(value) is ComputationState:
        return value
    if isinstance(value, ComputationState):
        # The public state DTO is a trust-boundary value.  A subclass may
        # override ``to_dict`` or axis accessors after construction, so
        # accepting it here would let polymorphic state bypass the canonical
        # status checks performed by ComputeResult/ComputeRun.
        raise TypeError(
            "computation_state must use the exact ComputationState type or mapping"
        )
    if isinstance(value, Mapping):
        return ComputationState.from_dict(value)
    raise TypeError("computation_state must be a ComputationState or mapping")


def _coerce_projection_mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    """Freeze an optional JSON mapping used by cross-entry projections."""

    if value is None:
        return _freeze_mapping({})
    if hasattr(value, "to_dict") and not isinstance(value, Mapping):
        value = value.to_dict()
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    return _freeze_mapping(value)


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
    # Keep extensionless vendor inputs (for example an NMR ``fid`` file)
    # aligned with AgentWorkflow inspection, which records an empty format.
    return "directory" if path.is_dir() else path.suffix.removeprefix(".").lower()


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
    project_context: Mapping[str, Any] = field(default_factory=dict)
    project_context_sha256: str = ""

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
        context = _freeze_mapping(self.project_context)
        object.__setattr__(self, "project_context", context)
        context_hash = _canonical_hash(context)
        if self.project_context_sha256 and self.project_context_sha256 != context_hash:
            raise ValueError("Analysis plan project context hash does not match its content")
        object.__setattr__(self, "project_context_sha256", context_hash)

    @classmethod
    def direct(
        cls,
        dataset: CanonicalDataset,
        *,
        output_dir: str | Path,
        pipeline_options: Mapping[str, Any] | None = None,
        project_context: Mapping[str, Any] | None = None,
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
                "project_context": project_context or {},
            }
        )
        return cls(
            plan_id=plan_id,
            dataset_id=dataset.dataset_id,
            technique=dataset.technique,
            output_dir=rendered_output_dir,
            pipeline_options=options,
            parameter_sources=parameter_sources,
            project_context=project_context or {},
        )


@dataclass(frozen=True)
class ComputeResult:
    """JSON-safe direct projection of calculated metrics and display assets."""

    metrics: Mapping[str, Any] = field(default_factory=dict)
    figures: Mapping[str, str] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    method_sensitivities: tuple[MethodSensitivity, ...] = ()
    # Optional shared AI-platform projection fields.  They are appended after
    # the historical fields so positional provider callers remain compatible.
    descriptor_id: str | None = None
    computation_state: Any = None
    provenance: Mapping[str, Any] = field(default_factory=dict)
    uncertainty: Mapping[str, Any] = field(default_factory=dict)

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
        object.__setattr__(self, "method_sensitivities", tuple(self.method_sensitivities))
        if not all(isinstance(item, MethodSensitivity) for item in self.method_sensitivities):
            raise TypeError("method_sensitivities must contain MethodSensitivity values")
        if self.descriptor_id is not None:
            if not isinstance(self.descriptor_id, str) or not self.descriptor_id.strip():
                raise ValueError("descriptor_id must be a non-empty string or null")
            object.__setattr__(self, "descriptor_id", self.descriptor_id.strip())
        object.__setattr__(self, "computation_state", _coerce_computation_state(self.computation_state))
        object.__setattr__(
            self,
            "provenance",
            _coerce_projection_mapping(self.provenance, "provenance"),
        )
        object.__setattr__(
            self,
            "uncertainty",
            _coerce_projection_mapping(self.uncertainty, "uncertainty"),
        )

    @property
    def state(self):
        """Short compatibility alias for callers using ``result.state``."""

        return self.computation_state

    def to_public_dict(self, *, source: str | None = None) -> dict[str, Any]:
        """Return the complete JSON-safe result projection."""
        payload = {
            "metrics": _json_value(self.metrics),
            "figures": _json_value(self.figures),
            "metadata": _json_value(self.metadata),
            "warnings": list(self.warnings),
            "field_inventory": list(self.field_inventory()),
            "metric_manifest": list(self.metric_manifest(source=source)),
            "method_sensitivities": [item.to_dict() for item in self.method_sensitivities],
        }
        if self.descriptor_id is not None:
            payload["descriptor_id"] = self.descriptor_id
        if self.computation_state is not None:
            payload["computation_state"] = self.computation_state.to_dict()
        if self.provenance:
            payload["provenance"] = _json_value(self.provenance)
        if self.uncertainty:
            payload["uncertainty"] = _json_value(self.uncertainty)
        return payload

    def field_inventory(self) -> tuple[dict[str, Any], ...]:
        """Return a JSON-safe inventory of every emitted metric field."""
        from .result_inventory import build_result_field_inventory

        return tuple(
            field.to_dict() for field in build_result_field_inventory(self.metrics)
        )

    def metric_manifest(self, *, source: str | None = None) -> tuple[dict[str, Any], ...]:
        """Expose every result leaf with uniform provenance metadata."""
        inventory = self.field_inventory()
        units = self.metadata.get("units", {})
        methods = self.metadata.get("methods", self.metadata.get("method", {}))
        parameters = self.metadata.get("parameters", {})
        source_value = source
        if source_value is None:
            source_value = self.metadata.get("source", self.metadata.get("source_file"))
        warnings = list(self.warnings)
        state = self.computation_state
        state_payload = state.to_dict() if state is not None else None
        manifest: list[dict[str, Any]] = []
        for item in inventory:
            path = str(item["path"])
            present = bool(item.get("present", True))
            computability = state.computability if state is not None else None
            # A discovered scalar whose value is ``None`` is an explicit
            # unavailable result, even when the enclosing provider completed.
            # Keeping this distinction in the shared manifest prevents
            # downstream contracts from treating missing optional metrics as
            # computed values.
            value_available = present and not (
                item.get("kind") == "scalar" and item.get("value") is None
            )
            if not value_available:
                status = "unavailable"
            elif computability in (None, "computed"):
                status = "computed"
            elif computability is not None:
                status = computability
            else:
                status = "unavailable"
            record = {
                "path": path,
                "kind": item["kind"],
                "unit": _json_value(_metadata_for_path(units, path)),
                "method": _json_value(_metadata_for_path(methods, path)),
                "parameters": _json_value(_metadata_for_path(parameters, path) or {}),
                "source": source_value,
                "warnings": warnings,
                "status": status,
            }
            if self.descriptor_id is not None:
                record["descriptor_id"] = self.descriptor_id
            if state_payload is not None:
                record["computation_state"] = state_payload
            provenance = _metric_projection(self.provenance, path)
            if provenance is not None:
                record["provenance"] = _json_value(provenance)
            uncertainty = _metric_projection(self.uncertainty, path)
            if uncertainty is not None:
                record["uncertainty"] = _json_value(uncertainty)
            if item["kind"] == "scalar" and status == "computed":
                record["value"] = item.get("value")
            elif item["kind"] == "series" and status == "computed":
                record["item_count"] = item.get("item_count", 0)
            manifest.append(record)
        return tuple(manifest)

    def metric_manifest_csv_rows(self, *, source: str | None = None) -> tuple[dict[str, Any], ...]:
        """Return one flat row per result leaf for deterministic CSV export."""
        rows: list[dict[str, Any]] = []
        for item in self.metric_manifest(source=source):
            row = dict(item)
            row["parameters"] = json.dumps(
                row.get("parameters", {}), ensure_ascii=False, sort_keys=True
            )
            row["warnings"] = ";".join(str(value) for value in row.get("warnings", ()))
            rows.append(row)
        return tuple(rows)

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
        normalized_metrics = metrics if isinstance(metrics, Mapping) else {}
        # Providers may expose the shared fields directly, while older
        # providers occasionally place them in metadata.  Read only these
        # explicit keys; never infer a descriptor from a technique name.
        descriptor_id = _safe_public_attr(value, "descriptor_id")
        direct_computation_state = _safe_public_attr(value, "computation_state")
        direct_state_alias = _safe_public_attr(value, "state")
        metadata_computation_state = None
        metadata_state_alias = None
        provenance = _safe_public_attr(value, "provenance")
        uncertainty = _safe_public_attr(value, "uncertainty")
        if isinstance(metadata, Mapping):
            if descriptor_id is None:
                descriptor_id = metadata.get("descriptor_id")
            metadata_computation_state = metadata.get("computation_state")
            metadata_state_alias = metadata.get("state")
            if provenance is None:
                provenance = metadata.get("provenance")
            if uncertainty is None:
                uncertainty = metadata.get("uncertainty")
        # Legacy providers often use a free-form metadata ``state`` string or
        # a provider-private partial mapping.  Only an explicit shared
        # four-axis state may cross this boundary; malformed values are
        # ignored rather than allowed to make a legacy result unparsable.
        computation_state = _first_legacy_computation_state(
            direct_computation_state,
            metadata_computation_state,
            direct_state_alias,
            metadata_state_alias,
        )
        declared_items = getattr(value, "method_sensitivities", ())
        declared_sensitivities = tuple(
            item for item in declared_items if isinstance(item, MethodSensitivity)
        ) if isinstance(declared_items, (list, tuple)) else ()
        if not declared_sensitivities and isinstance(declared_items, (list, tuple)):
            converted: list[MethodSensitivity] = []
            for item in declared_items:
                if not isinstance(item, Mapping):
                    continue
                primary = item.get("primary", {})
                if not isinstance(primary, Mapping):
                    continue
                candidates = item.get("candidates", ())
                candidate_values = {
                    str(candidate.get("method", "candidate")): candidate.get("value")
                    for candidate in candidates
                    if isinstance(candidate, Mapping)
                } if isinstance(candidates, (list, tuple)) else candidates
                converted.append(MethodSensitivity.create(
                    metric_path=item.get("metric_path", ""),
                    primary_method=primary.get("method", "explicit"),
                    primary_value=primary.get("value"),
                    candidates=candidate_values if isinstance(candidate_values, Mapping) else {},
                    parameters=item.get("parameters", {}),
                    source=item.get("source"),
                    warnings=tuple(item.get("warnings", ())),
                ))
            declared_sensitivities = tuple(converted)
        if not declared_sensitivities:
            declared_sensitivities = sensitivities_from_metrics(
                normalized_metrics,
                technique=str(getattr(value, "technique", "")),
                source=(metadata.get("source") if isinstance(metadata, Mapping) else None),
            )
        return cls(
            metrics=normalized_metrics,
            figures=figures if isinstance(figures, Mapping) else {},
            metadata=metadata if isinstance(metadata, Mapping) else {},
            warnings=tuple(warnings),
            method_sensitivities=declared_sensitivities,
            descriptor_id=descriptor_id,
            computation_state=computation_state,
            provenance=provenance if isinstance(provenance, Mapping) else {},
            uncertainty=uncertainty if isinstance(uncertainty, Mapping) else {},
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
    provider_capability_items: tuple[CapabilityItemResult, ...] = ()
    reasons: tuple[str, ...] = ()
    legacy_result: Any = field(default=None, repr=False, compare=False)
    # Shared AI-platform fields are optional and appended after the historical
    # constructor arguments to preserve positional compatibility.
    descriptor_id: str | None = None
    computation_state: Any = None
    provenance: Mapping[str, Any] = field(default_factory=dict)
    uncertainty: Mapping[str, Any] = field(default_factory=dict)

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
        object.__setattr__(self, "provider_capability_items", tuple(self.provider_capability_items))
        if not all(isinstance(item, CapabilityItemResult) for item in self.provider_capability_items):
            raise TypeError("provider_capability_items must contain CapabilityItemResult values")
        object.__setattr__(self, "reasons", _freeze_strings(self.reasons, "reasons"))
        if self.descriptor_id is not None:
            if not isinstance(self.descriptor_id, str) or not self.descriptor_id.strip():
                raise ValueError("descriptor_id must be a non-empty string or null")
            object.__setattr__(self, "descriptor_id", self.descriptor_id.strip())
        state = _coerce_computation_state(self.computation_state)
        descriptor_id = self.descriptor_id
        provenance = _coerce_projection_mapping(self.provenance, "provenance")
        uncertainty = _coerce_projection_mapping(self.uncertainty, "uncertainty")
        # A run may receive the fields either at the run envelope or result
        # level.  Normalize both to one shared projection and reject explicit
        # disagreements rather than silently choosing one.
        if self.result is not None:
            result_state = self.result.computation_state
            if state is not None and result_state is not None and state.to_dict() != result_state.to_dict():
                raise ValueError("Compute run and result computation_state do not match")
            state = state or result_state
            result_descriptor = self.result.descriptor_id
            if descriptor_id is not None and result_descriptor is not None and descriptor_id != result_descriptor:
                raise ValueError("Compute run and result descriptor_id do not match")
            descriptor_id = descriptor_id or result_descriptor
            # Provenance and uncertainty are shared identity-bearing
            # projections just like the state and descriptor.  When both the
            # run envelope and nested result provide a non-empty mapping,
            # silently choosing one would let two entry points publish
            # contradictory scientific lineage.  Empty mappings remain the
            # backwards-compatible "not supplied" sentinel and are filled
            # from the other projection when available.
            result_provenance = self.result.provenance
            if provenance and result_provenance and provenance != result_provenance:
                raise ValueError("Compute run and result provenance do not match")
            result_uncertainty = self.result.uncertainty
            if uncertainty and result_uncertainty and uncertainty != result_uncertainty:
                raise ValueError("Compute run and result uncertainty do not match")
            if not provenance and self.result.provenance:
                provenance = self.result.provenance
            if not uncertainty and self.result.uncertainty:
                uncertainty = self.result.uncertainty

        if state is None:
            state = _default_computation_state(
                self.status,
                artifact=self.artifact,
                dataset=self.dataset,
                reasons=self.reasons,
            )
        expected_computability = {
            "completed": "computed",
            "needs_input": "needs_input",
            "failed": "failed",
            "ready": "blocked",
        }[self.status]
        if state.computability != expected_computability:
            raise ValueError(
                f"Compute run status {self.status!r} requires computation_state "
                f"computability {expected_computability!r}"
            )
        if self.result is not None and (
            self.result.computation_state is not state
            or self.result.descriptor_id != descriptor_id
            or self.result.provenance != provenance
            or self.result.uncertainty != uncertainty
        ):
            # Ensure the result's metric manifest carries exactly the same
            # fields as the enclosing run consumed by every entry point.
            self_result = replace(
                self.result,
                descriptor_id=descriptor_id,
                computation_state=state,
                provenance=provenance,
                uncertainty=uncertainty,
            )
            object.__setattr__(self, "result", self_result)
        object.__setattr__(self, "descriptor_id", descriptor_id)
        object.__setattr__(self, "computation_state", state)
        object.__setattr__(self, "provenance", provenance)
        object.__setattr__(self, "uncertainty", uncertainty)
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
        provider_capability_items: tuple[CapabilityItemResult, ...] = (),
        reasons: tuple[str, ...] = (),
        legacy_result: Any = None,
        descriptor_id: str | None = None,
        computation_state: Any = None,
        provenance: Mapping[str, Any] | None = None,
        uncertainty: Mapping[str, Any] | None = None,
    ) -> ComputeRun:
        return cls(
            status="completed",
            artifact=artifact,
            dataset=dataset,
            plan=plan,
            result=result,
            canonical_template=canonical_template,
            capability_items=capability_items,
            provider_capability_items=provider_capability_items,
            reasons=reasons,
            legacy_result=legacy_result,
            descriptor_id=descriptor_id,
            computation_state=computation_state,
            provenance={} if provenance is None else provenance,
            uncertainty={} if uncertainty is None else uncertainty,
        )

    def to_dict(self) -> dict[str, Any]:
        optional_names = {"descriptor_id", "computation_state", "provenance", "uncertainty"}
        raw_payload = {}
        for field_info in fields(self):
            if field_info.name == "legacy_result":
                continue
            value = getattr(self, field_info.name)
            if field_info.name in optional_names and value in (None, {}):
                continue
            raw_payload[field_info.name] = value
        payload = _json_value(raw_payload)
        if self.result is not None:
            payload["result"]["field_inventory"] = list(self.result.field_inventory())
            payload["result"]["metric_manifest"] = list(self.result.metric_manifest(source=self.artifact.path))
            sensitivities = []
            for item in self.result.method_sensitivities:
                record = item.to_dict()
                if record.get("source") is None:
                    record["source"] = self.artifact.path
                sensitivities.append(record)
            payload["result"]["method_sensitivities"] = sensitivities
            payload["result"]["capability_catalog"] = [
                item.to_dict() for item in default_capability_catalog().for_technique(self.artifact.technique)
            ]
        return payload


def _metadata_for_path(value: Any, path: str) -> Any:
    if isinstance(value, Mapping):
        if path in value:
            return value[path]
        current: Any = value
        for part in path.split("."):
            if not isinstance(current, Mapping) or part not in current:
                return None
            current = current[part]
        return current
    return value if value not in (None, "") else None


def _metric_projection(value: Any, path: str) -> Any:
    """Resolve a per-metric projection, falling back to global metadata."""

    if value in (None, {}):
        return None
    exact = _metadata_for_path(value, path)
    if exact is not None:
        return exact
    if isinstance(value, Mapping):
        for key in ("*", "default", "global"):
            if key in value and value[key] not in (None, ""):
                return value[key]
    # A provenance mapping normally describes the whole result (for example
    # source_artifact_id/algorithm_id), so retain it when no path-specific
    # entry exists.  This is intentionally not used for empty mappings.
    return value


def _safe_public_attr(value: Any, name: str) -> Any:
    """Read an optional provider attribute without making it mandatory."""

    try:
        return getattr(value, name, None)
    except Exception:
        return None


_COMPUTATION_STATE_AXES = frozenset(
    {"data_availability", "computability", "validity", "promotion"}
)


def _coerce_legacy_computation_state(value: Any):
    """Accept only a validated shared four-axis state from legacy objects."""

    from ..ai_platform.contracts import ComputationState

    if type(value) is ComputationState:
        return value
    if isinstance(value, ComputationState):
        # Explicit legacy state values are still authoritative.  Do not
        # silently discard a polymorphic value and derive a permissive default
        # state from the provider's status.
        raise TypeError(
            "legacy computation_state must use the exact ComputationState type"
        )
    if not isinstance(value, Mapping):
        return None
    # A provider ``state`` mapping with a status/error field is not the shared
    # contract.  Require all four named axes before invoking its strict parser.
    if not _COMPUTATION_STATE_AXES.issubset(value.keys()):
        return None
    try:
        return ComputationState.from_dict(value)
    except (KeyError, TypeError, ValueError):
        return None


def _first_legacy_computation_state(*values: Any):
    """Return the first valid state, preferring explicit contract names."""

    for value in values:
        normalized = _coerce_legacy_computation_state(value)
        if normalized is not None:
            return normalized
    return None


def _default_computation_state(
    status: str,
    *,
    artifact: RawArtifact,
    dataset: CanonicalDataset | None,
    reasons: Sequence[str],
):
    """Build a conservative state for legacy runs that supplied no state."""

    from ..ai_platform.contracts import ComputationState

    availability = "canonical" if dataset is not None else "raw" if artifact.sha256 else "missing"
    if status == "completed":
        computability = "computed"
        validity = "diagnostic"
        promotion = "diagnostic_only"
    elif status == "needs_input":
        computability = "needs_input"
        validity = "not_assessed"
        promotion = "diagnostic_only"
    elif status == "failed":
        computability = "failed"
        validity = "not_assessed"
        promotion = "diagnostic_only"
    else:  # ready is a planned, not-yet-executed run.
        computability = "blocked"
        validity = "not_assessed"
        promotion = "diagnostic_only"
    return ComputationState.create(
        data_availability=availability,
        computability=computability,
        validity=validity,
        promotion=promotion,
        reason_codes=tuple(str(reason) for reason in reasons),
    )
