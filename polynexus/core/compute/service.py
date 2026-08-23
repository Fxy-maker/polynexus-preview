"""Direct-run adapter from the public compute contracts to legacy engines."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping

from ..engine import get_engine
from .models import AnalysisPlan, CanonicalDataset, ComputeResult, ComputeRun, RawArtifact


_SUPPORTED_PIPELINE_OPTIONS = frozenset({"skip_to"})


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
        try:
            options = dict(pipeline_options or {})
        except (TypeError, ValueError):
            options = {}
            unsupported_options = True
        else:
            unsupported_options = any(name not in _SUPPORTED_PIPELINE_OPTIONS for name in options)
        if unsupported_options:
            return ComputeRun(
                status="needs_input",
                artifact=artifact,
                reasons=("pipeline_option_unsupported",),
            )
        dataset: CanonicalDataset | None = None
        plan: AnalysisPlan | None = None
        try:
            dataset = CanonicalDataset.direct_envelope(artifact)
            plan = AnalysisPlan.direct(
                dataset,
                output_dir=output_dir,
                pipeline_options=options,
            )
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
