"""Direct-run adapter from the public compute contracts to legacy engines."""

from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
from typing import Any, Callable

from ..engine import get_engine
from .models import AnalysisPlan, CanonicalDataset, ComputeResult, ComputeRun, RawArtifact


_SUPPORTED_PIPELINE_OPTIONS = frozenset({"skip_to", "mask_edit_candidate"})
_SUPPORTED_SKIP_TO_VALUES = frozenset({"preprocess", "analyze", "plot"})


def _safe_technique(value: object) -> str | None:
    """Return one normalized technique string without coercing arbitrary objects."""
    if not isinstance(value, str):
        return None
    normalized = str.lower(str.strip(value))
    return normalized or None


def _resolve_path(value: object) -> Path | None:
    """Return a canonical path only when path normalization is safe."""
    try:
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
    ) -> ComputeRun:
        normalized_technique = _safe_technique(technique)
        if normalized_technique is None:
            return ComputeRun(
                status="needs_input",
                artifact=RawArtifact.missing(path, technique="unknown"),
                reasons=("technique_invalid",),
            )
        source = _resolve_path(path)
        if source is None:
            return ComputeRun(
                status="needs_input",
                artifact=RawArtifact.missing(path, technique=normalized_technique),
                reasons=("raw_artifact_unreadable",),
            )
        try:
            source_exists = source.exists()
            is_regular_file = source.is_file()
        except Exception:
            return ComputeRun(
                status="needs_input",
                artifact=RawArtifact.missing(path, technique=normalized_technique),
                reasons=("raw_artifact_unreadable",),
            )
        if not source_exists:
            return ComputeRun(
                status="needs_input",
                artifact=RawArtifact.missing(source, technique=normalized_technique),
                reasons=("raw_artifact_missing",),
            )
        if not is_regular_file:
            return ComputeRun(
                status="needs_input",
                artifact=RawArtifact.missing(source, technique=normalized_technique),
                reasons=("raw_artifact_unreadable",),
            )

        try:
            artifact = RawArtifact.from_path(source, technique=normalized_technique)
        except Exception:
            return ComputeRun(
                status="needs_input",
                artifact=RawArtifact.missing(source, technique=normalized_technique),
                reasons=("raw_artifact_unreadable",),
            )
        resolved_output_path = _resolve_path(output_dir)
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
            legacy_result = selected_engine.run_pipeline(
                artifact.path,
                plan.output_dir,
                **options,
            )
            if not _has_legacy_result_shape(legacy_result):
                return ComputeRun(
                    status="failed",
                    artifact=artifact,
                    dataset=dataset,
                    plan=plan,
                    reasons=("provider_execution_failed",),
                )
            return ComputeRun.completed(
                artifact=artifact,
                dataset=dataset,
                plan=plan,
                result=ComputeResult.from_legacy_result(legacy_result),
                legacy_result=legacy_result,
            )
        except Exception:
            return ComputeRun(
                status="failed",
                artifact=artifact,
                dataset=dataset,
                plan=plan,
                reasons=("provider_execution_failed",),
            )
