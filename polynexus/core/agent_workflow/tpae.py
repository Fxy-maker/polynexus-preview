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
            artifact = inspect_artifact(raw["path"], technique=str(raw.get("technique") or technique))
            artifacts.append(artifact)
            steps.append(RecipeStep(step_id=step_id, technique=technique, evidence_role=evidence_role))
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

    @staticmethod
    def _load_manifest(manifest: Mapping[str, object] | Path | str) -> Mapping[str, Any] | None:
        if isinstance(manifest, Mapping):
            return manifest
        try:
            return json.loads(Path(manifest).read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return None
