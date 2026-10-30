"""Registered project-local technique routes.

Project adapters own only request shape and recipe selection.  Provider
execution remains in :mod:`polynexus.core.agent_workflow`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
import json
import os
from pathlib import Path
from typing import Any

from polynexus.core.agent_workflow import inspect_artifact
from polynexus.core.agent_workflow.models import AnalysisRecipe, InputArtifact, RecipeProposal, RecipeStep
from polynexus.core.agent_workflow.tpae import TpaeCharacterizationWorkflow
from polynexus.core.canonical_experiments import CanonicalExperiment, default_converter_registry
from polynexus.core.canonical_experiments.models import MappingProposal
from polynexus.core.compute import RawArtifact, attach_analysis_options


def _convert_artifact(
    artifact: Any,
    *,
    technique: str,
    mapping_proposal: MappingProposal | None = None,
    portable_export: Mapping[str, object] | None = None,
):
    """Convert an inspected artifact through the shared canonical registry."""
    if portable_export is not None:
        export_path = portable_export.get("export_path")
        exporter = portable_export.get("exporter")
        if not export_path or not exporter:
            raise ValueError("portable_export requires export_path and exporter")
        raw_source = portable_export.get("raw_source") or artifact.path
        raw_identity = RawArtifact.from_path(raw_source, technique=technique)
        if artifact.sha256 and raw_identity.sha256 != artifact.sha256:
            raise ValueError("portable_export raw source hash does not match artifact")
        return default_converter_registry().convert_portable_export(
            raw_source,
            export_path,
            technique=technique,
            source_artifact_id=artifact.artifact_id,
            exporter=str(exporter),
            mapping_proposal=mapping_proposal,
        )
    return default_converter_registry().convert_path(
        artifact.path,
        technique=technique,
        source_artifact_id=artifact.artifact_id,
        mapping_proposal=mapping_proposal,
    )


def _canonical_technique(value: object) -> str:
    normalized = str(value or "").strip().lower()
    return "sec" if normalized in {"gpc", "sec/gpc"} else normalized


class SingleInputTechniqueAdapter:
    """Build a deterministic recipe for one static technique input."""

    workflow_id = "project.technique.single.v1"
    _SPECS = {
        "ir": ("ir.standard", "ir_spectrum", "supporting"),
        "waxs": ("waxs.static", "waxs_profile", "supporting"),
        "saxs": ("saxs.static", "saxs_profile", "supporting"),
        "tga": ("tga.standard", "tga_curve", "supporting"),
        "dma": ("dma.standard", "dma_curve", "supporting"),
        "rheology": ("rheology.standard", "rheology_curve", "supporting"),
        "mechanics": ("mechanics.standard", "mechanics_curve", "supporting"),
        "sec": ("sec.standard", "sec_chromatogram", "supporting"),
    }
    _NMR_SUBMODULES = frozenset({"nmr.liquid_h", "nmr.liquid_c", "nmr.solid_h", "nmr.solid_c"})

    def propose_recipe(self, manifest: Mapping[str, object] | Path | str) -> RecipeProposal:
        payload = self._load_manifest(manifest)
        if payload is None:
            return RecipeProposal(status="blocked", reason_codes=("manifest_invalid",))
        if payload.get("workflow_id") != self.workflow_id:
            return RecipeProposal(status="blocked", reason_codes=("workflow_id_mismatch",))
        technique = _canonical_technique(payload.get("technique"))
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
        try:
            portable_export = self._portable_export(payload)
        except (KeyError, TypeError, ValueError):
            return RecipeProposal(status="blocked", reason_codes=("portable_export_invalid",))
        try:
            mapping_proposal = self._mapping_proposal(payload)
        except (KeyError, TypeError, ValueError):
            return RecipeProposal(status="blocked", reason_codes=("mapping_proposal_invalid",))
        artifact = _inspect_project_artifact(paths[0], technique=technique, portable_export=portable_export)
        if artifact.inspection_status == "blocked":
            return RecipeProposal(
                status="blocked",
                reason_codes=tuple(dict.fromkeys(("artifact_blocked", *artifact.reason_codes))),
            )
        # ProjectWorkflow inventory IDs are deliberately scoped to the
        # project's logical relative path, while ``inspect_artifact`` uses the
        # absolute source path.  When a user confirms a mapping from the
        # project inventory, carry that already-validated identity into the
        # recipe instead of silently rewriting the proposal or dropping its
        # source binding.  The source hash is checked before accepting the
        # alias, so a stale/tampered inventory record remains fail-closed.
        inventory_id = payload.get("inventory_artifact_id")
        inventory_hash = payload.get("inventory_artifact_sha256")
        if (
            mapping_proposal is not None
            and inventory_id is not None
            and str(mapping_proposal.source_artifact_id) == str(inventory_id)
        ):
            if not inventory_hash or str(inventory_hash) != str(artifact.sha256):
                return RecipeProposal(status="blocked", reason_codes=("mapping_proposal_invalid",))
            artifact = replace(artifact, artifact_id=str(inventory_id))
        try:
            outcome = _convert_artifact(
                artifact,
                technique=technique,
                mapping_proposal=mapping_proposal,
                portable_export=portable_export,
            )
        except (OSError, TypeError, ValueError):
            return RecipeProposal(status="blocked", reason_codes=("portable_export_invalid",))
        if outcome.status != "ready" or outcome.template is None:
            return RecipeProposal(status="blocked", reason_codes=outcome.reason_codes)
        try:
            canonical_template, analysis_options = attach_analysis_options(
                outcome.template,
                technique=technique,
                options=self._analysis_options(payload),
            )
        except (KeyError, TypeError, ValueError):
            return RecipeProposal(
                status="blocked", reason_codes=("analysis_options_invalid",)
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
                    parameters={
                        "submodule_id": submodule_id,
                        "canonical_converter": outcome.record.conversion_id,
                        "canonical_template": canonical_template.to_dict(),
                        **(
                            {"analysis_options": analysis_options}
                            if analysis_options
                            else {}
                        ),
                        **({"portable_export": dict(portable_export)} if portable_export is not None else {}),
                    },
                    parameter_sources={
                        "submodule_id": "registered_project_recipe",
                        "canonical_converter": "registered_canonical_converter",
                        "canonical_template": "registered_canonical_converter",
                        **(
                            {"analysis_options": "explicit_project_request"}
                            if analysis_options
                            else {}
                        ),
                        **({"portable_export": "declared_portable_export"} if portable_export is not None else {}),
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
        if not cls._portable_export_declaration_is_valid(step, artifact):
            return False
        return cls._has_matching_canonical_template(step, artifact)

    @staticmethod
    def _portable_export_declaration_is_valid(step: RecipeStep, artifact: Any) -> bool:
        """Validate the persisted portable declaration before replay/provider use."""
        raw = step.parameters.get("portable_export")
        if raw is None:
            return True
        if not isinstance(raw, Mapping):
            return False
        export_path = raw.get("export_path")
        exporter = raw.get("exporter")
        if not isinstance(export_path, str) or not export_path.strip():
            return False
        if not isinstance(exporter, str) or not exporter.strip():
            return False
        raw_source = raw.get("raw_source")
        if raw_source not in (None, "") and not isinstance(raw_source, str):
            return False
        if raw_source:
            try:
                if Path(raw_source).expanduser().resolve(strict=False) != Path(artifact.path).expanduser().resolve(strict=False):
                    return False
            except (OSError, TypeError, ValueError):
                return False
        return True

    @staticmethod
    def _has_matching_canonical_template(step: RecipeStep, artifact: Any) -> bool:
        payload = step.parameters.get("canonical_template")
        if not isinstance(payload, Mapping):
            return False
        try:
            template = CanonicalExperiment.from_dict(payload)
        except (KeyError, TypeError, ValueError):
            return False
        if not (
            template.source_artifact_id == artifact.artifact_id
            and step.parameters.get("canonical_converter")
            == template.conversion_record.conversion_id
        ):
            return False
        analysis_options = step.parameters.get("analysis_options")
        if analysis_options is None:
            return True
        if not isinstance(analysis_options, Mapping):
            return False
        try:
            attached, normalized = attach_analysis_options(
                template,
                technique=artifact.technique,
                options=analysis_options,
            )
        except (KeyError, TypeError, ValueError):
            return False
        return bool(normalized) and attached.content_hash == template.content_hash

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

    @staticmethod
    def _analysis_options(payload: Mapping[str, object]) -> Mapping[str, Any]:
        raw = payload.get("analysis_options")
        if raw is None:
            return {}
        if not isinstance(raw, Mapping):
            raise TypeError("analysis_options must be a mapping")
        return dict(raw)

    @staticmethod
    def _portable_export(payload: Mapping[str, object]) -> Mapping[str, object] | None:
        raw = payload.get("portable_export")
        if raw is None:
            return None
        if not isinstance(raw, Mapping):
            raise TypeError("portable_export must be a mapping")
        export_path = raw.get("export_path")
        exporter = raw.get("exporter")
        if not isinstance(export_path, (str, Path)) or not str(export_path).strip():
            raise ValueError("portable_export export_path is required")
        if not isinstance(exporter, str) or not exporter.strip():
            raise ValueError("portable_export exporter is required")
        raw_source = raw.get("raw_source")
        if raw_source is not None and not isinstance(raw_source, (str, Path)):
            raise ValueError("portable_export raw_source must be a path")
        return {
            "raw_source": str(raw_source) if raw_source is not None else "",
            "export_path": str(export_path),
            "exporter": exporter.strip(),
        }


def _portable_exports(
    payload: Mapping[str, object], paths: Sequence[str]
) -> tuple[Mapping[str, object] | None, ...]:
    """Normalize a one-to-one raw-to-export declaration for a series.

    A sequence must name each source explicitly.  This keeps a manifest safe
    when the adapter normalizes its artifact order.  A mapping may instead use
    an exact source path (or a unique file name) as the raw binding key.
    """
    raw = payload.get("portable_exports")
    if raw is None:
        return (None,) * len(paths)
    source_keys = tuple(_portable_source_key(path) for path in paths)
    if len(set(source_keys)) != len(source_keys):
        raise ValueError("series artifact paths must be unique")
    declarations: list[Mapping[str, object] | None]
    if isinstance(raw, Mapping):
        declarations = [None] * len(paths)
        mapping_items = tuple((str(key), value) for key, value in raw.items())
        used_keys: set[str] = set()
        unique_names = {
            Path(path).name.casefold()
            for path in paths
            if sum(Path(candidate).name.casefold() == Path(path).name.casefold() for candidate in paths) == 1
        }
        for index, path in enumerate(paths):
            source_key = source_keys[index]
            source_name = Path(path).name
            matching_items = [
                (key, value)
                for key, value in mapping_items
                if _portable_source_key(key) == source_key
                or (
                    key.casefold() == source_name.casefold()
                    and source_name.casefold() in unique_names
                )
            ]
            if len(matching_items) != 1:
                raise ValueError("portable_exports must bind each series artifact exactly once")
            key, value = matching_items[0]
            used_keys.add(key)
            declaration = SingleInputTechniqueAdapter._portable_export(
                {"portable_export": value}
            )
            declared_source = declaration.get("raw_source")
            if declared_source and _portable_source_key(declared_source) != source_key:
                raise ValueError("portable_export raw_source does not match mapping key")
            declarations[index] = {
                **declaration,
                "raw_source": str(Path(path).expanduser().resolve(strict=False)),
            }
        if len(used_keys) != len(mapping_items):
            raise ValueError("portable_exports contains an unbound declaration")
    elif isinstance(raw, Sequence) and not isinstance(raw, (str, bytes, bytearray)):
        declarations = [None] * len(paths)
        for item in raw:
            declaration = SingleInputTechniqueAdapter._portable_export(
                {"portable_export": item}
            )
            raw_source = declaration.get("raw_source")
            if not raw_source:
                raise ValueError("series portable_export raw_source is required")
            try:
                index = source_keys.index(_portable_source_key(raw_source))
            except ValueError as exc:
                raise ValueError("portable_export raw_source is not a series artifact") from exc
            if declarations[index] is not None:
                raise ValueError("portable_exports binds a series artifact more than once")
            declarations[index] = declaration
    else:
        raise TypeError("portable_exports must be a sequence or mapping")
    if len(declarations) != len(paths) or any(item is None for item in declarations):
        raise ValueError("portable_exports must provide one declaration per series artifact")
    export_keys = tuple(
        _portable_source_key(str(declaration["export_path"]))
        for declaration in declarations
        if declaration is not None
    )
    if len(set(export_keys)) != len(export_keys):
        raise ValueError("portable_exports cannot reuse one export for multiple artifacts")
    return tuple(declaration for declaration in declarations if declaration is not None)


def _portable_source_key(value: object) -> str:
    """Return a platform-aware stable path key without requiring file access."""
    if not isinstance(value, (str, Path)) or not str(value).strip():
        raise ValueError("portable export source must be a path")
    return os.path.normcase(
        str(Path(value).expanduser().resolve(strict=False))
    )


def _inspect_project_artifact(
    path: str | Path,
    *,
    technique: str,
    portable_export: Mapping[str, object] | None,
) -> InputArtifact:
    """Allow an opaque raw source only when a portable export is declared."""
    artifact = inspect_artifact(path, technique=technique)
    if artifact.inspection_status != "blocked" or portable_export is None:
        return artifact
    raw_source = portable_export.get("raw_source") or path
    try:
        if Path(raw_source).expanduser().resolve(strict=False) != Path(path).expanduser().resolve(strict=False):
            return artifact
    except (OSError, TypeError, ValueError):
        return artifact
    try:
        raw = RawArtifact.from_path(raw_source, technique=technique)
    except (OSError, TypeError, ValueError):
        return artifact
    if raw.sha256 != artifact.sha256 and artifact.sha256 is not None:
        return artifact
    return InputArtifact(
        artifact_id=raw.artifact_id,
        path=raw.path,
        technique=technique,
        format=raw.format,
        sha256=raw.sha256,
        header_facts={"portable_export": True},
        inspection_status="review_required",
        reason_codes=("portable_export_source_opaque", *artifact.reason_codes),
    )


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
        technique = _canonical_technique(payload.get("technique"))
        spec = self._SPECS.get(technique)
        if spec is None:
            return RecipeProposal(status="blocked", reason_codes=("technique_unsupported",))
        paths = tuple(sorted(SingleInputTechniqueAdapter._paths(payload), key=lambda value: Path(value).as_posix().lower()))
        if len(paths) < 2:
            return RecipeProposal(status="blocked", reason_codes=("series_requires_multiple_artifacts",))
        try:
            portable_exports = _portable_exports(payload, paths)
        except (KeyError, TypeError, ValueError):
            return RecipeProposal(status="blocked", reason_codes=("portable_export_invalid",))
        artifacts = tuple(
            _inspect_project_artifact(
                path,
                technique=technique,
                portable_export=portable_exports[index],
            )
            for index, path in enumerate(paths)
        )
        if any(artifact.technique != technique for artifact in artifacts):
            return RecipeProposal(status="blocked", reason_codes=("series_technique_mismatch",))
        blocked = tuple(code for artifact in artifacts if artifact.inspection_status == "blocked" for code in artifact.reason_codes)
        if blocked:
            return RecipeProposal(status="blocked", reason_codes=tuple(dict.fromkeys(("artifact_blocked", *blocked))))
        outcomes = tuple(
            _convert_artifact(
                artifact,
                technique=technique,
                portable_export=portable_exports[index],
            )
            for index, artifact in enumerate(artifacts)
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
                    **(
                        {"portable_export": dict(portable_exports[index])}
                        if portable_exports[index] is not None
                        else {}
                    ),
                },
                parameter_sources={
                    "submodule_id": "registered_project_recipe",
                    "artifact_index": "series_path_order",
                    "source_order": "series_path_order",
                    "canonical_converter": "registered_canonical_converter",
                    "canonical_template": "registered_canonical_converter",
                    **(
                        {"portable_export": "declared_portable_export"}
                        if portable_exports[index] is not None
                        else {}
                    ),
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
            and SingleInputTechniqueAdapter._portable_export_declaration_is_valid(
                step, recipe.artifacts[index]
            )
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
            technique = _canonical_technique(raw_technique)
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
