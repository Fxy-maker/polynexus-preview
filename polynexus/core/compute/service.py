"""Direct-run adapter from the public compute contracts to legacy engines."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Callable

from ..engine import get_engine
from .models import AnalysisPlan, CanonicalDataset, ComputeResult, ComputeRun, RawArtifact


_SUPPORTED_PIPELINE_OPTIONS = frozenset({"skip_to"})
_SUPPORTED_SKIP_TO_VALUES = frozenset({"preprocess", "analyze", "plot"})


def _resolve_output_dir(value: str | Path) -> str | None:
    """Return a canonical output directory only when it is path-valid."""
    try:
        return str(Path(value).expanduser().resolve(strict=False))
    except (OSError, TypeError, ValueError):
        return None


def _validated_pipeline_options(
    value: Mapping[str, Any] | None,
) -> tuple[dict[str, Any] | None, str | None]:
    """Return supported JSON-safe direct-pipeline options or a public reason."""
    if value is None:
        return {}, None
    if not isinstance(value, Mapping):
        return None, "pipeline_option_invalid"
    try:
        options = dict(value)
    except (OSError, TypeError, ValueError):
        return None, "pipeline_option_invalid"
    if any(name not in _SUPPORTED_PIPELINE_OPTIONS for name in options):
        return None, "pipeline_option_unsupported"
    skip_to = options.get("skip_to")
    if "skip_to" in options and not (
        skip_to is None or (isinstance(skip_to, str) and skip_to in _SUPPORTED_SKIP_TO_VALUES)
    ):
        return None, "pipeline_option_invalid"
    return options, None


class ComputeRunService:
    """Create one canonical direct run and delegate its calculation to an engine."""

    def __init__(self, engine_factory: Callable[..., Any] = get_engine) -> None:
        self._engine_factory = engine_factory

    def run_direct(
        self,
        *,
        technique: str,
        path: str | Path,
        output_dir: str | Path,
        config: Any = None,
        submodule_id: str | None = None,
        engine: Any = None,
        pipeline_options: Mapping[str, Any] | None = None,
    ) -> ComputeRun:
        try:
            source = Path(path).expanduser().resolve(strict=False)
            source_exists = source.exists()
            is_regular_file = source.is_file()
        except (OSError, ValueError, TypeError):
            return ComputeRun(
                status="needs_input",
                artifact=RawArtifact.missing(path, technique=technique),
                reasons=("raw_artifact_unreadable",),
            )
        if not source_exists:
            return ComputeRun(
                status="needs_input",
                artifact=RawArtifact.missing(source, technique=technique),
                reasons=("raw_artifact_missing",),
            )
        if not is_regular_file:
            return ComputeRun(
                status="needs_input",
                artifact=RawArtifact.missing(source, technique=technique),
                reasons=("raw_artifact_unreadable",),
            )

        try:
            artifact = RawArtifact.from_path(source, technique=technique)
        except (OSError, ValueError, TypeError):
            return ComputeRun(
                status="needs_input",
                artifact=RawArtifact.missing(source, technique=technique),
                reasons=("raw_artifact_unreadable",),
            )
        resolved_output_dir = _resolve_output_dir(output_dir)
        if resolved_output_dir is None:
            return ComputeRun(
                status="needs_input",
                artifact=artifact,
                reasons=("output_directory_invalid",),
            )
        options, options_reason = _validated_pipeline_options(pipeline_options)
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
            output_dir=resolved_output_dir,
            pipeline_options=options,
        )
        try:
            selected_engine = engine
            if selected_engine is None:
                selected_engine = self._engine_factory(
                    technique,
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
                **dict(plan.pipeline_options),
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
