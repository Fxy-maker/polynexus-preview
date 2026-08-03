"""Explicit SAXS panel-to-config binding with diagnostics."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
import json
import math
from numbers import Integral, Real
from typing import Any, Callable, Mapping

from .saxs_engine.config import (
    TENSILE_AXIS_CONVENTION,
    normalize_tensile_axis,
)


def _as_float_or_nan(value: Any) -> float:
    if value is None:
        return float("nan")
    text = str(value).strip()
    return float(text) if text else float("nan")


def _as_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    return float(text) if text else None


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on", "pyfai"}


_FIELD_BINDINGS: dict[str, tuple[str, Callable[[Any], Any]]] = {
    "baseline_method": ("baseline_method", str),
    "smooth_window": ("savgol_window", int),
    "q_range_min": ("q_min", float),
    "q_range_max": ("q_max", float),
    "integration_mode": ("use_pyfai_integration", _as_bool),
    "crystallinity": ("crystallinity", _as_float_or_nan),
    "T_melt_expected": ("T_melt_expected", _as_optional_float),
}


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, Real):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return str(value)


def _binding_for(config: Any, panel_key: str):
    binding = _FIELD_BINDINGS.get(panel_key)
    if binding is not None:
        return binding if hasattr(config, binding[0]) else None
    if hasattr(config, panel_key):
        return panel_key, lambda value: value
    return None


def apply_saxs_config_panel_values(
    config: Any, values: Mapping[str, Any] | None
) -> dict[str, Any]:
    """Apply panel values and return applied/unavailable diagnostics."""

    report: dict[str, Any] = {
        "applied": {},
        "unavailable": {},
        "normalized_values": {},
        "diagnostic_only": {},
        "provenance": {},
    }
    if not isinstance(values, Mapping):
        return report

    axis_keys = {"tensile_axis_deg", "tensile_axis_convention"}
    if any(key in values for key in axis_keys):
        try:
            axis_value, axis_convention = normalize_tensile_axis(
                values.get("tensile_axis_deg"),
                values.get("tensile_axis_convention"),
            )
        except ValueError as exc:
            report["unavailable"]["tensile_axis_deg"] = str(exc)
        else:
            setattr(config, "tensile_axis_deg", axis_value)
            setattr(config, "tensile_axis_convention", axis_convention)
            report["applied"]["tensile_axis_deg"] = "tensile_axis_deg"
            report["applied"]["tensile_axis_convention"] = "tensile_axis_convention"
            report["normalized_values"]["tensile_axis_deg"] = axis_value
            report["normalized_values"]["tensile_axis_convention"] = axis_convention
            report["provenance"]["tensile_axis_deg"] = {
                "source": "explicit_run_config",
                "convention": axis_convention or TENSILE_AXIS_CONVENTION,
            }

    for raw_key, raw_value in values.items():
        panel_key = str(raw_key)
        if panel_key in axis_keys:
            continue
        binding = _binding_for(config, panel_key)
        if binding is None:
            explicit = _FIELD_BINDINGS.get(panel_key)
            report["unavailable"][panel_key] = (
                f"binding_target_missing:{explicit[0]}"
                if explicit is not None
                else "unknown_panel_key"
            )
            continue

        field_name, converter = binding
        try:
            value = converter(raw_value)
            setattr(config, field_name, value)
        except (TypeError, ValueError, OverflowError, AttributeError) as exc:
            report["unavailable"][panel_key] = f"invalid_value:{exc}"
            continue

        report["applied"][panel_key] = field_name
        report["normalized_values"][panel_key] = value
        if panel_key == "baseline_method":
            report["diagnostic_only"][panel_key] = (
                "persisted_without_algorithm_mapping"
            )
        elif panel_key not in _FIELD_BINDINGS:
            report["diagnostic_only"][panel_key] = (
                "canonical_name_without_type_conversion"
            )

    try:
        config.config_binding_report = report
    except Exception:
        pass
    return report


def saxs_config_snapshot(config: Any) -> dict[str, Any]:
    """Return a strict-JSON-safe configuration snapshot."""

    if is_dataclass(config):
        snapshot = asdict(config)
    elif hasattr(config, "__dict__"):
        snapshot = dict(vars(config))
    else:
        snapshot = {}
    safe = _json_safe(snapshot)
    try:
        return json.loads(
            json.dumps(safe, ensure_ascii=False, allow_nan=False, default=str)
        )
    except (TypeError, ValueError):
        return {str(key): _json_safe(value) for key, value in snapshot.items()}


__all__ = [
    "apply_saxs_config_panel_values",
    "normalize_tensile_axis",
    "saxs_config_snapshot",
]
