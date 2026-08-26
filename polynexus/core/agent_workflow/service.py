"""Public agent-workflow operations with replay identity checks."""

from __future__ import annotations

from collections.abc import Callable, Mapping
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import secrets
from typing import Any

from .inspection import inspect_artifact
from .evidence import build_evidence
from .models import (
    AnalysisRecipe,
    AnalysisRun,
    InputArtifact,
    RecipeProposal,
    WorkflowStepResult,
    canonical_json,
)
from .registry import WorkflowRegistry
from .tpae import TpaeCharacterizationWorkflow
from polynexus.core.canonical_experiments import CanonicalExperiment, default_converter_registry
from polynexus.core.compute import ComputeRun, ComputeRunService


class AgentWorkflowService:
    """Constrained orchestration facade for agents, CLI, and future GUI callers."""

    def __init__(
        self,
        *,
        registry: WorkflowRegistry | None = None,
        provider_runner: Callable[[Any, InputArtifact, Path], Any] | None = None,
        get_engine_fn: Callable[[str], Any] | None = None,
    ) -> None:
        self.registry = registry or WorkflowRegistry()
        if self.registry.get(TpaeCharacterizationWorkflow.workflow_id) is None:
            self.registry.register(TpaeCharacterizationWorkflow())
        self.get_engine_fn = get_engine_fn
        self.provider_runner = provider_runner or self._run_existing_pipeline

    def inspect_data(self, path: str | Path, *, technique: str = "unknown") -> InputArtifact:
        return inspect_artifact(path, technique=technique)

    def inspect_manifest(self, manifest: Mapping[str, object] | Path | str) -> dict[str, Any]:
        """Inspect all declared manifest artifacts without requiring a valid recipe."""
        payload = self._load_manifest(manifest)
        if payload is None:
            return {"status": "blocked", "reason_codes": ["manifest_invalid"], "artifacts": []}
        raw_artifacts = payload.get("artifacts")
        if not isinstance(raw_artifacts, Mapping):
            return {"status": "blocked", "reason_codes": ["manifest_artifacts_missing"], "artifacts": []}
        artifacts: list[dict[str, Any]] = []
        blocked = False
        review = False
        for step_id, raw in raw_artifacts.items():
            if not isinstance(raw, Mapping) or not raw.get("path"):
                artifacts.append({"step_id": str(step_id), "reason_codes": ["artifact_invalid"]})
                blocked = True
                continue
            artifact = inspect_artifact(raw["path"], technique=str(raw.get("technique", "unknown")))
            artifacts.append({"step_id": str(step_id), **artifact.to_dict()})
            blocked = blocked or artifact.inspection_status == "blocked"
            review = review or artifact.inspection_status == "review_required"
        return {
            "status": "blocked" if blocked else "review_required" if review else "ready",
            "reason_codes": [],
            "artifacts": artifacts,
        }

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
        if not self._recipe_is_valid(recipe):
            return AnalysisRun(recipe=recipe, status="blocked", reason_codes=("recipe_invalid",))
        for artifact in recipe.artifacts:
            current = inspect_artifact(artifact.path, technique=artifact.technique)
            if current.sha256 != artifact.sha256:
                return AnalysisRun(recipe=recipe, status="blocked", reason_codes=("artifact_hash_mismatch",))
            if current.inspection_status == "blocked":
                return AnalysisRun(recipe=recipe, status="blocked", reason_codes=("artifact_blocked",))
        destination = Path(output_dir).resolve()
        raw_dirs = self._input_directories(recipe.artifacts)
        if destination in raw_dirs or any(raw_dir in destination.parents for raw_dir in raw_dirs):
            return AnalysisRun(recipe=recipe, status="blocked", reason_codes=("output_inside_input_directory",))
        try:
            destination.mkdir(parents=True, exist_ok=True)
        except OSError:
            return AnalysisRun(recipe=recipe, status="failed", reason_codes=("output_directory_unavailable",))
        artifacts_by_technique = {artifact.technique: artifact for artifact in recipe.artifacts}
        results: list[WorkflowStepResult] = []
        for step in recipe.steps:
            artifact_index = step.parameters.get("artifact_index")
            artifact = (
                recipe.artifacts[int(artifact_index)]
                if isinstance(artifact_index, int) and 0 <= artifact_index < len(recipe.artifacts)
                else artifacts_by_technique.get(step.technique)
            )
            if artifact is None:
                return AnalysisRun(recipe=recipe, status="blocked", reason_codes=("step_artifact_missing",))
            try:
                canonical_template = self._replay_canonical_template(step, artifact)
                if canonical_template is False:
                    return AnalysisRun(recipe=recipe, status="blocked", reason_codes=("canonical_conversion_mismatch",))
                output, compute_run = self._run_shared_compute(step, artifact, destination)
                results.append(
                    self._public_step_result(
                        step.step_id,
                        step.technique,
                        output,
                        canonical_template=canonical_template if isinstance(canonical_template, CanonicalExperiment) else None,
                        compute_run=compute_run,
                    )
                )
            except Exception:
                return AnalysisRun(recipe=recipe, status="failed", reason_codes=("provider_execution_failed",))
        status = (
            "failed"
            if any(result.status == "failed" for result in results)
            else "completed" if all(result.status == "completed" for result in results) else "review_required"
        )
        return self._with_execution_receipt(AnalysisRun(recipe=recipe, status=status, steps=tuple(results)))

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
                execution_receipt=run.execution_receipt,
            )
        if not self._receipt_is_valid(run):
            return AnalysisRun(
                recipe=run.recipe,
                status="blocked",
                reason_codes=("run_receipt_invalid",),
                steps=run.steps,
                evidence=build_evidence(run.steps),
                execution_receipt=run.execution_receipt,
            )
        status = "completed" if all(step.status == "completed" for step in run.steps) else "review_required"
        if any(step.technique in {"ir", "waxs", "saxs"} for step in run.steps):
            status = "review_required"
        return self._with_execution_receipt(
            AnalysisRun(
                recipe=run.recipe,
                status=status,
                reason_codes=run.reason_codes,
                steps=run.steps,
                evidence=build_evidence(run.steps),
                validated=True,
            )
        )

    def export_run(self, run: AnalysisRun, destination: str | Path) -> Path:
        """Write replay evidence only; raw source files are never copied."""
        if not run.validated or not self._run_is_exportable(run):
            raise ValueError("Run must be validated before export")
        bundle = Path(destination).resolve()
        raw_dirs = self._input_directories(run.recipe.artifacts)
        if bundle in raw_dirs or any(raw_dir in bundle.parents for raw_dir in raw_dirs):
            raise ValueError("Export destination must not be inside an input artifact directory")
        bundle.mkdir(parents=True, exist_ok=True)
        (bundle / "results").mkdir(exist_ok=True)
        (bundle / "figures").mkdir(exist_ok=True)
        self._write_json(bundle / "run.json", run.to_dict())
        self._write_json(bundle / "recipe.json", run.recipe.to_dict())
        self._write_json(bundle / "artifacts.json", [artifact.to_dict() for artifact in run.recipe.artifacts])
        self._write_json(bundle / "evidence.json", run.evidence.to_dict() if run.evidence else {})
        for step in run.steps:
            self._write_json(bundle / "results" / f"{step.step_id}.json", step.to_dict())
        self._write_json(
            bundle / "figures" / "manifest.json",
            {
                "steps": [
                    {"step_id": step.step_id, "assets": self._normalize_public_value(step.figure_references)}
                    for step in run.steps
                ]
            },
        )
        return bundle

    @staticmethod
    def _public_step_result(
        step_id: str,
        technique: str,
        output: Any,
        *,
        canonical_template: CanonicalExperiment | None = None,
        compute_run: ComputeRun | None = None,
    ) -> WorkflowStepResult:
        if hasattr(output, "to_dict") and hasattr(output, "analysis_evidence"):
            summary = AgentWorkflowService._normalize_public_value(output.to_dict())
            evidence = getattr(output, "analysis_evidence", {})
        elif isinstance(output, Mapping):
            summary = AgentWorkflowService._normalize_public_value(dict(output))
            evidence = summary.get("analysis_evidence", {})
        else:
            raise TypeError("Provider must return AnalysisResult or public result mapping")
        if canonical_template is not None:
            summary["canonical_template_hash"] = canonical_template.content_hash
            summary["canonical_conversion"] = canonical_template.conversion_record.to_dict()
        validation_passed = bool(summary.get("validation_passed", True))
        warnings = summary.get("validation_warnings", [])
        logs = summary.get("logs", [])
        provider_error = any("ERROR:" in str(entry).upper() for entry in logs)
        status = (
            "failed"
            if provider_error
            else "completed"
            if validation_passed and not warnings and canonical_template is None
            else "review_required"
        )
        figure_references = getattr(output, "figures", {})
        if not isinstance(figure_references, Mapping):
            figure_references = {}
        return WorkflowStepResult(
            step_id=step_id,
            technique=technique,
            status=status,
            result_summary=summary,
            analysis_evidence=evidence if isinstance(evidence, Mapping) else {},
            figure_references=AgentWorkflowService._normalize_public_value(dict(figure_references)),
            compute_run=(compute_run.to_dict() if isinstance(compute_run, ComputeRun) else None),
            reason_codes=("provider_reported_error",) if provider_error else (),
        )

    def _run_shared_compute(
        self,
        step: Any,
        artifact: InputArtifact,
        output_dir: Path,
    ) -> tuple[Any, ComputeRun | None]:
        """Execute table-backed workflow steps through the shared run service.

        Directory workflows and the protected DSC template route retain their
        existing adapters until their dedicated canonical migrations land.
        Generic one-dimensional files already have a registered converter and
        therefore produce the same ComputeRun consumed by Batch and GUI.
        """
        if artifact.format == "directory":
            return self.provider_runner(step, artifact, output_dir), None

        provider_output = self.provider_runner(step, artifact, output_dir)
        legacy_output = provider_output
        if isinstance(provider_output, Mapping):
            class _MappingResult:
                parameters = provider_output.get("parameters", provider_output)
                figures = provider_output.get("figures", {})
                metadata = provider_output.get("metadata", {})
                validation_passed = provider_output.get("validation_passed", True)
                validation_warnings = provider_output.get("validation_warnings", ())
                quality_flags = provider_output.get("quality_flags", {})
                validation_summary = provider_output.get("validation_summary", "")
                logs = provider_output.get("logs", ())

            legacy_output = _MappingResult()

        class _WorkflowEngine:
            def run_pipeline(inner_self, path, step_output_dir, **options):
                return legacy_output

        compute_run = ComputeRunService(lambda *args, **kwargs: _WorkflowEngine()).run_direct(
            technique=step.technique,
            path=artifact.path,
            output_dir=output_dir / step.step_id,
            submodule_id=step.parameters.get("submodule_id"),
        )
        if compute_run.status != "completed":
            return provider_output, None
        return provider_output, compute_run

    @staticmethod
    def _write_json(path: Path, payload: Any) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    def _run_existing_pipeline(self, step: Any, artifact: InputArtifact, output_dir: Path) -> Any:
        """Adapt existing public engine pipelines without reaching into their state."""
        if self.get_engine_fn is None:
            from polynexus.core.engine import get_engine

            engine = get_engine(step.technique)
        else:
            engine = self.get_engine_fn(step.technique)
        if engine is None:
            raise RuntimeError("engine unavailable")
        submodule_id = step.parameters.get("submodule_id")
        if submodule_id:
            engine.active_submodule = str(submodule_id)
        canonical_payload = step.parameters.get("canonical_template")
        if canonical_payload is not None and step.technique == "dsc":
            template = CanonicalExperiment.from_dict(canonical_payload)
            engine.run_isothermal_template(template)
            engine.result.parameters = engine.get_parameters()
            engine.result.metadata.update({
                "canonical_template_hash": template.content_hash,
                "canonical_conversion_hash": template.conversion_record.conversion_hash,
            })
            return engine.result
        return engine.run_pipeline(artifact.path, str(output_dir / step.step_id))

    @staticmethod
    def _replay_canonical_template(step: Any, artifact: InputArtifact) -> CanonicalExperiment | bool | None:
        """Reconvert a registered source after artifact hash verification."""
        payload = step.parameters.get("canonical_template")
        if payload is None:
            return None
        if artifact.format == "directory" and artifact.technique != "ir":
            return False
        try:
            registered = CanonicalExperiment.from_dict(payload)
        except (KeyError, OSError, TypeError, ValueError):
            return False
        outcome = default_converter_registry().replay_path(
            artifact.path,
            technique=artifact.technique,
            source_artifact_id=artifact.artifact_id,
        )
        if outcome.status != "ready" or outcome.template is None:
            return False
        if outcome.record.conversion_id != step.parameters.get("canonical_converter"):
            return False
        return outcome.template if hmac.compare_digest(outcome.template.content_hash, registered.content_hash) else False

    @staticmethod
    def _load_manifest(manifest: Mapping[str, object] | Path | str) -> Mapping[str, Any] | None:
        if isinstance(manifest, Mapping):
            return manifest
        try:
            payload = json.loads(Path(manifest).read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return None
        return payload if isinstance(payload, Mapping) else None

    @staticmethod
    def _input_directories(artifacts: tuple[InputArtifact, ...]) -> set[Path]:
        return {
            path if artifact.format == "directory" else path.parent
            for artifact in artifacts
            for path in (Path(artifact.path).resolve(),)
        }

    def _recipe_is_valid(self, recipe: AnalysisRecipe) -> bool:
        """Reconstruct canonical content before any provider can be invoked."""
        try:
            AnalysisRecipe.from_dict(recipe.to_dict())
        except (KeyError, TypeError, ValueError):
            return False
        adapter = self.registry.get(recipe.workflow_id)
        validator = getattr(adapter, "is_valid_recipe", None)
        return bool(callable(validator) and validator(recipe))

    def _run_is_exportable(self, run: AnalysisRun) -> bool:
        """Reject fabricated or stale persisted state before creating evidence bundles."""
        if (
            not self._receipt_is_valid(run)
            or not self._recipe_is_valid(run.recipe)
            or run.status not in {"completed", "review_required"}
        ):
            return False
        expected = {(step.step_id, step.technique) for step in run.recipe.steps}
        actual = {(step.step_id, step.technique) for step in run.steps}
        if expected != actual or any(step.status not in {"completed", "review_required"} for step in run.steps):
            return False
        expected_status = "completed" if all(step.status == "completed" for step in run.steps) else "review_required"
        if any(step.technique in {"ir", "waxs", "saxs"} for step in run.steps):
            expected_status = "review_required"
        if run.status != expected_status:
            return False
        for artifact in run.recipe.artifacts:
            current = inspect_artifact(artifact.path, technique=artifact.technique)
            if current.inspection_status == "blocked" or current.sha256 != artifact.sha256:
                return False
        return True

    def _with_execution_receipt(self, run: AnalysisRun) -> AnalysisRun:
        return AnalysisRun(
            recipe=run.recipe,
            status=run.status,
            reason_codes=run.reason_codes,
            steps=run.steps,
            evidence=run.evidence,
            validated=run.validated,
            execution_receipt=self._receipt_for(run),
        )

    def _receipt_is_valid(self, run: AnalysisRun) -> bool:
        return bool(run.execution_receipt) and hmac.compare_digest(
            run.execution_receipt,
            self._receipt_for(run),
        )

    def _receipt_for(self, run: AnalysisRun) -> str:
        payload = {
            "recipe": run.recipe.to_dict(),
            "status": run.status,
            "reason_codes": list(run.reason_codes),
            "steps": [step.to_dict() for step in run.steps],
            "evidence": run.evidence.to_dict() if run.evidence else None,
            "validated": run.validated,
        }
        return hmac.new(self._receipt_key(), canonical_json(payload).encode("utf-8"), hashlib.sha256).hexdigest()

    @staticmethod
    def _receipt_key() -> bytes:
        configured = os.environ.get("POLYNEXUS_AGENT_WORKFLOW_RECEIPT_KEY")
        if configured:
            return configured.encode("utf-8")
        state_root = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local")) / "PolyNexus"
        key_path = state_root / "agent-workflow-receipt.key"
        try:
            key = key_path.read_bytes()
        except OSError:
            state_root.mkdir(parents=True, exist_ok=True)
            key = secrets.token_bytes(32)
            key_path.write_bytes(key)
        return key

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
