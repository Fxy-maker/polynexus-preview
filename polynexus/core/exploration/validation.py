"""Strict execution validation for exploration descriptor contracts."""

from __future__ import annotations

import math
from typing import Any, Mapping

from .canonical import CanonicalAdmission
from .contracts import ExplorationExecutorDescriptor
from polynexus.core.ai_platform.contracts import ProviderResultInput


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _type_matches(value: Any, expected: str) -> bool:
    expected = str(expected).lower()
    return {
        "number": _number(value),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "string": isinstance(value, str),
        "array": isinstance(value, (list, tuple)),
        "object": isinstance(value, Mapping),
        "any": True,
    }.get(expected, False)


def validate_input_contract(
    descriptor: ExplorationExecutorDescriptor,
    request: Any,
    admission: CanonicalAdmission,
) -> tuple[str, ...]:
    """Return deterministic input-contract violations (never raise)."""

    contract = descriptor.input_contract
    if not isinstance(contract, Mapping):
        return ("exploration_input_contract_invalid",)
    canonical = contract.get("canonical")
    parameters = contract.get("parameters")
    if not isinstance(canonical, Mapping) or not isinstance(parameters, Mapping):
        return ("exploration_input_contract_schema_missing",)
    errors: list[str] = []
    kinds = canonical.get("kinds", ("dataset", "experiment"))
    if not isinstance(kinds, (list, tuple, set, frozenset)) or admission.canonical_kind not in kinds:
        errors.append("exploration_input_canonical_kind_mismatch")
    techniques = canonical.get("techniques", descriptor.supported_techniques)
    if not isinstance(techniques, (list, tuple, set, frozenset)) or admission.technique not in techniques:
        errors.append("exploration_input_canonical_technique_mismatch")
    required_axes = canonical.get("required_axes", ())
    if not isinstance(required_axes, (list, tuple, set, frozenset)):
        errors.append("exploration_input_axis_contract_invalid")
    else:
        missing_axes = [str(axis) for axis in required_axes if str(axis) not in admission.axis_provenance]
        if missing_axes:
            errors.append("exploration_input_axis_provenance_missing")
    expected_template = canonical.get("template_id")
    if expected_template is not None and admission.template_id != expected_template:
        errors.append("exploration_input_template_mismatch")
    axis_contract = canonical.get("axis_provenance", {})
    if axis_contract is not None:
        if not isinstance(axis_contract, Mapping):
            errors.append("exploration_input_axis_contract_invalid")
        else:
            for axis, spec in axis_contract.items():
                axis_name = str(axis)
                provenance = admission.axis_provenance.get(axis_name)
                if provenance is None:
                    errors.append(f"exploration_input_axis_provenance_missing:{axis_name}")
                    continue
                if not isinstance(spec, Mapping):
                    continue
                if "unit" in spec:
                    actual_unit = (
                        provenance.get("unit") if isinstance(provenance, Mapping) else None
                    )
                    if actual_unit != spec["unit"]:
                        errors.append(f"exploration_input_axis_unit_mismatch:{axis_name}")
                accepted_sources = spec.get("sources", spec.get("accepted_sources"))
                if accepted_sources is not None:
                    if not isinstance(accepted_sources, (list, tuple, set, frozenset)):
                        errors.append(f"exploration_input_axis_sources_contract_invalid:{axis_name}")
                    else:
                        actual_source = (
                            provenance.get("source")
                            if isinstance(provenance, Mapping)
                            else provenance
                        )
                        if actual_source not in accepted_sources:
                            errors.append(f"exploration_input_axis_source_mismatch:{axis_name}")
    if canonical.get("require_calibration") and not admission.calibration_identity:
        errors.append("exploration_input_calibration_missing")
    required_calibrations = canonical.get("required_calibrations", ())
    if required_calibrations:
        if isinstance(required_calibrations, Mapping):
            calibration_names = required_calibrations.keys()
        elif isinstance(required_calibrations, (list, tuple, set, frozenset)):
            calibration_names = required_calibrations
        else:
            errors.append("exploration_input_calibration_contract_invalid")
            calibration_names = ()
        errors.extend(
            f"exploration_input_calibration_missing:{name}"
            for name in calibration_names
            if str(name) not in admission.calibration_identity
        )
    for name, spec in parameters.items():
        if not isinstance(spec, Mapping):
            errors.append(f"exploration_parameter_contract_invalid:{name}")
            continue
        required = bool(spec.get("required", True))
        if name not in request.parameters:
            if required and "default" not in spec:
                errors.append(f"exploration_parameter_missing:{name}")
            continue
        raw = request.parameters[name]
        value = raw.get("value") if isinstance(raw, Mapping) and "value" in raw else raw
        if "type" in spec and not _type_matches(value, str(spec["type"])):
            errors.append(f"exploration_parameter_type_mismatch:{name}")
        if "enum" in spec and value not in spec["enum"]:
            errors.append(f"exploration_parameter_enum_mismatch:{name}")
        if _number(value):
            if "min" in spec and value < spec["min"]:
                errors.append(f"exploration_parameter_below_min:{name}")
            if "max" in spec and value > spec["max"]:
                errors.append(f"exploration_parameter_above_max:{name}")
        if "unit" in spec:
            unit = raw.get("unit") if isinstance(raw, Mapping) else None
            if unit != spec["unit"]:
                errors.append(f"exploration_parameter_unit_mismatch:{name}")
    if not bool(contract.get("allow_unknown_parameters", False)):
        unknown = sorted(set(request.parameters) - set(parameters))
        errors.extend(f"exploration_parameter_unknown:{name}" for name in unknown)
    return tuple(dict.fromkeys(errors))


