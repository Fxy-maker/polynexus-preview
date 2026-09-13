"""Direct-run adapter from the public compute contracts to legacy engines."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import copy
from dataclasses import is_dataclass, replace
import json
import math
from pathlib import Path
import re
from typing import Any, Callable

from ..engine import get_engine
from ..project_context import ProjectContext
from ..ai_platform.contracts import ProviderResultInput
from ..input_formats import inspect_format
from ..canonical_experiments import CapabilityExecutor, CanonicalExperiment, default_converter_registry
from .models import AnalysisPlan, CanonicalDataset, ComputeResult, ComputeRun, RawArtifact
from .method_sensitivity import sensitivities_from_metrics


_SUPPORTED_PIPELINE_OPTIONS = frozenset(
    {
        "skip_to",
        "mask_edit_candidate",
        "method_sensitivity",
        "rheology_analysis",
        "rheology_advanced",
        "sec_analysis",
        "tga_kinetics",
        "dma_tts",
        "mechanics_analysis",
        "mechanics_advanced",
    }
)
_SUPPORTED_SKIP_TO_VALUES = frozenset({"preprocess", "analyze", "plot"})
_ANALYSIS_OPTION_TECHNIQUES = {
    "tga_kinetics": "tga",
    "dma_tts": "dma",
    "rheology_analysis": "rheology",
    "rheology_advanced": "rheology",
    "mechanics_analysis": "mechanics",
    "mechanics_advanced": "mechanics",
    "sec_analysis": "sec",
}


def _safe_technique(value: object) -> str | None:
    """Return one normalized technique string without coercing arbitrary objects."""
    if not isinstance(value, str):
        return None
    normalized = str.lower(str.strip(value))
    aliases = {"ftir": "ir", "gpc": "sec", "sec/gpc": "sec"}
    normalized = aliases.get(normalized, normalized)
    return normalized or None


def _resolve_output_dir(value: object) -> Path | None:
    """Return a canonical output path only when normalization is safe."""
    try:
        if "\x00" in str(value):
            return None
        return Path(value).expanduser().resolve(strict=False)
    except Exception:
        return None


def _normalize_pipeline_options(
    value: object,
) -> tuple[dict[str, Any] | None, str | None]:
    """Return supported JSON-safe direct-pipeline options or a public reason."""
    if value is None:
        return {}, None
    if not isinstance(value, Mapping):
        return None, "pipeline_option_invalid"
    try:
        options = dict(value)
        if any(name not in _SUPPORTED_PIPELINE_OPTIONS for name in options):
            return None, "pipeline_option_unsupported"
        skip_to = options.get("skip_to")
        if "skip_to" in options and not (
            skip_to is None
            or (isinstance(skip_to, str) and skip_to in _SUPPORTED_SKIP_TO_VALUES)
        ):
            return None, "pipeline_option_invalid"
        mask_edit_candidate = options.get("mask_edit_candidate")
        if "mask_edit_candidate" in options and not _is_json_safe(
            mask_edit_candidate
        ):
            return None, "pipeline_option_invalid"
        method_sensitivity = options.get("method_sensitivity")
        if "method_sensitivity" in options and not _valid_method_sensitivity_request(method_sensitivity):
            return None, "pipeline_option_invalid"
        rheology_analysis = options.get("rheology_analysis")
        if "rheology_analysis" in options and (
            not isinstance(rheology_analysis, Mapping) or not _is_json_safe(rheology_analysis)
        ):
            return None, "pipeline_option_invalid"
        sec_analysis = options.get("sec_analysis")
        if "sec_analysis" in options and (
            not isinstance(sec_analysis, Mapping) or not _is_json_safe(sec_analysis)
        ):
            return None, "pipeline_option_invalid"
        tga_kinetics = options.get("tga_kinetics")
        if "tga_kinetics" in options and (
            not isinstance(tga_kinetics, Mapping) or not _is_json_safe(tga_kinetics)
        ):
            return None, "pipeline_option_invalid"
        for key in ("dma_tts", "mechanics_analysis", "rheology_advanced", "mechanics_advanced"):
            value = options.get(key)
            if key in options and (not isinstance(value, Mapping) or not _is_json_safe(value)):
                return None, "pipeline_option_invalid"
        normalized: dict[str, Any] = {}
        if "skip_to" in options:
            normalized["skip_to"] = skip_to
        if "mask_edit_candidate" in options:
            normalized["mask_edit_candidate"] = mask_edit_candidate
        if "method_sensitivity" in options:
            normalized["method_sensitivity"] = _normalize_method_sensitivity_request(method_sensitivity)
        if "rheology_analysis" in options:
            normalized["rheology_analysis"] = dict(rheology_analysis)
        if "sec_analysis" in options:
            normalized["sec_analysis"] = dict(sec_analysis)
        if "tga_kinetics" in options:
            normalized["tga_kinetics"] = dict(tga_kinetics)
        for key in ("dma_tts", "mechanics_analysis", "rheology_advanced", "mechanics_advanced"):
            if key in options:
                normalized[key] = dict(options[key])
        return normalized, None
    except Exception:
        return None, "pipeline_option_invalid"


def attach_analysis_options(
    template: CanonicalExperiment,
    *,
    technique: str,
    options: Mapping[str, Any] | None,
) -> tuple[CanonicalExperiment, dict[str, Any]]:
    """Validate explicit analysis options and bind them to one canonical input.

    This is the shared project/Agent admission helper for request semantics
    that must become part of the canonical content hash. Runtime-only pipeline
    controls such as ``skip_to`` are intentionally rejected here.
    """

    normalized_technique = _safe_technique(technique)
    if normalized_technique is None:
        raise ValueError("analysis option technique is invalid")
    normalized, reason = _normalize_pipeline_options(options)
    if reason is not None or normalized is None:
        raise ValueError(reason or "analysis_options_invalid")
    for key in normalized:
        if _ANALYSIS_OPTION_TECHNIQUES.get(key) != normalized_technique:
            raise ValueError(
                f"analysis option does not apply to {normalized_technique}: {key}"
            )

    attached = template
    attachers = {
        "rheology_analysis": _attach_rheology_analysis_spec,
        "rheology_advanced": _attach_rheology_advanced_spec,
        "sec_analysis": _attach_sec_analysis_spec,
        "tga_kinetics": _attach_tga_kinetics_spec,
        "dma_tts": _attach_dma_tts_spec,
        "mechanics_analysis": _attach_mechanics_analysis_spec,
        "mechanics_advanced": _attach_mechanics_advanced_spec,
    }
    for key, value in normalized.items():
        attached = attachers[key](attached, value)
    return attached, normalized


def _is_json_safe(value: object) -> bool:
    """Return whether a pipeline option can be stored in an AnalysisPlan."""
    if isinstance(value, Mapping):
        try:
            return all(
                isinstance(key, str) and _is_json_safe(item)
                for key, item in value.items()
            )
        except Exception:
            return False
    if isinstance(value, (list, tuple)):
        return all(_is_json_safe(item) for item in value)
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError, OverflowError, RecursionError):
        return False
    return value is None or isinstance(value, (str, bool, int, float))


def _has_legacy_result_shape(value: Any) -> bool:
    """Return whether a provider result exposes the required legacy mappings."""
    if value is None:
        return False
    try:
        return all(
            isinstance(getattr(value, attribute), Mapping)
            for attribute in ("parameters", "figures", "metadata")
        )
    except Exception:
        return False


def _json_safe_projection(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe_projection(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe_projection(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


class ComputeRunService:
    """Create one canonical direct run and delegate its calculation to an engine."""

    def __init__(self, engine_factory: Callable[..., Any] = get_engine) -> None:
        self._engine_factory = engine_factory

    def execute_graph(
        self,
        graph: Any,
        context: Any,
        executors: Mapping[str, Callable[[Mapping[str, Any]], Any]] | None = None,
        *,
        cache: Mapping[str, Any] | None = None,
        descriptor_registry: Any | None = None,
        capability_registry: Any | None = None,
        admissions: Mapping[str, Any] | None = None,
    ) -> Any:
        """Execute a shared AI-platform graph through the compute façade.

        This is intentionally a narrow adapter: it validates the public graph
        and context types, then delegates synchronously to
        :meth:`ExecutionGraph.execute`.  It does not turn graph nodes into a
        second ``ComputeRun`` representation or route the established
        ``run_direct`` path through a scheduler.
        """

        from ..ai_platform.execution import ExecutionContext, ExecutionGraph

        if isinstance(graph, Mapping):
            graph = ExecutionGraph.from_dict(graph)
        if isinstance(context, Mapping):
            context = ExecutionContext.from_dict(context)
        if not isinstance(graph, ExecutionGraph):
            raise TypeError("execute_graph expects an ExecutionGraph or mapping")
        if not isinstance(context, ExecutionContext):
            raise TypeError("execute_graph expects an ExecutionContext or mapping")
        return graph.execute(
            context,
            executors,
            cache=cache,
            descriptor_registry=descriptor_registry,
            capability_registry=capability_registry,
            admissions=admissions,
        )

    def run_direct(
        self,
        *,
        technique: object,
        path: object,
        output_dir: object,
        config: Any = None,
        submodule_id: str | None = None,
        engine: Any = None,
        pipeline_options: object = None,
        canonical_template: CanonicalExperiment | None = None,
        source_artifact_id: str | None = None,
        project_context: object = None,
    ) -> ComputeRun:
        normalized_technique = _safe_technique(technique)
        if normalized_technique is None:
            return ComputeRun(
                status="needs_input",
                artifact=RawArtifact.missing(path, technique="unknown"),
                reasons=("technique_invalid",),
            )
        try:
            artifact = RawArtifact.from_path(path, technique=normalized_technique)
        except FileNotFoundError:
            return ComputeRun(
                status="needs_input",
                artifact=RawArtifact.missing(path, technique=normalized_technique),
                reasons=("raw_artifact_missing",),
            )
        except Exception:
            return ComputeRun(
                status="needs_input",
                artifact=RawArtifact.missing(path, technique=normalized_technique),
                reasons=("raw_artifact_unreadable",),
            )
        input_inspection = inspect_format(
            artifact.path,
            technique=normalized_technique,
            source_sha256=artifact.sha256,
        )
        # A project inventory may use a logical, project-scoped artifact ID
        # while the physical ``RawArtifact`` identity includes the absolute
        # path.  A source-bound canonical template can explicitly carry that
        # project identity through this boundary.  The caller must provide a
        # non-empty ID; template validation below still requires the template
        # and artifact identities to agree.
        if source_artifact_id is not None:
            if not isinstance(source_artifact_id, str) or not source_artifact_id.strip():
                return ComputeRun(
                    status="needs_input",
                    artifact=artifact,
                    reasons=("source_artifact_id_invalid",),
                    input_inspection=input_inspection,
                )
            artifact = replace(artifact, artifact_id=source_artifact_id.strip())
        source = Path(artifact.path)
        try:
            source_exists = source.exists()
            is_regular_file = source.is_file()
            is_directory = source.is_dir()
        except Exception:
            return ComputeRun(
                status="needs_input",
                artifact=RawArtifact.missing(source, technique=normalized_technique),
                reasons=("raw_artifact_unreadable",),
            )
        if not source_exists:
            return ComputeRun(
                status="needs_input",
                artifact=RawArtifact.missing(source, technique=normalized_technique),
                reasons=("raw_artifact_missing",),
            )
        if not (is_regular_file or is_directory):
            return ComputeRun(
                status="needs_input",
                artifact=RawArtifact.missing(source, technique=normalized_technique),
                reasons=("raw_artifact_unreadable",),
            )
        if input_inspection.status == "needs_reader":
            return ComputeRun(
                status="needs_input",
                artifact=artifact,
                reasons=input_inspection.reason_codes or ("format_reader_missing",),
                input_inspection=input_inspection,
            )
        resolved_output_path = _resolve_output_dir(output_dir)
        if resolved_output_path is None:
            return ComputeRun(
                status="needs_input",
                artifact=artifact,
                reasons=("output_directory_invalid",),
                input_inspection=input_inspection,
            )
        options, options_reason = _normalize_pipeline_options(pipeline_options)
        if options_reason is not None:
            return ComputeRun(
                status="needs_input",
                artifact=artifact,
                reasons=(options_reason,),
                input_inspection=input_inspection,
            )
        assert options is not None
        if "rheology_analysis" in options and normalized_technique != "rheology":
            return ComputeRun(
                status="needs_input",
                artifact=artifact,
                reasons=("rheology_analysis_technique_mismatch",),
                input_inspection=input_inspection,
            )
        if "rheology_advanced" in options and normalized_technique != "rheology":
            return ComputeRun(
                status="needs_input",
                artifact=artifact,
                reasons=("rheology_advanced_technique_mismatch",),
                input_inspection=input_inspection,
            )
        if "tga_kinetics" in options and normalized_technique != "tga":
            return ComputeRun(
                status="needs_input",
                artifact=artifact,
                reasons=("tga_kinetics_technique_mismatch",),
                input_inspection=input_inspection,
            )
        if "dma_tts" in options and normalized_technique != "dma":
            return ComputeRun(
                status="needs_input",
                artifact=artifact,
                reasons=("dma_tts_technique_mismatch",),
                input_inspection=input_inspection,
            )
        if "mechanics_analysis" in options and normalized_technique != "mechanics":
            return ComputeRun(
                status="needs_input",
                artifact=artifact,
                reasons=("mechanics_analysis_technique_mismatch",),
                input_inspection=input_inspection,
            )
        if "mechanics_advanced" in options and normalized_technique != "mechanics":
            return ComputeRun(
                status="needs_input",
                artifact=artifact,
                reasons=("mechanics_advanced_technique_mismatch",),
                input_inspection=input_inspection,
            )
        if "sec_analysis" in options and normalized_technique != "sec":
            return ComputeRun(
                status="needs_input",
                artifact=artifact,
                reasons=("sec_analysis_technique_mismatch",),
                input_inspection=input_inspection,
            )
        try:
            context = ProjectContext.load(project_context)
        except ValueError:
            return ComputeRun(
                status="needs_input",
                artifact=artifact,
                reasons=("project_context_invalid",),
                input_inspection=input_inspection,
            )
        dataset = CanonicalDataset.direct_envelope(artifact)
        plan = AnalysisPlan.direct(
            dataset,
            output_dir=resolved_output_path,
            pipeline_options=options,
            project_context=context.snapshot,
        )
        # An empty output string is the public provider convention for
        # analysis-only execution.  Keep it empty at the engine boundary even
        # though the immutable plan stores a resolved path for provenance.
        provider_output_dir = "" if isinstance(output_dir, str) and not output_dir.strip() else plan.output_dir
        if canonical_template is not None:
            try:
                canonical_template = CanonicalExperiment.from_dict(canonical_template.to_dict())
            except (AttributeError, KeyError, TypeError, ValueError):
                return ComputeRun(
                    status="needs_input",
                    artifact=artifact,
                    reasons=("canonical_template_invalid",),
                    input_inspection=input_inspection,
                )
            if canonical_template.source_artifact_id != artifact.artifact_id:
                return ComputeRun(
                    status="needs_input",
                    artifact=artifact,
                    reasons=("canonical_template_mismatch",),
                    input_inspection=input_inspection,
                )
            if str(canonical_template.payload.get("technique", normalized_technique)).lower() != normalized_technique:
                return ComputeRun(
                    status="needs_input",
                    artifact=artifact,
                    reasons=("canonical_template_technique_mismatch",),
                    input_inspection=input_inspection,
                )
            if "rheology_analysis" in options:
                try:
                    canonical_template = _attach_rheology_analysis_spec(
                        canonical_template,
                        options["rheology_analysis"],
                    )
                except (TypeError, ValueError):
                    return ComputeRun(
                        status="needs_input",
                        artifact=artifact,
                        reasons=("rheology_analysis_mismatch",),
                        input_inspection=input_inspection,
                    )
            if "rheology_advanced" in options:
                try:
                    canonical_template = _attach_rheology_advanced_spec(
                        canonical_template,
                        options["rheology_advanced"],
                    )
                except (TypeError, ValueError):
                    return ComputeRun(
                        status="needs_input",
                        artifact=artifact,
                        reasons=("rheology_advanced_mismatch",),
                        input_inspection=input_inspection,
                    )
            if "sec_analysis" in options:
                try:
                    canonical_template = _attach_sec_analysis_spec(
                        canonical_template,
                        options["sec_analysis"],
                    )
                except (TypeError, ValueError):
                    return ComputeRun(
                        status="needs_input",
                        artifact=artifact,
                        reasons=("sec_analysis_mismatch",),
                        input_inspection=input_inspection,
                    )
            if "tga_kinetics" in options:
                try:
                    canonical_template = _attach_tga_kinetics_spec(
                        canonical_template, options["tga_kinetics"]
                    )
                except (TypeError, ValueError):
                    return ComputeRun(
                        status="needs_input",
                        artifact=artifact,
                        reasons=("tga_kinetics_mismatch",),
                        input_inspection=input_inspection,
                    )
            if "dma_tts" in options:
                try:
                    canonical_template = _attach_dma_tts_spec(canonical_template, options["dma_tts"])
                except (TypeError, ValueError):
                    return ComputeRun(status="needs_input", artifact=artifact, reasons=("dma_tts_mismatch",), input_inspection=input_inspection)
            if "mechanics_analysis" in options:
                try:
                    canonical_template = _attach_mechanics_analysis_spec(canonical_template, options["mechanics_analysis"])
                except (TypeError, ValueError):
                    return ComputeRun(status="needs_input", artifact=artifact, reasons=("mechanics_analysis_mismatch",), input_inspection=input_inspection)
            if "mechanics_advanced" in options:
                try:
                    canonical_template = _attach_mechanics_advanced_spec(canonical_template, options["mechanics_advanced"])
                except (TypeError, ValueError):
                    return ComputeRun(status="needs_input", artifact=artifact, reasons=("mechanics_advanced_mismatch",), input_inspection=input_inspection)
        capability_items = (
            CapabilityExecutor().execute(canonical_template)
            if canonical_template is not None and canonical_template.measurements
            else ()
        )
        if (
            canonical_template is None
            and normalized_technique in {
                "dsc", "ir", "nmr", "saxs", "waxs", "tga", "dma", "rheology", "sec", "mechanics"
            }
            and (source.is_file() or (source.is_dir() and normalized_technique != "dsc"))
        ):
            conversion = default_converter_registry().convert_path(
                source,
                technique=normalized_technique,
                source_artifact_id=artifact.artifact_id,
            )
            if conversion.status == "needs_input":
                return ComputeRun(
                    status="needs_input",
                    artifact=artifact,
                    reasons=conversion.reason_codes,
                    input_inspection=input_inspection,
                )
            if (
                conversion.status == "blocked"
                and source.is_file()
                and source.suffix.casefold()
                in {".edf", ".cbf", ".tif", ".tiff", ".h5", ".hdf5", ".nxs"}
                and any(str(reason).startswith("detector_image_") for reason in conversion.reason_codes)
            ):
                # Keep provider compatibility when a vendor reader can open
                # an image that the canonical detector decoder cannot.  The
                # fallback is a raw-file envelope only: it carries the byte
                # hash and never asserts pixel geometry, calibration, or a
                # derived physical axis.
                fallback = default_converter_registry().compatibility_envelope(
                    source,
                    technique=normalized_technique,
                    source_artifact_id=artifact.artifact_id,
                )
                if fallback.status == "ready":
                    canonical_template = fallback.template
            if (
                conversion.status == "ready"
                and conversion.template is not None
            ):
                canonical_template = conversion.template
                if "rheology_analysis" in options and normalized_technique == "rheology":
                    try:
                        canonical_template = _attach_rheology_analysis_spec(
                            canonical_template,
                            options["rheology_analysis"],
                        )
                    except (TypeError, ValueError):
                        return ComputeRun(
                            status="needs_input",
                            artifact=artifact,
                            reasons=("rheology_analysis_invalid",),
                            input_inspection=input_inspection,
                        )
                if "rheology_advanced" in options and normalized_technique == "rheology":
                    try:
                        canonical_template = _attach_rheology_advanced_spec(
                            canonical_template,
                            options["rheology_advanced"],
                        )
                    except (TypeError, ValueError):
                        return ComputeRun(
                            status="needs_input",
                            artifact=artifact,
                            reasons=("rheology_advanced_invalid",),
                            input_inspection=input_inspection,
                        )
                if "sec_analysis" in options and normalized_technique == "sec":
                    try:
                        canonical_template = _attach_sec_analysis_spec(
                            canonical_template,
                            options["sec_analysis"],
                        )
                    except (TypeError, ValueError):
                        return ComputeRun(
                            status="needs_input",
                            artifact=artifact,
                            reasons=("sec_analysis_invalid",),
                            input_inspection=input_inspection,
                        )
                if "tga_kinetics" in options and normalized_technique == "tga":
                    try:
                        canonical_template = _attach_tga_kinetics_spec(
                            canonical_template, options["tga_kinetics"]
                        )
                    except (TypeError, ValueError):
                        return ComputeRun(
                            status="needs_input",
                            artifact=artifact,
                            reasons=("tga_kinetics_invalid",),
                            input_inspection=input_inspection,
                        )
                if "dma_tts" in options and normalized_technique == "dma":
                    try:
                        canonical_template = _attach_dma_tts_spec(canonical_template, options["dma_tts"])
                    except (TypeError, ValueError):
                        return ComputeRun(status="needs_input", artifact=artifact, reasons=("dma_tts_invalid",), input_inspection=input_inspection)
                if "mechanics_analysis" in options and normalized_technique == "mechanics":
                    try:
                        canonical_template = _attach_mechanics_analysis_spec(canonical_template, options["mechanics_analysis"])
                    except (TypeError, ValueError):
                        return ComputeRun(status="needs_input", artifact=artifact, reasons=("mechanics_analysis_invalid",), input_inspection=input_inspection)
                if "mechanics_advanced" in options and normalized_technique == "mechanics":
                    try:
                        canonical_template = _attach_mechanics_advanced_spec(canonical_template, options["mechanics_advanced"])
                    except (TypeError, ValueError):
                        return ComputeRun(status="needs_input", artifact=artifact, reasons=("mechanics_advanced_invalid",), input_inspection=input_inspection)
                if canonical_template.measurements:
                    capability_items = CapabilityExecutor().execute(canonical_template)
            if (
                "rheology_analysis" in options
                and normalized_technique == "rheology"
                and canonical_template is None
            ):
                return ComputeRun(
                    status="needs_input",
                    artifact=artifact,
                    reasons=("rheology_analysis_requires_canonical_template",),
                    input_inspection=input_inspection,
                )
            if (
                "rheology_advanced" in options
                and normalized_technique == "rheology"
                and canonical_template is None
            ):
                return ComputeRun(
                    status="needs_input",
                    artifact=artifact,
                    reasons=("rheology_advanced_requires_canonical_template",),
                    input_inspection=input_inspection,
                )
            if (
                "sec_analysis" in options
                and normalized_technique == "sec"
                and canonical_template is None
            ):
                return ComputeRun(
                    status="needs_input",
                    artifact=artifact,
                    reasons=("sec_analysis_requires_canonical_template",),
                    input_inspection=input_inspection,
                )
            for option_name, option_technique in (
                ("tga_kinetics", "tga"),
                ("dma_tts", "dma"),
                ("mechanics_analysis", "mechanics"),
                ("mechanics_advanced", "mechanics"),
            ):
                if option_name in options and normalized_technique == option_technique and canonical_template is None:
                    return ComputeRun(
                        status="needs_input",
                        artifact=artifact,
                        reasons=(f"{option_name}_requires_canonical_template",),
                        input_inspection=input_inspection,
                    )
        try:
            selected_engine = engine
            if selected_engine is None:
                selected_engine = self._engine_factory(
                    normalized_technique,
                    config=config,
                    submodule_id=submodule_id,
                )
            if selected_engine is None:
                return ComputeRun(
                    status="needs_input",
                    artifact=artifact,
                    reasons=("technique_unknown",),
                    input_inspection=input_inspection,
                )
            if normalized_technique == "dsc" and context.dsc_reference_enthalpy is not None:
                dsc_config = getattr(selected_engine, "_dsc_config", None)
                if dsc_config is not None:
                    dsc_config.user_DHm0 = context.dsc_reference_enthalpy
                    dsc_config.crystallinity_std = context.dsc_reference_enthalpy
            material = context.snapshot.get("material", {})
            material_name = material.get("name") if isinstance(material, Mapping) else None
            if normalized_technique == "ir" and material_name:
                ir_config = getattr(selected_engine, "_ir_config", None)
                if ir_config is not None and not getattr(ir_config, "polymer_name", ""):
                    ir_config.polymer_name = str(material_name)
            if normalized_technique == "nmr" and material_name:
                nmr_config = getattr(selected_engine, "_cfg", None)
                if nmr_config is not None and not getattr(nmr_config, "polymer_name", ""):
                    nmr_config.polymer_name = str(material_name)
            if normalized_technique == "waxs" and context.waxs_polymer_type:
                waxs_config = getattr(selected_engine, "_waxs_config", None)
                if waxs_config is not None and not getattr(waxs_config, "polymer_type", ""):
                    waxs_config.polymer_type = context.waxs_polymer_type
            canonical_runner = (
                getattr(selected_engine, "run_canonical_template", None)
                if canonical_template is not None
                else None
            )
            if callable(canonical_runner):
                provider_options = {
                    key: value for key, value in options.items()
                    if key not in {
                        "method_sensitivity",
                        "rheology_analysis",
                        "rheology_advanced",
                        "sec_analysis",
                        "tga_kinetics",
                        "dma_tts",
                        "mechanics_analysis",
                        "mechanics_advanced",
                    }
                }
                legacy_result = canonical_runner(
                    canonical_template,
                    provider_output_dir,
                    **provider_options,
                )
            elif (
                canonical_template is not None
                and normalized_technique == "dsc"
                and (
                    hasattr(selected_engine, "run_thermal_program_template")
                    or hasattr(selected_engine, "run_isothermal_template")
                )
            ):
                template_runner = getattr(selected_engine, "run_thermal_program_template", None)
                if not callable(template_runner):
                    template_runner = getattr(selected_engine, "run_isothermal_template")
                template_output = template_runner(canonical_template)
                legacy_result = template_output
                if not _has_legacy_result_shape(legacy_result):
                    legacy_result = getattr(selected_engine, "result", None)
                if legacy_result is not None:
                    get_parameters = getattr(selected_engine, "get_parameters", None)
                    if callable(get_parameters):
                        parameters = get_parameters()
                        if isinstance(parameters, Mapping):
                            legacy_result.parameters = _json_safe_projection(parameters)
            else:
                provider_options = {
                    key: value for key, value in options.items()
                    if key not in {
                        "method_sensitivity",
                        "rheology_analysis",
                        "rheology_advanced",
                        "sec_analysis",
                        "tga_kinetics",
                        "dma_tts",
                        "mechanics_analysis",
                        "mechanics_advanced",
                    }
                }
                legacy_result = selected_engine.run_pipeline(
                    artifact.path,
                    provider_output_dir,
                    **provider_options,
                )
            if not _has_legacy_result_shape(legacy_result):
                return ComputeRun(
                    status="failed",
                    artifact=artifact,
                    dataset=dataset,
                    plan=plan,
                    canonical_template=canonical_template,
                    capability_items=capability_items,
                    reasons=("provider_execution_failed",),
                    input_inspection=input_inspection,
                )
            result = ComputeResult.from_legacy_result(legacy_result)
            method_sensitivity = options.get("method_sensitivity")
            if method_sensitivity:
                result = self._attach_method_sensitivity(
                    result=result,
                    technique=normalized_technique,
                    source_path=artifact.path,
                    output_dir=provider_output_dir,
                    config=config,
                    submodule_id=submodule_id,
                    selected_engine=selected_engine,
                    canonical_template=canonical_template,
                    provider_options={
                        key: value for key, value in options.items()
                        if key != "method_sensitivity"
                    },
                    request=method_sensitivity,
                )
            provider_input = ProviderResultInput.create(
                source_artifact_id=artifact.artifact_id,
                technique=normalized_technique,
                metrics=result.metrics,
                metric_manifest=result.metric_manifest(source=artifact.path),
                descriptor_id=result.descriptor_id,
                computation_state=result.computation_state,
                provenance=result.provenance,
                uncertainty=result.uncertainty,
            )
            provider_capability_items = CapabilityExecutor().execute_provider_result(
                provider_input=provider_input,
            )
            return ComputeRun.completed(
                artifact=artifact,
                dataset=dataset,
                plan=plan,
                result=result,
                canonical_template=canonical_template,
                capability_items=capability_items,
                provider_capability_items=provider_capability_items,
                legacy_result=legacy_result,
                input_inspection=input_inspection,
            )
        except Exception:
            return ComputeRun(
                status="failed",
                artifact=artifact,
                dataset=dataset,
                plan=plan,
                canonical_template=canonical_template,
                capability_items=capability_items,
                reasons=("provider_execution_failed",),
                input_inspection=input_inspection,
            )

    def _attach_method_sensitivity(
        self,
        *,
        result: ComputeResult,
        technique: str,
        source_path: str,
        output_dir: str,
        config: Any,
        submodule_id: str | None,
        selected_engine: Any,
        canonical_template: CanonicalExperiment | None,
        provider_options: Mapping[str, Any],
        request: Mapping[str, Any],
    ) -> ComputeResult:
        """Run explicitly requested config candidates and retain their values."""
        dimensions = request.get("dimensions", {})
        if not isinstance(dimensions, Mapping):
            return result
        base_config = config
        if base_config is None:
            base_config = _engine_config(selected_engine, technique)
        variants: dict[str, dict[str, Any]] = {}
        sensitivity_warnings: list[str] = []
        primary_input = (
            "canonical_template"
            if canonical_template is not None
            and callable(getattr(selected_engine, "run_canonical_template", None))
            else "raw_pipeline_compatibility"
        )
        primary_metrics = _scalar_metric_paths(result.metrics)
        for dimension, methods in dimensions.items():
            attribute = _sensitivity_attribute(technique, str(dimension))
            if attribute is None:
                sensitivity_warnings.append(
                    f"method_sensitivity_unavailable:{technique}:{dimension}"
                )
                continue
            primary_method_value = _config_value(base_config, attribute, selected_engine)
            primary_method = _method_label(primary_method_value)
            if primary_method is None:
                primary_method = "default"
            candidate_values: dict[str, dict[str, Any] | None] = {}
            candidate_errors: dict[str, str] = {}
            candidate_output_dirs: dict[str, str] = {}
            candidate_inputs: dict[str, str] = {}
            for method in methods:
                method_name = _method_label(method)
                if method_name == primary_method:
                    continue
                candidate_config = _clone_config(base_config)
                try:
                    candidate_config = _set_config_value(candidate_config, attribute, method)
                except (TypeError, ValueError) as exc:
                    candidate_values[method_name] = None
                    candidate_errors[method_name] = type(exc).__name__
                    candidate_inputs[method_name] = "candidate_configuration_invalid"
                    continue
                candidate_output_dir = _candidate_output_dir(output_dir, str(dimension), method_name)
                candidate_output_dirs[method_name] = candidate_output_dir
                try:
                    candidate_engine = self._engine_factory(
                        technique,
                        config=candidate_config,
                        submodule_id=submodule_id,
                    )
                    candidate_runner = (
                        getattr(candidate_engine, "run_canonical_template", None)
                        if canonical_template is not None
                        else None
                    )
                    if callable(candidate_runner):
                        candidate_inputs[method_name] = "canonical_template"
                        candidate_result = candidate_runner(
                            canonical_template,
                            candidate_output_dir,
                            **provider_options,
                        )
                    else:
                        candidate_inputs[method_name] = "raw_pipeline_compatibility"
                        candidate_result = candidate_engine.run_pipeline(
                            source_path,
                            candidate_output_dir,
                            **provider_options,
                        )
                    if not _has_legacy_result_shape(candidate_result):
                        raise RuntimeError("candidate_provider_result_invalid")
                    candidate_projection = ComputeResult.from_legacy_result(candidate_result)
                    candidate_values[method_name] = _scalar_metric_paths(candidate_projection.metrics)
                except Exception as exc:
                    candidate_values[method_name] = None
                    candidate_errors[method_name] = type(exc).__name__
            all_paths = sorted(
                set(primary_metrics)
                | {
                    path
                    for values in candidate_values.values()
                    if isinstance(values, Mapping)
                    for path in values
                }
            )
            for path in all_paths:
                candidates = {
                    method: (values.get(path) if isinstance(values, Mapping) else None)
                    for method, values in candidate_values.items()
                }
                if not candidates:
                    continue
                variant_key = path
                if variant_key in variants:
                    variant_key = f"{path} [{dimension}]"
                warnings = [
                    f"method_failed:{method}:{candidate_errors[method]}"
                    for method in sorted(candidate_errors)
                ]
                variants[variant_key] = {
                    "primary_method": str(primary_method),
                    "primary": primary_metrics.get(path),
                    "candidates": candidates,
                    "parameters": {
                        "dimension": str(dimension),
                        "config_attribute": attribute,
                        "primary_input": primary_input,
                        "candidate_inputs": dict(candidate_inputs),
                        "candidate_output_dirs": dict(candidate_output_dirs),
                    },
                    "warnings": warnings,
                }
        sensitivities = sensitivities_from_metrics(
            {"method_variants": variants},
            technique=technique,
            source=source_path,
        )
        if not sensitivities and not sensitivity_warnings:
            return result
        return ComputeResult(
            metrics=result.metrics,
            figures=result.figures,
            metadata=result.metadata,
            warnings=(*result.warnings, *sensitivity_warnings),
            method_sensitivities=(*result.method_sensitivities, *sensitivities),
        )


def _valid_method_sensitivity_request(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    dimensions = value.get("dimensions", value)
    if not isinstance(dimensions, Mapping) or not dimensions:
        return False
    for dimension, methods in dimensions.items():
        if not str(dimension).strip() or not isinstance(methods, (list, tuple)) or not methods:
            return False
        if any(not _is_json_safe(method) for method in methods):
            return False
    return True


def _attach_rheology_analysis_spec(
    template: CanonicalExperiment,
    value: Mapping[str, Any],
) -> CanonicalExperiment:
    """Return a rehashed canonical template carrying an explicit rheology spec."""
    if not isinstance(value, Mapping):
        raise TypeError("rheology_analysis must be a mapping")
    if str(template.payload.get("technique", "")).casefold() != "rheology":
        raise ValueError("rheology_analysis requires a rheology canonical template")
    from ..rheology_processing import RheologyAnalysisSpec

    normalized = RheologyAnalysisSpec.from_mapping(value).to_dict()
    # The DTO normalizes scientific options; the canonical template remains
    # the authority for which source measurements may be referenced.
    advanced = normalized.get("advanced")
    if isinstance(advanced, Mapping):
        _validate_measurement_bindings(
            template,
            advanced,
            scalar_keys=(
                "complex_viscosity_measurement_id",
                "steady_viscosity_measurement_id",
                "thixotropy_measurement_id",
                "creep_measurement_id",
                "relaxation_measurement_id",
                "time_measurement_id",
            ),
            sequence_keys=("tts_curve_measurement_ids",),
            sequence_length_keys={"tts_curve_measurement_ids": "temperatures"},
            temperature_key="temperatures",
        )
    existing = template.payload.get("rheology_analysis")
    if existing is not None:
        if not isinstance(existing, Mapping):
            raise ValueError("canonical rheology analysis spec is invalid")
        if RheologyAnalysisSpec.from_mapping(existing).to_dict() != normalized:
            raise ValueError("canonical rheology analysis spec does not match request")
        return template
    payload = dict(template.payload)
    payload["rheology_analysis"] = normalized
    return CanonicalExperiment.create(
        template_id=template.template_id,
        source_artifact_id=template.source_artifact_id,
        payload=payload,
        conversion_record=template.conversion_record,
        measurements=template.measurements,
        mapping_proposal=template.mapping_proposal,
        contract_version=template.contract_version,
    )


def _attach_rheology_advanced_spec(
    template: CanonicalExperiment,
    value: Mapping[str, Any],
) -> CanonicalExperiment:
    if not isinstance(value, Mapping):
        raise TypeError("rheology_advanced must be a mapping")
    if str(template.payload.get("technique", "")).casefold() != "rheology":
        raise ValueError("rheology_advanced requires a rheology canonical template")
    from ..rheology_processing import RheologyAdvancedSpec

    normalized = RheologyAdvancedSpec.from_mapping(value).to_dict()
    _validate_measurement_bindings(
        template,
        normalized,
        scalar_keys=(
            "complex_viscosity_measurement_id",
            "steady_viscosity_measurement_id",
            "thixotropy_measurement_id",
            "creep_measurement_id",
            "relaxation_measurement_id",
            "time_measurement_id",
        ),
        sequence_keys=("tts_curve_measurement_ids",),
        sequence_length_keys={"tts_curve_measurement_ids": "temperatures"},
        temperature_key="temperatures",
    )
    existing = template.payload.get("rheology_advanced")
    if existing is not None and RheologyAdvancedSpec.from_mapping(existing).to_dict() != normalized:
        raise ValueError("canonical rheology advanced spec does not match request")
    if existing is not None:
        return template
    payload = dict(template.payload)
    payload["rheology_advanced"] = normalized
    return CanonicalExperiment.create(
        template_id=template.template_id,
        source_artifact_id=template.source_artifact_id,
        payload=payload,
        conversion_record=template.conversion_record,
        measurements=template.measurements,
        mapping_proposal=template.mapping_proposal,
        contract_version=template.contract_version,
    )


def _attach_sec_analysis_spec(
    template: CanonicalExperiment,
    value: Mapping[str, Any],
) -> CanonicalExperiment:
    """Return a rehashed SEC template carrying explicit calibration semantics."""
    if not isinstance(value, Mapping):
        raise TypeError("sec_analysis must be a mapping")
    if str(template.payload.get("technique", "")).casefold() != "sec":
        raise ValueError("sec_analysis requires a SEC canonical template")
    from ..sec_processing import SECCalibrationSpec

    normalized = SECCalibrationSpec.from_mapping(value).to_dict()
    existing = template.payload.get("sec_analysis")
    if existing is not None:
        if not isinstance(existing, Mapping):
            raise ValueError("canonical SEC analysis spec is invalid")
        if SECCalibrationSpec.from_mapping(existing).to_dict() != normalized:
            raise ValueError("canonical SEC analysis spec does not match request")
        return template
    payload = dict(template.payload)
    payload["sec_analysis"] = normalized
    return CanonicalExperiment.create(
        template_id=template.template_id,
        source_artifact_id=template.source_artifact_id,
        payload=payload,
        conversion_record=template.conversion_record,
        measurements=template.measurements,
        mapping_proposal=template.mapping_proposal,
        contract_version=template.contract_version,
    )


def _attach_tga_kinetics_spec(template: CanonicalExperiment, value: Mapping[str, Any]) -> CanonicalExperiment:
    if not isinstance(value, Mapping):
        raise TypeError("tga_kinetics must be a mapping")
    if str(template.payload.get("technique", "")).casefold() != "tga":
        raise ValueError("tga_kinetics requires a TGA canonical template")
    from ..tga_processing import TGAKineticsSpec

    normalized = TGAKineticsSpec.from_mapping(value).to_dict()
    _validate_measurement_bindings(
        template,
        normalized,
        sequence_keys=("curve_measurement_ids",),
        sequence_length_keys={"curve_measurement_ids": "heating_rates"},
        value_key="heating_rates",
    )
    existing = template.payload.get("tga_kinetics")
    if existing is not None and TGAKineticsSpec.from_mapping(existing).to_dict() != normalized:
        raise ValueError("canonical TGA kinetics spec does not match request")
    if existing is not None:
        return template
    payload = dict(template.payload)
    payload["tga_kinetics"] = normalized
    return CanonicalExperiment.create(
        template_id=template.template_id,
        source_artifact_id=template.source_artifact_id,
        payload=payload,
        conversion_record=template.conversion_record,
        measurements=template.measurements,
        mapping_proposal=template.mapping_proposal,
        contract_version=template.contract_version,
    )


def _attach_dma_tts_spec(template: CanonicalExperiment, value: Mapping[str, Any]) -> CanonicalExperiment:
    if not isinstance(value, Mapping):
        raise TypeError("dma_tts must be a mapping")
    if str(template.payload.get("technique", "")).casefold() != "dma":
        raise ValueError("dma_tts requires a DMA canonical template")
    from ..dma_processing import DMATTSSpec

    normalized = DMATTSSpec.from_mapping(value).to_dict()
    _validate_measurement_bindings(
        template,
        normalized,
        sequence_keys=("curve_measurement_ids",),
        sequence_length_keys={"curve_measurement_ids": "temperatures"},
        temperature_key="temperatures",
    )
    existing = template.payload.get("dma_tts")
    if existing is not None and DMATTSSpec.from_mapping(existing).to_dict() != normalized:
        raise ValueError("canonical DMA TTS spec does not match request")
    if existing is not None:
        return template
    payload = dict(template.payload)
    payload["dma_tts"] = normalized
    return CanonicalExperiment.create(
        template_id=template.template_id,
        source_artifact_id=template.source_artifact_id,
        payload=payload,
        conversion_record=template.conversion_record,
        measurements=template.measurements,
        mapping_proposal=template.mapping_proposal,
        contract_version=template.contract_version,
    )


def _attach_analysis_mapping(template: CanonicalExperiment, value: Mapping[str, Any], technique: str, key: str) -> CanonicalExperiment:
    if not isinstance(value, Mapping) or str(template.payload.get("technique", "")).casefold() != technique:
        raise ValueError(f"{key} requires a {technique} canonical template")
    _validate_measurement_bindings(
        template,
        value,
        scalar_keys=(
            "stress_measurement_id",
            "strain_measurement_id",
            "cycle_measurement_id",
            "fatigue_measurement_id",
            "creep_measurement_id",
            "fracture_measurement_id",
        ),
    )
    existing = template.payload.get(key)
    normalized = dict(value)
    if existing is not None and existing != normalized:
        raise ValueError(f"canonical {key} does not match request")
    if existing is not None:
        return template
    payload = dict(template.payload)
    payload[key] = normalized
    return CanonicalExperiment.create(template_id=template.template_id, source_artifact_id=template.source_artifact_id, payload=payload, conversion_record=template.conversion_record, measurements=template.measurements, mapping_proposal=template.mapping_proposal, contract_version=template.contract_version)


def _attach_mechanics_analysis_spec(template: CanonicalExperiment, value: Mapping[str, Any]) -> CanonicalExperiment:
    from ..mechanics_processing import MechanicsAnalysisSpec
    normalized = MechanicsAnalysisSpec.from_mapping(value).to_dict()
    return _attach_analysis_mapping(template, normalized, "mechanics", "mechanics_analysis")


def _attach_mechanics_advanced_spec(template: CanonicalExperiment, value: Mapping[str, Any]) -> CanonicalExperiment:
    from ..mechanics_processing import MechanicsAdvancedSpec

    normalized = MechanicsAdvancedSpec.from_mapping(value).to_dict()
    return _attach_analysis_mapping(template, normalized, "mechanics", "mechanics_advanced")


def _validate_measurement_bindings(
    template: CanonicalExperiment,
    spec: Mapping[str, Any],
    *,
    scalar_keys: Sequence[str] = (),
    sequence_keys: Sequence[str] = (),
    sequence_length_keys: Mapping[str, str] | None = None,
    temperature_key: str | None = None,
    value_key: str | None = None,
) -> None:
    """Validate explicit analysis-spec references against canonical data.

    Analysis DTOs describe intent, while a ``CanonicalExperiment`` owns the
    source identity.  Keeping this check at the attach boundary prevents a
    caller from referring to a raw/vendor identifier that is not actually
    present in the canonical template.  Empty optional ID vectors preserve the
    legacy single-curve/provider fallback; once IDs are supplied, every ID is
    strict and ordered.
    """
    if not isinstance(spec, Mapping):
        raise TypeError("analysis spec must be a mapping")
    available = {
        str(measurement.measurement_id).strip()
        for measurement in template.measurements
        if str(measurement.measurement_id).strip()
    }
    if not available:
        raise ValueError("canonical template has no measurements")

    for key in scalar_keys:
        identifier = spec.get(key)
        if identifier is None or (isinstance(identifier, str) and not identifier.strip()):
            continue
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError(f"{key} must be a canonical measurement id")
        if identifier.strip() not in available:
            raise ValueError(f"{key} is not present in canonical measurements")

    length_keys = sequence_length_keys or {}
    for key in sequence_keys:
        raw_ids = spec.get(key, ())
        # DTOs normalize omitted vectors to either ``()`` or ``[]``.  An
        # empty vector means that the provider may use its established
        # single-curve/legacy fallback; only a non-empty vector is an
        # explicit canonical binding that must be validated.
        if raw_ids is None or (
            isinstance(raw_ids, Sequence)
            and not isinstance(raw_ids, (str, bytes, bytearray))
            and len(raw_ids) == 0
        ):
            continue
        if isinstance(raw_ids, (str, bytes, bytearray)) or not isinstance(raw_ids, Sequence):
            raise ValueError(f"{key} must be a sequence of canonical measurement ids")
        identifiers = tuple(str(item).strip() for item in raw_ids)
        if any(not identifier for identifier in identifiers):
            raise ValueError(f"{key} must not contain empty measurement ids")
        missing = tuple(identifier for identifier in identifiers if identifier not in available)
        if missing:
            raise ValueError(f"{key} references measurement(s) not present in canonical data")
        expected_key = length_keys.get(key)
        if expected_key is not None:
            expected = spec.get(expected_key, ())
            if isinstance(expected, Sequence) and not isinstance(expected, (str, bytes, bytearray)) and len(identifiers) != len(expected):
                raise ValueError(f"{key} must align with {expected_key}")
        if temperature_key is not None and key == "curve_measurement_ids":
            temperatures = spec.get(temperature_key, ())
            if isinstance(temperatures, Sequence) and not isinstance(temperatures, (str, bytes, bytearray)) and len(temperatures) == len(identifiers):
                by_id = {str(item.measurement_id).strip(): item for item in template.measurements}
                for identifier, declared in zip(identifiers, temperatures, strict=True):
                    metadata = by_id[identifier].acquisition_metadata
                    observed = next(
                        (metadata[name] for name in ("temperature", "temperature_C", "temperature_c") if name in metadata),
                        None,
                    )
                    if observed is None:
                        continue
                    try:
                        observed_value = float(observed)
                        declared_value = float(declared)
                    except (TypeError, ValueError):
                        raise ValueError("curve measurement temperature is invalid") from None
                    if not math.isclose(observed_value, declared_value, rel_tol=0.0, abs_tol=1e-9):
                        raise ValueError("curve measurement temperature does not match analysis spec")

    if value_key is not None:
        values = spec.get(value_key, ())
        if isinstance(values, Sequence) and not isinstance(values, (str, bytes, bytearray)):
            # TGA rate metadata is optional in existing converters.  If a
            # converter has recorded it, verify the explicit ordering.
            ids = tuple(str(item).strip() for item in spec.get("curve_measurement_ids", ()))
            if ids and len(ids) == len(values):
                by_id = {str(item.measurement_id).strip(): item for item in template.measurements}
                for identifier, declared in zip(ids, values, strict=True):
                    metadata = by_id[identifier].acquisition_metadata
                    observed = next(
                        (metadata[name] for name in ("heating_rate", "heating_rate_K_min", "heating_rate_k_min") if name in metadata),
                        None,
                    )
                    if observed is None:
                        continue
                    try:
                        observed_value = float(observed)
                        declared_value = float(declared)
                    except (TypeError, ValueError):
                        raise ValueError("curve measurement heating rate is invalid") from None
                    if not math.isclose(observed_value, declared_value, rel_tol=0.0, abs_tol=1e-9):
                        raise ValueError("curve measurement heating rate does not match analysis spec")


def _normalize_method_sensitivity_request(value: Mapping[str, Any]) -> dict[str, Any]:
    dimensions = value.get("dimensions", value)
    return {"dimensions": {str(key): list(methods) for key, methods in dimensions.items()}}


def _sensitivity_attribute(technique: str, dimension: str) -> str | tuple[str, ...] | None:
    mapping = {
        "ir": {"background": "baseline_method", "baseline": "baseline_method", "normalization": "normalization_method", "peak_fit": "lineshape", "integration_window": "peak_fit_window_cm1"},
        "saxs": {
            "background": "bg_scale_method",
            "fit_model": "lorentz_fit_method",
            "integration_window": ("q_bragg_min", "q_bragg_max"),
        },
        "waxs": {"background": "background_method", "peak_decomposition": "peak_function", "crystallinity": "crystallinity_method"},
        "nmr": {"baseline": "baseline_method", "peak_fit": "deconvolution_method", "region_integration": "region_windows_ppm"},
        "tga": {
            "dtg_window": "dtg_window_points",
            "dtg_polynomial_order": "dtg_polynomial_order",
            "event_prominence": "event_prominence_noise_factor",
            "event_minimum_mass_loss": "event_minimum_mass_loss_percent",
        },
    }
    return mapping.get(str(technique).lower(), {}).get(str(dimension).lower())


def _engine_config(engine: Any, technique: str) -> Any:
    normalized = "ir" if str(technique).lower() == "ftir" else str(technique).lower()
    name = {
        "ir": "_ir_config",
        "saxs": "cfg",
        "waxs": "_waxs_config",
        "nmr": "_cfg",
        "tga": "processing_config",
    }.get(normalized)
    if name is None:
        return None
    for name in (name,):
        value = getattr(engine, name, None)
        if value is not None:
            return value
    return None


def _clone_config(config: Any) -> Any:
    return copy.deepcopy(config) if config is not None else {}


def _config_value(config: Any, attribute: str | tuple[str, ...], engine: Any) -> Any:
    if isinstance(attribute, tuple):
        return {
            name: _config_value(config, name, engine)
            for name in attribute
        }
    if isinstance(config, Mapping):
        return config.get(attribute)
    value = getattr(config, attribute, None) if config is not None else None
    return value


def _set_config_value(config: Any, attribute: str | tuple[str, ...], value: Any) -> Any:
    if isinstance(attribute, tuple):
        if not isinstance(value, Mapping):
            raise TypeError("coupled method sensitivity override must be a mapping")
        aliases = {
            "q_min": attribute[0],
            "q_max": attribute[1],
        }
        updated = config
        for key, item in value.items():
            target = aliases.get(str(key), str(key))
            if target not in attribute:
                raise ValueError(f"unsupported coupled override field: {key}")
            updated = _set_config_value(updated, target, item)
        if any(_config_value(updated, name, None) is None for name in attribute):
            raise ValueError("coupled method sensitivity override must set all fields")
        return updated
    if isinstance(config, Mapping):
        config[attribute] = value
        return config
    if is_dataclass(config):
        return replace(config, **{attribute: value})
    setattr(config, attribute, value)
    return config


def _scalar_metric_paths(value: Mapping[str, Any], prefix: str = "") -> dict[str, float]:
    result: dict[str, float] = {}
    for key, child in value.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(child, Mapping):
            result.update(_scalar_metric_paths(child, path))
        elif isinstance(child, (int, float)) and not isinstance(child, bool) and math.isfinite(float(child)):
            result[path] = float(child)
    return result


def _candidate_output_dir(output_dir: str, dimension: str, method: str) -> str:
    """Give each explicit candidate an isolated, reproducible output path."""
    if not output_dir:
        return ""
    safe_dimension = re.sub(r"[^A-Za-z0-9_.-]+", "_", dimension).strip("._") or "dimension"
    safe_method = re.sub(r"[^A-Za-z0-9_.-]+", "_", method).strip("._") or "method"
    return str(Path(output_dir) / "method-sensitivity" / safe_dimension / safe_method)


def _method_label(value: Any) -> str:
    """Return a stable display key for scalar or coupled method descriptors."""
    if isinstance(value, Mapping):
        return json.dumps(_json_safe_projection(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return str(value)
