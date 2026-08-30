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
from polynexus.core.agent_workflow.tpae import TpaeCharacterizationWorkflow
from polynexus.core.canonical_experiments import CanonicalExperiment, default_converter_registry
from polynexus.core.canonical_experiments.models import MappingProposal


def _convert_artifact(
    artifact: Any,
    *,
    technique: str,
    mapping_proposal: MappingProposal | None = None,
):
    """Convert an inspected artifact through the shared canonical registry."""
    return default_converter_registry().convert_path(
        artifact.path,
        technique=technique,
        source_artifact_id=artifact.artifact_id,
        mapping_proposal=mapping_proposal,
    )


class SingleInputTechniqueAdapter:
    """Build a deterministic recipe for one static technique input."""

    workflow_id = "project.technique.single.v1"
    _SPECS = {
        "ir": ("ir.standard", "ir_spectrum", "supporting"),
        "waxs": ("waxs.static", "waxs_profile", "supporting"),
        "saxs": ("saxs.static", "saxs_profile", "supporting"),
    }
    _NMR_SUBMODULES = frozenset({"nmr.liquid_h", "nmr.liquid_c", "nmr.solid_h", "nmr.solid_c"})

    def propose_recipe(self, manifest: Mapping[str, object] | Path | str) -> RecipeProposal:
        payload = self._load_manifest(manifest)
        if payload is None:
            return RecipeProposal(status="blocked", reason_codes=("manifest_invalid",))
        if payload.get("workflow_id") != self.workflow_id:
            return RecipeProposal(status="blocked", reason_codes=("workflow_id_mismatch",))
        technique = str(payload.get("technique") or "").strip().lower()
        if technique == "nmr":
            submodule_id = str(payload.get("submodule_id") or payload.get("submodule") or "").strip().lower()
            if submodule_id in {value.removeprefix("nmr.") for value in self._NMR_SUBMODULES}:
                submodule_id = f"nmr.{submodule_id}"
            if submodule_id not in self._NMR_SUBMODULES:
                return RecipeProposal(status="blocked", reason_codes=("nmr_submodule_required",))
            spec = (submodule_id, "nmr_spectrum", "supporting")
        else:
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
        try:
            mapping_proposal = self._mapping_proposal(payload)
        except (KeyError, TypeError, ValueError):
            return RecipeProposal(status="blocked", reason_codes=("mapping_proposal_invalid",))
        outcome = _convert_artifact(
            artifact,
            technique=technique,
            mapping_proposal=mapping_proposal,
        )
        if outcome.status != "ready" or outcome.template is None:
            return RecipeProposal(status="blocked", reason_codes=outcome.reason_codes)
        submodule_id, step_id, role = spec
        recipe = AnalysisRecipe.create(
            workflow_id=self.workflow_id,
            artifacts=(artifact,),
            steps=(
                RecipeStep(
                    step_id=step_id,
                    technique=technique,
                    evidence_role=role,
                    parameters={
                        "submodule_id": submodule_id,
                        "canonical_converter": outcome.record.conversion_id,
                        "canonical_template": outcome.template.to_dict(),
                    },
                    parameter_sources={
                        "submodule_id": "registered_project_recipe",
                        "canonical_converter": "registered_canonical_converter",
                        "canonical_template": "registered_canonical_converter",
                    },
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
        if artifact.technique == "nmr":
            submodule_id = str(step.parameters.get("submodule_id") or "").strip().lower()
            spec = (submodule_id, "nmr_spectrum", "supporting") if submodule_id in cls._NMR_SUBMODULES else None
        else:
            spec = cls._SPECS.get(artifact.technique)
        if spec is None:
            return False
        submodule_id, step_id, role = spec
        if not (
            step.step_id == step_id
            and step.technique == artifact.technique
            and step.evidence_role == role
            and step.parameters.get("submodule_id") == submodule_id
        ):
            return False
        return cls._has_matching_canonical_template(step, artifact)

    @staticmethod
    def _has_matching_canonical_template(step: RecipeStep, artifact: Any) -> bool:
        payload = step.parameters.get("canonical_template")
        if not isinstance(payload, Mapping):
            return False
        try:
            template = CanonicalExperiment.from_dict(payload)
        except (KeyError, TypeError, ValueError):
            return False
        return (
            template.source_artifact_id == artifact.artifact_id
            and step.parameters.get("canonical_converter") == template.conversion_record.conversion_id
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

    @staticmethod
    def _mapping_proposal(payload: Mapping[str, object]) -> MappingProposal | None:
        raw = payload.get("mapping_proposal")
        if raw is None:
            return None
        if not isinstance(raw, Mapping):
            raise TypeError("mapping_proposal must be a mapping")
        return MappingProposal.from_dict(raw)


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
        artifacts = tuple(inspect_artifact(path, technique=technique) for path in paths)
        if any(artifact.technique != technique for artifact in artifacts):
            return RecipeProposal(status="blocked", reason_codes=("series_technique_mismatch",))
        blocked = tuple(code for artifact in artifacts if artifact.inspection_status == "blocked" for code in artifact.reason_codes)
        if blocked:
            return RecipeProposal(status="blocked", reason_codes=tuple(dict.fromkeys(("artifact_blocked", *blocked))))
        outcomes = tuple(
            _convert_artifact(artifact, technique=technique)
            for artifact in artifacts
        )
        blocked_outcomes = tuple(
            reason
            for outcome in outcomes
            if outcome.status != "ready" or outcome.template is None
            for reason in outcome.reason_codes
        )
        if blocked_outcomes:
            return RecipeProposal(status="blocked", reason_codes=tuple(dict.fromkeys(blocked_outcomes)))
        submodule_id, step_id, role = spec
        steps = tuple(
            RecipeStep(
                step_id=f"{step_id}.{index:03d}",
                technique=technique,
                evidence_role=role,
                parameters={
                    "submodule_id": submodule_id,
                    "artifact_index": index,
                    "source_order": index,
                    "canonical_converter": outcomes[index].record.conversion_id,
                    "canonical_template": outcomes[index].template.to_dict(),
                },
                parameter_sources={
                    "submodule_id": "registered_project_recipe",
                    "artifact_index": "series_path_order",
                    "source_order": "series_path_order",
                    "canonical_converter": "registered_canonical_converter",
                    "canonical_template": "registered_canonical_converter",
                },
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
            and SingleInputTechniqueAdapter._has_matching_canonical_template(step, recipe.artifacts[index])
            for index, step in enumerate(recipe.steps)
        )


class IRTemperatureSeriesAdapter:
    """Build one directory-bound recipe for an IR temperature sequence."""

    workflow_id = "project.ir.temperature-series.v1"

    def propose_recipe(self, manifest: Mapping[str, object] | Path | str) -> RecipeProposal:
        payload = SingleInputTechniqueAdapter._load_manifest(manifest)
        if payload is None or payload.get("workflow_id") != self.workflow_id:
            return RecipeProposal(status="blocked", reason_codes=("workflow_id_mismatch",))
        raw_path = payload.get("path")
        if not raw_path:
            paths = SingleInputTechniqueAdapter._paths(payload)
            raw_path = paths[0] if len(paths) == 1 else None
        if not raw_path:
            return RecipeProposal(status="blocked", reason_codes=("series_directory_missing",))
        artifact = inspect_artifact(raw_path, technique="ir")
        if artifact.format != "directory" or artifact.inspection_status == "blocked":
            return RecipeProposal(
                status="blocked",
                reason_codes=tuple(dict.fromkeys(("artifact_blocked", *artifact.reason_codes))),
            )
        outcome = _convert_artifact(artifact, technique="ir")
        if outcome.status != "ready" or outcome.template is None:
            return RecipeProposal(status="blocked", reason_codes=outcome.reason_codes)
        if outcome.template.template_id != "ir.temperature_series.v1":
            return RecipeProposal(status="blocked", reason_codes=("temperature_series_template_missing",))
        step = RecipeStep(
            step_id="ir_temperature_series",
            technique="ir",
            evidence_role="supporting",
            parameters={
                "submodule_id": "ir.temperature_2d",
                "canonical_converter": outcome.record.conversion_id,
                "canonical_template": outcome.template.to_dict(),
            },
            parameter_sources={
                "submodule_id": "registered_project_recipe",
                "canonical_converter": "registered_canonical_converter",
                "canonical_template": "registered_canonical_converter",
            },
        )
        status = "review_required" if artifact.inspection_status == "review_required" else "ready"
        return RecipeProposal(
            status=status,
            recipe=AnalysisRecipe.create(
                workflow_id=self.workflow_id,
                artifacts=(artifact,),
                steps=(step,),
            ),
        )

    @classmethod
    def is_valid_recipe(cls, recipe: AnalysisRecipe) -> bool:
        if recipe.workflow_id != cls.workflow_id or len(recipe.artifacts) != 1 or len(recipe.steps) != 1:
            return False
        artifact = recipe.artifacts[0]
        step = recipe.steps[0]
        if artifact.technique != "ir" or artifact.format != "directory":
            return False
        if step.step_id != "ir_temperature_series" or step.technique != "ir" or step.evidence_role != "supporting":
            return False
        if step.parameters.get("submodule_id") != "ir.temperature_2d":
            return False
        if not SingleInputTechniqueAdapter._has_matching_canonical_template(step, artifact):
            return False
        payload = step.parameters.get("canonical_template")
        return isinstance(payload, Mapping) and payload.get("template_id") == "ir.temperature_series.v1"


class MixedTechniqueAdapter:
    """Compose existing technique recipes into one request-level recipe."""

    workflow_id = "project.technique.composite.v1"

    def __init__(self) -> None:
        self._single = SingleInputTechniqueAdapter()
        self._series = TechniqueSeriesAdapter()
        self._ir_temperature_series = IRTemperatureSeriesAdapter()
        self._dsc = TpaeCharacterizationWorkflow()

    def propose_recipe(self, manifest: Mapping[str, object] | Path | str) -> RecipeProposal:
        payload = SingleInputTechniqueAdapter._load_manifest(manifest)
        if payload is None or payload.get("workflow_id") != self.workflow_id:
            return RecipeProposal(status="blocked", reason_codes=("workflow_id_mismatch",))
        raw_components = payload.get("components")
        if not isinstance(raw_components, Mapping) or not raw_components:
            return RecipeProposal(status="blocked", reason_codes=("components_missing",))

        proposals: list[tuple[str, AnalysisRecipe]] = []
        reasons: list[str] = []
        review_required = False
        for raw_technique, raw_paths in sorted(raw_components.items(), key=lambda item: str(item[0])):
            technique = str(raw_technique).strip().lower()
            component_payload = raw_paths if isinstance(raw_paths, Mapping) else {"paths": raw_paths}
            paths = SingleInputTechniqueAdapter._paths(component_payload)
            if not paths:
                reasons.append(f"{technique}_artifact_missing")
                continue
            if technique == "dsc":
                if len(paths) != 1:
                    reasons.append("dsc_source_count_invalid")
                    continue
                proposal = self._dsc.propose_recipe({
                    "workflow_id": self._dsc.workflow_id,
                    "artifacts": {"dsc_isothermal": {"path": paths[0], "technique": "dsc"}},
                })
            elif technique == "ir" and len(paths) == 1 and Path(paths[0]).is_dir():
                proposal = self._ir_temperature_series.propose_recipe({
                    "workflow_id": IRTemperatureSeriesAdapter.workflow_id,
                    "path": paths[0],
                })
            elif len(paths) > 1:
                proposal = self._series.propose_recipe({
                    "workflow_id": self._series.workflow_id,
                    "technique": technique,
                    "paths": list(paths),
                })
            else:
                proposal = self._single.propose_recipe({
                    "workflow_id": self._single.workflow_id,
                    "technique": technique,
                    "paths": list(paths),
                    **({"submodule_id": str(component_payload["submodule_id"])} if technique == "nmr" and component_payload.get("submodule_id") else {}),
                })
            if proposal.recipe is None:
                reasons.extend(proposal.reason_codes or (f"{technique}_route_blocked",))
                continue
            proposals.append((technique, proposal.recipe))
            review_required = review_required or proposal.status == "review_required"

        if reasons:
            return RecipeProposal(status="blocked", reason_codes=tuple(dict.fromkeys(reasons)))
        if not proposals:
            return RecipeProposal(status="blocked", reason_codes=("components_missing",))
        artifacts = []
        steps = []
        for _, recipe in proposals:
            offset = len(artifacts)
            artifacts.extend(recipe.artifacts)
            for step in recipe.steps:
                parameters = dict(step.parameters)
                artifact_index = parameters.get("artifact_index")
                if isinstance(artifact_index, int) and not isinstance(artifact_index, bool):
                    parameters["artifact_index"] = offset + artifact_index
                steps.append(
                    RecipeStep(
                        step_id=step.step_id,
                        technique=step.technique,
                        evidence_role=step.evidence_role,
                        parameters=parameters,
                        parameter_sources=step.parameter_sources,
                    )
                )
        recipe = AnalysisRecipe.create(
            workflow_id=self.workflow_id,
            artifacts=tuple(artifacts),
            steps=tuple(steps),
        )
        return RecipeProposal(
            status="review_required" if review_required else "ready",
            recipe=recipe,
        )

    @classmethod
    def is_valid_recipe(cls, recipe: AnalysisRecipe) -> bool:
        if recipe.workflow_id != cls.workflow_id or not recipe.artifacts or not recipe.steps:
            return False
        if len({artifact.artifact_id for artifact in recipe.artifacts}) != len(recipe.artifacts):
            return False
        if len({step.step_id for step in recipe.steps}) != len(recipe.steps):
            return False
        # The merged recipe must have one component per technique. Reconstruct
        # each component and delegate validation to its existing adapter.
        artifacts_by_technique: dict[str, list[tuple[int, Any]]] = {}
        for index, artifact in enumerate(recipe.artifacts):
            artifacts_by_technique.setdefault(artifact.technique, []).append((index, artifact))
        steps_by_technique: dict[str, list[RecipeStep]] = {}
        for step in recipe.steps:
            steps_by_technique.setdefault(step.technique, []).append(step)
        if set(artifacts_by_technique) != set(steps_by_technique):
            return False
        for technique, indexed_artifacts in artifacts_by_technique.items():
            component_steps = steps_by_technique[technique]
            local_artifacts = tuple(artifact for _, artifact in indexed_artifacts)
            index_map = {global_index: local_index for local_index, (global_index, _) in enumerate(indexed_artifacts)}
            local_steps = []
            for step in component_steps:
                parameters = dict(step.parameters)
                global_index = parameters.get("artifact_index")
                if isinstance(global_index, int) and not isinstance(global_index, bool):
                    if global_index not in index_map:
                        return False
                    parameters["artifact_index"] = index_map[global_index]
                local_steps.append(RecipeStep(
                    step_id=step.step_id,
                    technique=step.technique,
                    evidence_role=step.evidence_role,
                    parameters=parameters,
                    parameter_sources=step.parameter_sources,
                ))
            if technique == "dsc":
                valid = TpaeCharacterizationWorkflow.is_valid_recipe(
                    AnalysisRecipe.create(
                        workflow_id=TpaeCharacterizationWorkflow.workflow_id,
                        artifacts=local_artifacts,
                        steps=tuple(local_steps),
                    )
                )
            elif (
                technique == "ir"
                and len(local_artifacts) == 1
                and local_artifacts[0].format == "directory"
                and len(local_steps) == 1
                and local_steps[0].parameters.get("submodule_id") == "ir.temperature_2d"
            ):
                valid = IRTemperatureSeriesAdapter.is_valid_recipe(
                    AnalysisRecipe.create(
                        workflow_id=IRTemperatureSeriesAdapter.workflow_id,
                        artifacts=local_artifacts,
                        steps=tuple(local_steps),
                    )
                )
            elif len(local_artifacts) > 1:
                valid = TechniqueSeriesAdapter.is_valid_recipe(
                    AnalysisRecipe.create(
                        workflow_id=TechniqueSeriesAdapter.workflow_id,
                        artifacts=local_artifacts,
                        steps=tuple(local_steps),
                    )
                )
            else:
                valid = SingleInputTechniqueAdapter.is_valid_recipe(
                    AnalysisRecipe.create(
                        workflow_id=SingleInputTechniqueAdapter.workflow_id,
                        artifacts=local_artifacts,
                        steps=tuple(local_steps),
                    )
                )
            if not valid:
                return False
        return True


__all__ = ["IRTemperatureSeriesAdapter", "MixedTechniqueAdapter", "SingleInputTechniqueAdapter", "TechniqueSeriesAdapter"]
