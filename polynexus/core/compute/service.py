"""Direct-run adapter from the public compute contracts to legacy engines."""

from __future__ import annotations

from collections.abc import Mapping
import json
import math
from pathlib import Path
from typing import Any, Callable

from ..engine import get_engine
from ..canonical_experiments import CapabilityExecutor, CanonicalExperiment, default_converter_registry
from .models import AnalysisPlan, CanonicalDataset, ComputeResult, ComputeRun, RawArtifact


_SUPPORTED_PIPELINE_OPTIONS = frozenset({"skip_to", "mask_edit_candidate"})
_SUPPORTED_SKIP_TO_VALUES = frozenset({"preprocess", "analyze", "plot"})


def _safe_technique(value: object) -> str | None:
    """Return one normalized technique string without coercing arbitrary objects."""
    if not isinstance(value, str):
        return None
    normalized = str.lower(str.strip(value))
    return normalized or None


def _resolve_output_dir(value: object) -> Path | None:
    """Return a canonical output path only when normalization is safe."""
    try:
        if "\x00" in str(value):
            return None
        return Path(value).expanduser().resolve(strict=False)
    except Exception:
        return None


def _normalize_pipeline_options(
    value: object,
) -> tuple[dict[str, Any] | None, str | None]:
    """Return supported JSON-safe direct-pipeline options or a public reason."""
    if value is None:
        return {}, None
    if not isinstance(value, Mapping):
        return None, "pipeline_option_invalid"
    try:
        options = dict(value)
        if any(name not in _SUPPORTED_PIPELINE_OPTIONS for name in options):
            return None, "pipeline_option_unsupported"
        skip_to = options.get("skip_to")
        if "skip_to" in options and not (
            skip_to is None
            or (isinstance(skip_to, str) and skip_to in _SUPPORTED_SKIP_TO_VALUES)
        ):
            return None, "pipeline_option_invalid"
        mask_edit_candidate = options.get("mask_edit_candidate")
        if "mask_edit_candidate" in options and not _is_json_safe(
            mask_edit_candidate
        ):
            return None, "pipeline_option_invalid"
        normalized: dict[str, Any] = {}
        if "skip_to" in options:
            normalized["skip_to"] = skip_to
        if "mask_edit_candidate" in options:
            normalized["mask_edit_candidate"] = mask_edit_candidate
        return normalized, None
    except Exception:
        return None, "pipeline_option_invalid"


def _is_json_safe(value: object) -> bool:
    """Return whether a pipeline option can be stored in an AnalysisPlan."""
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError, OverflowError, RecursionError):
        return False
    if isinstance(value, Mapping):
        try:
            return all(
                isinstance(key, str) and _is_json_safe(item)
                for key, item in value.items()
            )
        except Exception:
            return False
    if isinstance(value, list):
        return all(_is_json_safe(item) for item in value)
    return value is None or isinstance(value, (str, bool, int, float))


def _has_legacy_result_shape(value: Any) -> bool:
    """Return whether a provider result exposes the required legacy mappings."""
    if value is None:
        return False
    try:
        return all(
            isinstance(getattr(value, attribute), Mapping)
            for attribute in ("parameters", "figures", "metadata")
        )
    except Exception:
        return False


