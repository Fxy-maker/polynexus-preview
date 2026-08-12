"""Registered project-local technique routes.

Project adapters own only request shape and recipe selection.  Provider
execution remains in :mod:`polynexus.core.agent_workflow`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from pathlib import Path
from typing import Any

from polynexus.core.agent_workflow import inspect_artifact
from polynexus.core.agent_workflow.models import AnalysisRecipe, RecipeProposal, RecipeStep


class SingleInputTechniqueAdapter:
    """Build a deterministic recipe for one static technique input."""

    workflow_id = "project.technique.single.v1"
    _SPECS = {
        "ir": ("ir.standard", "ir_spectrum", "supporting"),
        "waxs": ("waxs.static", "waxs_profile", "supporting"),
        "saxs": ("saxs.static", "saxs_profile", "supporting"),
    }

    def propose_recipe(self, manifest: Mapping[str, object] | Path | str) -> RecipeProposal:
        payload = self._load_manifest(manifest)
        if payload is None:
            return RecipeProposal(status="blocked", reason_codes=("manifest_invalid",))
        if payload.get("workflow_id") != self.workflow_id:
            return RecipeProposal(status="blocked", reason_codes=("workflow_id_mismatch",))
        technique = str(payload.get("technique") or "").strip().lower()
        spec = self._SPECS.get(technique)
        if spec is None:
            return RecipeProposal(status="blocked", reason_codes=("technique_unsupported",))
        paths = self._paths(payload)
        if not paths:
            return RecipeProposal(status="blocked", reason_codes=("artifact_missing",))
        if len(paths) != 1:
            return RecipeProposal(status="blocked", reason_codes=("multiple_artifacts",))
        artifact = inspect_artifact(paths[0], technique=technique)
        if artifact.inspection_status == "blocked":
            return RecipeProposal(
                status="blocked",
                reason_codes=tuple(dict.fromkeys(("artifact_blocked", *artifact.reason_codes))),
            )
        submodule_id, step_id, role = spec
        recipe = AnalysisRecipe.create(
            workflow_id=self.workflow_id,
            artifacts=(artifact,),
            steps=(
                RecipeStep(
                    step_id=step_id,
                    technique=technique,
                    evidence_role=role,
                    parameters={"submodule_id": submodule_id},
                    parameter_sources={"submodule_id": "registered_project_recipe"},
                ),
            ),
        )
        status = "review_required" if artifact.inspection_status == "review_required" else "ready"
        return RecipeProposal(status=status, recipe=recipe)

    @classmethod
    def is_valid_recipe(cls, recipe: AnalysisRecipe) -> bool:
        if recipe.workflow_id != cls.workflow_id or len(recipe.artifacts) != 1 or len(recipe.steps) != 1:
            return False
        artifact = recipe.artifacts[0]
        step = recipe.steps[0]
        spec = cls._SPECS.get(artifact.technique)
        if spec is None:
            return False
        submodule_id, step_id, role = spec
        return (
            step.step_id == step_id
            and step.technique == artifact.technique
            and step.evidence_role == role
            and step.parameters.get("submodule_id") == submodule_id
        )

    @staticmethod
    def _load_manifest(manifest: Mapping[str, object] | Path | str) -> Mapping[str, Any] | None:
        if isinstance(manifest, Mapping):
            return manifest
        try:
            payload = json.loads(Path(manifest).read_text(encoding="utf-8"))
        except (OSError, TypeError, ValueError):
            return None
        return payload if isinstance(payload, Mapping) else None

    @staticmethod
    def _paths(payload: Mapping[str, object]) -> tuple[str, ...]:
        raw = payload.get("paths", payload.get("artifact_paths"))
        if raw is None and payload.get("path"):
            raw = (payload["path"],)
        if raw is None:
            artifact = payload.get("artifact")
            if isinstance(artifact, Mapping) and artifact.get("path"):
                raw = (artifact["path"],)
        if isinstance(raw, (str, Path)):
            return (str(raw),)
        if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes, bytearray)):
            return tuple(str(item) for item in raw if item)
        return ()


class TechniqueSeriesAdapter:
    """Build one provider step per ordered artifact in a same-technique series."""

    workflow_id = "project.technique.series.v1"
    _SPECS = SingleInputTechniqueAdapter._SPECS

    def propose_recipe(self, manifest: Mapping[str, object] | Path | str) -> RecipeProposal:
        payload = SingleInputTechniqueAdapter._load_manifest(manifest)
        if payload is None:
            return RecipeProposal(status="blocked", reason_codes=("manifest_invalid",))
        if payload.get("workflow_id") != self.workflow_id:
            return RecipeProposal(status="blocked", reason_codes=("workflow_id_mismatch",))
        technique = str(payload.get("technique") or "").strip().lower()
        spec = self._SPECS.get(technique)
        if spec is None:
            return RecipeProposal(status="blocked", reason_codes=("technique_unsupported",))
        paths = tuple(sorted(SingleInputTechniqueAdapter._paths(payload), key=lambda value: Path(value).as_posix().lower()))
        if len(paths) < 2:
            return RecipeProposal(status="blocked", reason_codes=("series_requires_multiple_artifacts",))
        technique_markers = {marker for path in paths for marker in ("ir", "ftir", "waxs", "saxs") if marker in " ".join(Path(path).parts).lower()}
        if any(marker in {"ir", "ftir"} for marker in technique_markers) and technique != "ir":
            return RecipeProposal(status="blocked", reason_codes=("series_technique_mismatch",))
        if "waxs" in technique_markers and technique != "waxs":
            return RecipeProposal(status="blocked", reason_codes=("series_technique_mismatch",))
        if "saxs" in technique_markers and technique != "saxs":
            return RecipeProposal(status="blocked", reason_codes=("series_technique_mismatch",))
        artifacts = tuple(inspect_artifact(path, technique=technique) for path in paths)
        if any(artifact.technique != technique for artifact in artifacts):
            return RecipeProposal(status="blocked", reason_codes=("series_technique_mismatch",))
        blocked = tuple(code for artifact in artifacts if artifact.inspection_status == "blocked" for code in artifact.reason_codes)
        if blocked:
            return RecipeProposal(status="blocked", reason_codes=tuple(dict.fromkeys(("artifact_blocked", *blocked))))
        submodule_id, step_id, role = spec
        steps = tuple(
            RecipeStep(
                step_id=f"{step_id}.{index:03d}",
                technique=technique,
                evidence_role=role,
                parameters={"submodule_id": submodule_id, "artifact_index": index, "source_order": index},
                parameter_sources={"submodule_id": "registered_project_recipe", "artifact_index": "series_path_order", "source_order": "series_path_order"},
            )
            for index in range(len(artifacts))
        )
        status = "review_required" if any(artifact.inspection_status == "review_required" for artifact in artifacts) else "ready"
        return RecipeProposal(status=status, recipe=AnalysisRecipe.create(workflow_id=self.workflow_id, artifacts=artifacts, steps=steps))

    @classmethod
    def is_valid_recipe(cls, recipe: AnalysisRecipe) -> bool:
        if recipe.workflow_id != cls.workflow_id or len(recipe.artifacts) < 2 or len(recipe.steps) != len(recipe.artifacts):
            return False
        technique = recipe.artifacts[0].technique
        spec = cls._SPECS.get(technique)
        if spec is None or any(artifact.technique != technique for artifact in recipe.artifacts):
            return False
        submodule_id, step_prefix, role = spec
        return all(
            step.step_id == f"{step_prefix}.{index:03d}"
            and step.technique == technique
            and step.evidence_role == role
            and step.parameters.get("submodule_id") == submodule_id
            and step.parameters.get("artifact_index") == index
            and step.parameters.get("source_order") == index
            for index, step in enumerate(recipe.steps)
        )


__all__ = ["SingleInputTechniqueAdapter", "TechniqueSeriesAdapter"]
