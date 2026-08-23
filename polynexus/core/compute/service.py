"""Direct-run adapter from the public compute contracts to legacy engines."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping

from ..engine import get_engine
from .models import AnalysisPlan, CanonicalDataset, ComputeResult, ComputeRun, RawArtifact


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
        source = Path(path).expanduser()
        if not source.exists():
            return ComputeRun(
                status="needs_input",
                artifact=RawArtifact.missing(path, technique=technique),
                reasons=("raw_artifact_missing",),
            )

        artifact = RawArtifact.from_path(path, technique=technique)
        dataset: CanonicalDataset | None = None
        plan: AnalysisPlan | None = None
        try:
            dataset = CanonicalDataset.direct_envelope(artifact)
            plan = AnalysisPlan.direct(
                dataset,
                output_dir=output_dir,
                pipeline_options=pipeline_options,
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
                str(path),
                str(output_dir),
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