def _json_safe_projection(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe_projection(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe_projection(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


class ComputeRunService:
    """Create one canonical direct run and delegate its calculation to an engine."""

    def __init__(self, engine_factory: Callable[..., Any] = get_engine) -> None:
        self._engine_factory = engine_factory

    def run_direct(
        self,
        *,
        technique: object,
        path: object,
        output_dir: object,
        config: Any = None,
        submodule_id: str | None = None,
        engine: Any = None,
        pipeline_options: object = None,
        canonical_template: CanonicalExperiment | None = None,
    ) -> ComputeRun:
        normalized_technique = _safe_technique(technique)
        if normalized_technique is None:
            return ComputeRun(
                status="needs_input",
                artifact=RawArtifact.missing(path, technique="unknown"),
                reasons=("technique_invalid",),
            )
        try:
            artifact = RawArtifact.from_path(path, technique=normalized_technique)
        except FileNotFoundError:
            return ComputeRun(
                status="needs_input",
                artifact=RawArtifact.missing(path, technique=normalized_technique),
                reasons=("raw_artifact_missing",),
            )
        except Exception:
            return ComputeRun(
                status="needs_input",
                artifact=RawArtifact.missing(path, technique=normalized_technique),
                reasons=("raw_artifact_unreadable",),
            )
        source = Path(artifact.path)
        try:
            source_exists = source.exists()
            is_regular_file = source.is_file()
            is_directory = source.is_dir()
        except Exception:
            return ComputeRun(
                status="needs_input",
                artifact=RawArtifact.missing(source, technique=normalized_technique),
                reasons=("raw_artifact_unreadable",),
            )
        if not source_exists:
            return ComputeRun(
                status="needs_input",
                artifact=RawArtifact.missing(source, technique=normalized_technique),
                reasons=("raw_artifact_missing",),
            )
        if not (is_regular_file or is_directory):
            return ComputeRun(
                status="needs_input",
                artifact=RawArtifact.missing(source, technique=normalized_technique),
                reasons=("raw_artifact_unreadable",),
            )
        resolved_output_path = _resolve_output_dir(output_dir)
        if resolved_output_path is None:
            return ComputeRun(
                status="needs_input",
                artifact=artifact,
                reasons=("output_directory_invalid",),
            )
        options, options_reason = _normalize_pipeline_options(pipeline_options)
        if options_reason is not None:
            return ComputeRun(
                status="needs_input",
                artifact=artifact,
                reasons=(options_reason,),
            )
        assert options is not None
        dataset = CanonicalDataset.direct_envelope(artifact)
        plan = AnalysisPlan.direct(
            dataset,
            output_dir=resolved_output_path,
            pipeline_options=options,
        )
        # An empty output string is the public provider convention for
        # analysis-only execution.  Keep it empty at the engine boundary even
        # though the immutable plan stores a resolved path for provenance.
        provider_output_dir = "" if isinstance(output_dir, str) and not output_dir.strip() else plan.output_dir
        if canonical_template is not None:
            try:
                canonical_template = CanonicalExperiment.from_dict(canonical_template.to_dict())
            except (AttributeError, KeyError, TypeError, ValueError):
                return ComputeRun(
                    status="needs_input",
                    artifact=artifact,
                    reasons=("canonical_template_invalid",),
                )
            if canonical_template.source_artifact_id != artifact.artifact_id:
                return ComputeRun(
                    status="needs_input",
                    artifact=artifact,
                    reasons=("canonical_template_mismatch",),
                )
            if str(canonical_template.payload.get("technique", normalized_technique)).lower() != normalized_technique:
                return ComputeRun(
                    status="needs_input",
                    artifact=artifact,
                    reasons=("canonical_template_technique_mismatch",),
                )
        capability_items = (
            CapabilityExecutor().execute(canonical_template)
            if canonical_template is not None and canonical_template.measurements
            else ()
        )
        if (
            canonical_template is None
            and normalized_technique in {"dsc", "ir", "saxs", "waxs"}
            and (source.is_file() or (source.is_dir() and normalized_technique != "dsc"))
        ):
            conversion = default_converter_registry().convert_path(
                source,
                technique=normalized_technique,
                source_artifact_id=artifact.artifact_id,
            )
            if conversion.status == "needs_input":
                return ComputeRun(
                    status="needs_input",
                    artifact=artifact,
                    reasons=conversion.reason_codes,
                )
            if (
                conversion.status == "ready"
                and conversion.template is not None
            ):
                canonical_template = conversion.template
                if canonical_template.measurements:
                    capability_items = CapabilityExecutor().execute(canonical_template)
        try:
            selected_engine = engine
            if selected_engine is None:
                selected_engine = self._engine_factory(
                    normalized_technique,
                    config=config,
                    submodule_id=submodule_id,
                )
            if selected_engine is None:
                return ComputeRun(
                    status="needs_input",
                    artifact=artifact,
                    reasons=("technique_unknown",),
                )
            if (
                canonical_template is not None
                and normalized_technique == "dsc"
                and (
                    hasattr(selected_engine, "run_thermal_program_template")
                    or hasattr(selected_engine, "run_isothermal_template")
                )
            ):
                template_runner = getattr(selected_engine, "run_thermal_program_template", None)
                if not callable(template_runner):
                    template_runner = getattr(selected_engine, "run_isothermal_template")
                template_output = template_runner(canonical_template)
                legacy_result = template_output
                if not _has_legacy_result_shape(legacy_result):
                    legacy_result = getattr(selected_engine, "result", None)
                if legacy_result is not None:
                    get_parameters = getattr(selected_engine, "get_parameters", None)
                    if callable(get_parameters):
                        parameters = get_parameters()
                        if isinstance(parameters, Mapping):
                            legacy_result.parameters = _json_safe_projection(parameters)
            else:
                legacy_result = selected_engine.run_pipeline(
                    artifact.path,
                    provider_output_dir,
                    **options,
                )
            if not _has_legacy_result_shape(legacy_result):
                return ComputeRun(
                    status="failed",
                    artifact=artifact,
                    dataset=dataset,
                    plan=plan,
                    canonical_template=canonical_template,
                    capability_items=capability_items,
                    reasons=("provider_execution_failed",),
                )
            return ComputeRun.completed(
                artifact=artifact,
                dataset=dataset,
                plan=plan,
                result=ComputeResult.from_legacy_result(legacy_result),
                canonical_template=canonical_template,
                capability_items=capability_items,
                legacy_result=legacy_result,
            )
        except Exception:
            return ComputeRun(
                status="failed",
                artifact=artifact,
                dataset=dataset,
                plan=plan,
                canonical_template=canonical_template,
                capability_items=capability_items,
                reasons=("provider_execution_failed",),
            )
