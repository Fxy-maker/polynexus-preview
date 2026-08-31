"""Direct-run adapter from the public compute contracts to legacy engines."""

from __future__ import annotations

from collections.abc import Mapping
import copy
import json
import math
from pathlib import Path
import re
from typing import Any, Callable

from ..engine import get_engine
from ..project_context import ProjectContext
from ..canonical_experiments import CapabilityExecutor, CanonicalExperiment, default_converter_registry
from .models import AnalysisPlan, CanonicalDataset, ComputeResult, ComputeRun, RawArtifact
from .method_sensitivity import sensitivities_from_metrics


_SUPPORTED_PIPELINE_OPTIONS = frozenset({"skip_to", "mask_edit_candidate", "method_sensitivity"})
_SUPPORTED_SKIP_TO_VALUES = frozenset({"preprocess", "analyze", "plot"})


def _safe_technique(value: object) -> str | None:
    """Return one normalized technique string without coercing arbitrary objects."""
    if not isinstance(value, str):
        return None
    normalized = str.lower(str.strip(value))
    if normalized == "ftir":
        normalized = "ir"
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
        normalized: dict[str, Any] = {}
        if "skip_to" in options:
            normalized["skip_to"] = skip_to
        if "mask_edit_candidate" in options:
            normalized["mask_edit_candidate"] = mask_edit_candidate
        if "method_sensitivity" in options:
            normalized["method_sensitivity"] = _normalize_method_sensitivity_request(method_sensitivity)
        return normalized, None
    except Exception:
        return None, "pipeline_option_invalid"


def _is_json_safe(value: object) -> bool:
    """Return whether a pipeline option can be stored in an AnalysisPlan."""
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError, OverflowError, RecursionError):
        return False
    if isinstance(value, Mapping):
        try:
            return all(
                isinstance(key, str) and _is_json_safe(item)
                for key, item in value.items()
            )
        except Exception:
            return False
    if isinstance(value, list):
        return all(_is_json_safe(item) for item in value)
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
        resolved_output_path = _resolve_output_dir(output_dir)
        if resolved_output_path is None:
            return ComputeRun(
                status="needs_input",
                artifact=artifact,
                reasons=("output_directory_invalid",),
            )
        options, options_reason = _normalize_pipeline_options(pipeline_options)
        if options_reason is not None:
            return ComputeRun(
                status="needs_input",
                artifact=artifact,
                reasons=(options_reason,),
            )
        assert options is not None
        try:
            context = ProjectContext.load(project_context)
        except ValueError:
            return ComputeRun(status="needs_input", artifact=artifact, reasons=("project_context_invalid",))
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
                )
            if canonical_template.source_artifact_id != artifact.artifact_id:
                return ComputeRun(
                    status="needs_input",
                    artifact=artifact,
                    reasons=("canonical_template_mismatch",),
                )
            if str(canonical_template.payload.get("technique", normalized_technique)).lower() != normalized_technique:
                return ComputeRun(
                    status="needs_input",
                    artifact=artifact,
                    reasons=("canonical_template_technique_mismatch",),
                )
        capability_items = (
            CapabilityExecutor().execute(canonical_template)
            if canonical_template is not None and canonical_template.measurements
            else ()
        )
        if (
            canonical_template is None
            and normalized_technique in {"dsc", "ir", "nmr", "saxs", "waxs"}
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
                if canonical_template.measurements:
                    capability_items = CapabilityExecutor().execute(canonical_template)
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
            if (
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
                    if key != "method_sensitivity"
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
                    provider_options={
                        key: value for key, value in options.items()
                        if key != "method_sensitivity"
                    },
                    request=method_sensitivity,
                )
            provider_capability_items = CapabilityExecutor().execute_provider_result(
                source_artifact_id=artifact.artifact_id,
                technique=normalized_technique,
                metrics=result.metrics,
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
            for method in methods:
                method_name = _method_label(method)
                if method_name == primary_method:
                    continue
                candidate_config = _clone_config(base_config)
                try:
                    _set_config_value(candidate_config, attribute, method)
                except (TypeError, ValueError) as exc:
                    candidate_values[method_name] = None
                    candidate_errors[method_name] = type(exc).__name__
                    continue
                candidate_output_dir = _candidate_output_dir(output_dir, str(dimension), method_name)
                candidate_output_dirs[method_name] = candidate_output_dir
                try:
                    candidate_engine = self._engine_factory(
                        technique,
                        config=candidate_config,
                        submodule_id=submodule_id,
                    )
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
    }
    return mapping.get(str(technique).lower(), {}).get(str(dimension).lower())


def _engine_config(engine: Any, technique: str) -> Any:
    normalized = "ir" if str(technique).lower() == "ftir" else str(technique).lower()
    name = {"ir": "_ir_config", "saxs": "cfg", "waxs": "_waxs_config", "nmr": "_cfg"}.get(normalized)
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


def _set_config_value(config: Any, attribute: str | tuple[str, ...], value: Any) -> None:
    if isinstance(attribute, tuple):
        if not isinstance(value, Mapping):
            raise TypeError("coupled method sensitivity override must be a mapping")
        aliases = {
            "q_min": attribute[0],
            "q_max": attribute[1],
        }
        for key, item in value.items():
            target = aliases.get(str(key), str(key))
            if target not in attribute:
                raise ValueError(f"unsupported coupled override field: {key}")
            _set_config_value(config, target, item)
        if any(_config_value(config, name, None) is None for name in attribute):
            raise ValueError("coupled method sensitivity override must set all fields")
        return
    if isinstance(config, Mapping):
        config[attribute] = value
    else:
        setattr(config, attribute, value)


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
