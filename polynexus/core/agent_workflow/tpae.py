"""Manifest adapter for the first TPAE characterization golden workflow."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .inspection import inspect_artifact
from .models import AnalysisRecipe, RecipeProposal, RecipeStep


class TpaeCharacterizationWorkflow:
    """Propose only existing provider calls; this adapter contains no algorithms."""

    workflow_id = "tpae.characterization.v1"
    _STEP_SPECS = (
        ("dsc_isothermal", "dsc", "primary", True),
        ("ftir_temperature", "ir", "supporting", False),
        ("waxs_profile", "waxs", "context", False),
        ("saxs_profile", "saxs", "context", False),
    )

    def propose_recipe(self, manifest: Mapping[str, object] | Path | str) -> RecipeProposal:
        payload = self._load_manifest(manifest)
        if payload is None:
            return RecipeProposal(status="blocked", reason_codes=("manifest_invalid",))
        if payload.get("workflow_id") != self.workflow_id:
            return RecipeProposal(status="blocked", reason_codes=("workflow_id_mismatch",))
        raw_artifacts = payload.get("artifacts")
        if not isinstance(raw_artifacts, Mapping):
            return RecipeProposal(status="blocked", reason_codes=("manifest_artifacts_missing",))

        artifacts = []
        steps = []
        status = "ready"
        reasons: list[str] = []
        for step_id, technique, evidence_role, required in self._STEP_SPECS:
            raw = raw_artifacts.get(step_id)
            if raw is None:
                if required:
                    reasons.append(f"required_artifact_missing:{step_id}")
                continue
            if not isinstance(raw, Mapping) or not raw.get("path"):
                reasons.append(f"artifact_invalid:{step_id}")
                continue
            declared_technique = str(raw.get("technique") or technique).lower()
            if declared_technique != technique:
                reasons.append(f"artifact_technique_mismatch:{step_id}")
                continue
            artifact = inspect_artifact(raw["path"], technique=technique)
            if step_id in {"dsc_isothermal", "ftir_temperature"} and artifact.format != "directory":
                reasons.append(f"artifact_format_mismatch:{step_id}")
                continue
            artifacts.append(artifact)
            parameters = {
                "dsc_isothermal": {"submodule_id": "dsc.isothermal"},
                "ftir_temperature": {"submodule_id": "ir.temperature_2d"},
            }.get(step_id, {})
            sources = {"submodule_id": "workflow"} if parameters else {}
            steps.append(
                RecipeStep(
                    step_id=step_id,
                    technique=technique,
                    evidence_role=evidence_role,
                    parameters=parameters,
                    parameter_sources=sources,
                )
            )
            if artifact.inspection_status == "blocked":
                reasons.append(f"artifact_blocked:{step_id}")
            elif artifact.inspection_status == "review_required":
                status = "review_required"

        if reasons:
            return RecipeProposal(status="blocked", reason_codes=tuple(reasons))
        return RecipeProposal(
            status=status,
            recipe=AnalysisRecipe.create(
                workflow_id=self.workflow_id,
                artifacts=artifacts,
                steps=steps,
            ),
        )

    @classmethod
    def is_valid_recipe(cls, recipe: AnalysisRecipe) -> bool:
        """Confirm a persisted recipe still binds only declared TPAE providers."""
        if recipe.workflow_id != cls.workflow_id:
            return False
        specifications = {step_id: (technique, role) for step_id, technique, role, _ in cls._STEP_SPECS}
        if not recipe.steps or len({step.step_id for step in recipe.steps}) != len(recipe.steps):
            return False
        if len({artifact.technique for artifact in recipe.artifacts}) != len(recipe.artifacts):
            return False
        artifacts = {artifact.technique: artifact for artifact in recipe.artifacts}
        required_steps = {step_id for step_id, _, _, required in cls._STEP_SPECS if required}
        if not required_steps.issubset({step.step_id for step in recipe.steps}):
            return False
        for step in recipe.steps:
            expected = specifications.get(step.step_id)
            if expected is None or (step.technique, step.evidence_role) != expected:
                return False
            artifact = artifacts.get(step.technique)
            if artifact is None:
                return False
            expected_submodule = {
                "dsc_isothermal": "dsc.isothermal",
                "ftir_temperature": "ir.temperature_2d",
            }.get(step.step_id)
            if expected_submodule and step.parameters.get("submodule_id") != expected_submodule:
                return False
            if step.step_id in {"dsc_isothermal", "ftir_temperature"} and artifact.format != "directory":
                return False
        return True

    @staticmethod
    def _load_manifest(manifest: Mapping[str, object] | Path | str) -> Mapping[str, Any] | None:
        if isinstance(manifest, Mapping):
            return manifest
        try:
            return json.loads(Path(manifest).read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return None