def validate_output_contract(
    descriptor: ExplorationExecutorDescriptor,
    result: ProviderResultInput,
) -> tuple[str, ...]:
    """Return deterministic output-contract violations (never raise)."""

    contract = descriptor.output_contract
    if not isinstance(contract, Mapping):
        return ("exploration_output_contract_invalid",)
    required = contract.get("required_metrics")
    if not isinstance(required, Mapping):
        return ("exploration_output_contract_schema_missing",)
    rows = {str(row.get("path")): row for row in result.metric_manifest}
    errors: list[str] = []
    expected_descriptor = contract.get("descriptor_id")
    if expected_descriptor is not None and result.descriptor_id != expected_descriptor:
        errors.append("exploration_output_descriptor_mismatch")
    for path, spec in required.items():
        if not isinstance(spec, Mapping):
            errors.append(f"exploration_output_metric_contract_invalid:{path}")
            continue
        row = rows.get(str(path))
        if row is None:
            errors.append(f"exploration_output_metric_missing:{path}")
            continue
        if row.get("status") != spec.get("status", "computed"):
            errors.append(f"exploration_output_metric_status_mismatch:{path}")
        for field in ("unit", "shape", "method"):
            if field in spec and row.get(field) != spec[field]:
                errors.append(f"exploration_output_metric_{field}_mismatch:{path}")
    if not bool(contract.get("allow_extra_metrics", False)):
        extras = sorted(set(rows) - set(required))
        errors.extend(f"exploration_output_metric_undeclared:{path}" for path in extras)
    provenance = contract.get("required_provenance", ())
    if not isinstance(provenance, (list, tuple, set, frozenset)):
        errors.append("exploration_output_provenance_contract_invalid")
    else:
        errors.extend(
            f"exploration_output_provenance_missing:{key}"
            for key in provenance
            if key not in result.provenance
        )
    required_uncertainty = contract.get("required_uncertainty", ())
    if required_uncertainty:
        if isinstance(required_uncertainty, Mapping):
            uncertainty_keys = required_uncertainty.keys()
        elif isinstance(required_uncertainty, (list, tuple, set, frozenset)):
            uncertainty_keys = required_uncertainty
        else:
            errors.append("exploration_output_uncertainty_contract_invalid")
            uncertainty_keys = ()
        errors.extend(
            f"exploration_output_uncertainty_missing:{key}"
            for key in uncertainty_keys
            if str(key) not in result.uncertainty
        )
    return tuple(dict.fromkeys(errors))


__all__ = ["validate_input_contract", "validate_output_contract"]
