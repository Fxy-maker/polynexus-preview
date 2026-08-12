"""Public agent-workflow operations with replay identity checks."""

from __future__ import annotations

from collections.abc import Callable, Mapping
import json
import math
from pathlib import Path
from typing import Any

from .inspection import inspect_artifact
from .evidence import build_evidence
from .models import (
    AnalysisRecipe,
    AnalysisRun,
    InputArtifact,
    RecipeProposal,
    WorkflowStepResult,
)
from .registry import WorkflowRegistry
from .tpae import TpaeCharacterizationWorkflow


class AgentWorkflowService:
    """Constrained orchestration facade for agents, CLI, and future GUI callers."""

    def __init__(
        self,
        *,
        registry: WorkflowRegistry | None = None,
        provider_runner: Callable[[Any, InputArtifact, Path], Any] | None = None,
    ) -> None:
        self.registry = registry or WorkflowRegistry()
        if self.registry.get(TpaeCharacterizationWorkflow.workflow_id) is None:
            self.registry.register(TpaeCharacterizationWorkflow())
        self.provider_runner = provider_runner

    def inspect_data(self, path: str | Path, *, technique: str = "unknown") -> InputArtifact:
        return inspect_artifact(path, technique=technique)

    def propose_recipe(
        self,
        workflow_id: str,
        manifest: Mapping[str, object] | Path | str,
    ) -> RecipeProposal:
        adapter = self.registry.get(workflow_id)
        if adapter is None:
            return RecipeProposal(status="blocked", reason_codes=("workflow_unknown",))
        return adapter.propose_recipe(manifest)

    def run_recipe(self, recipe: AnalysisRecipe, output_dir: str | Path) -> AnalysisRun:
        for artifact in recipe.artifacts:
            current = inspect_artifact(artifact.path, technique=artifact.technique)
            if current.sha256 != artifact.sha256:
                return AnalysisRun(recipe=recipe, status="blocked", reason_codes=("artifact_hash_mismatch",))
            if current.inspection_status == "blocked":
                return AnalysisRun(recipe=recipe, status="blocked", reason_codes=("artifact_blocked",))
        if self.provider_runner is None:
            return AnalysisRun(recipe=recipe, status="blocked", reason_codes=("provider_runner_unavailable",))
        destination = Path(output_dir).resolve()
        destination.mkdir(parents=True, exist_ok=True)
        artifacts_by_technique = {artifact.technique: artifact for artifact in recipe.artifacts}
        results: list[WorkflowStepResult] = []
        for step in recipe.steps:
            artifact = artifacts_by_technique.get(step.technique)
            if artifact is None:
                return AnalysisRun(recipe=recipe, status="blocked", reason_codes=("step_artifact_missing",))
            try:
                output = self.provider_runner(step, artifact, destination)
                results.append(self._public_step_result(step.step_id, step.technique, output))
            except Exception:
                return AnalysisRun(recipe=recipe, status="failed", reason_codes=("provider_execution_failed",))
        status = "completed" if all(result.status == "completed" for result in results) else "review_required"
        return AnalysisRun(recipe=recipe, status=status, steps=tuple(results))

    def validate_run(self, run: AnalysisRun) -> AnalysisRun:
        """Aggregate public step evidence without rerunning providers."""
        if run.status in {"blocked", "failed"}:
            return AnalysisRun(
                recipe=run.recipe,
                status=run.status,
                reason_codes=run.reason_codes,
                steps=run.steps,
                evidence=build_evidence(run.steps),
                validated=True,
            )
        status = "completed" if all(step.status == "completed" for step in run.steps) else "review_required"
        if any(step.technique in {"ir", "waxs", "saxs"} for step in run.steps):
            status = "review_required"
        return AnalysisRun(
            recipe=run.recipe,
            status=status,
            reason_codes=run.reason_codes,
            steps=run.steps,
            evidence=build_evidence(run.steps),
            validated=True,
        )

    def export_run(self, run: AnalysisRun, destination: str | Path) -> Path:
        """Write replay evidence only; raw source files are never copied."""
        if not run.validated:
            raise ValueError("Run must be validated before export")
        bundle = Path(destination).resolve()
        raw_paths = {Path(artifact.path).resolve() for artifact in run.recipe.artifacts}
        if bundle in raw_paths:
            raise ValueError("Export destination must not replace an input artifact")
        bundle.mkdir(parents=True, exist_ok=True)
        (bundle / "results").mkdir(exist_ok=True)
        self._write_json(bundle / "run.json", run.to_dict())
        self._write_json(bundle / "recipe.json", run.recipe.to_dict())
        self._write_json(bundle / "artifacts.json", [artifact.to_dict() for artifact in run.recipe.artifacts])
        self._write_json(bundle / "evidence.json", run.evidence.to_dict() if run.evidence else {})
        for step in run.steps:
            self._write_json(bundle / "results" / f"{step.step_id}.json", step.to_dict())
        return bundle

    @staticmethod
    def _public_step_result(step_id: str, technique: str, output: Any) -> WorkflowStepResult:
        if hasattr(output, "to_dict") and hasattr(output, "analysis_evidence"):
            summary = AgentWorkflowService._normalize_public_value(output.to_dict())
            evidence = getattr(output, "analysis_evidence", {})
        elif isinstance(output, Mapping):
            summary = AgentWorkflowService._normalize_public_value(dict(output))
            evidence = summary.get("analysis_evidence", {})
        else:
            raise TypeError("Provider must return AnalysisResult or public result mapping")
        validation_passed = bool(summary.get("validation_passed", True))
        warnings = summary.get("validation_warnings", [])
        status = "completed" if validation_passed and not warnings else "review_required"
        return WorkflowStepResult(
            step_id=step_id,
            technique=technique,
            status=status,
            result_summary=summary,
            analysis_evidence=evidence if isinstance(evidence, Mapping) else {},
        )

    @staticmethod
    def _write_json(path: Path, payload: Any) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    @staticmethod
    def _normalize_public_value(value: Any) -> Any:
        """Map legacy non-finite result scalars to JSON null at the new boundary."""
        if isinstance(value, float):
            return value if math.isfinite(value) else None
        if isinstance(value, Mapping):
            return {str(key): AgentWorkflowService._normalize_public_value(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [AgentWorkflowService._normalize_public_value(item) for item in value]
        return value
