from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from numbers import Real
from typing import Any


@dataclass(frozen=True)
class ParamRule:
    field_name: str
    value_type: type
    constraint: tuple[float, float] | tuple[str, ...] | None


WAXS_PARAM_MAP: dict[str, ParamRule] = {
    "peak_function": ParamRule("peak_function", str, ("gaussian", "lorentzian", "pseudo_voigt")),
    "smooth_window": ParamRule("smooth_window", int, (3, 15)),
    "background_method": ParamRule("background_method", str, ("linear", "polynomial", "spline", "chebyshev")),
    "arpls_lam": ParamRule("arpls_lam", float, (1e4, 1e8)),
    "amorphous_subtraction": ParamRule("amorphous_subtraction", str, ("spline", "polynomial", "manual")),
    "amorphous_n_peaks": ParamRule("amorphous_n_peaks", int, (1, 2)),
    "peak_distance": ParamRule("peak_distance", float, (0.5, 2.0)),
    "two_theta_offset": ParamRule("two_theta_offset", float, (-0.5, 0.5)),
    "max_peaks": ParamRule("max_peaks", int, (4, 12)),
}

DSC_PARAM_MAP: dict[str, ParamRule] = {
    "exo_up": ParamRule("exo_up", bool, None),
    "baseline_type": ParamRule("baseline_corr", str, ("auto", "linear", "polynomial", "spline", "tangential")),
    "peak_function": ParamRule("peak_function", str, ("gaussian", "lorentzian", "voigt", "pseudo_voigt")),
    "smooth_window": ParamRule("smooth_window", int, (3, 31)),
    "Tg_method": ParamRule("Tg_method", str, ("half_height", "inflection", "onset", "fictive")),
    "tg_search_low_C": ParamRule("Tg_search_low_C", float, (0.0, 180.0)),
    "tg_search_high_C": ParamRule("Tg_search_high_C", float, (20.0, 240.0)),
    "tm_search_low_C": ParamRule("Tm_search_low_C", float, (50.0, 260.0)),
    "tm_search_high_C": ParamRule("Tm_search_high_C", float, (120.0, 380.0)),
    "tc_search_low_C": ParamRule("Tc_search_low_C", float, (0.0, 240.0)),
    "tc_search_high_C": ParamRule("Tc_search_high_C", float, (80.0, 320.0)),
    "peak_prominence_ratio": ParamRule("peak_prominence_ratio", float, (0.005, 0.2)),
    "min_event_enthalpy_Jg": ParamRule("min_event_enthalpy_Jg", float, (0.01, 5.0)),
    "max_melting_peak_width_C": ParamRule("max_melting_peak_width_C", float, (5.0, 120.0)),
}

SAXS_PARAM_MAP: dict[str, ParamRule] = {
    "bg_scale_value": ParamRule("bg_scale_value", float, (0.50, 1.50)),
    "smooth_method": ParamRule(
        "smooth_method", str, ("none", "savgol", "moving_average")
    ),
    "smooth_span": ParamRule("smooth_span", int, (3, 31)),
    "q_bragg_min": ParamRule("q_bragg_min", float, (0.05, 0.6)),
    "q_bragg_max": ParamRule("q_bragg_max", float, (0.3, 2.0)),
    "q_corr_min": ParamRule("q_corr_min", float, (0.03, 1.0)),
    "q_corr_max": ParamRule("q_corr_max", float, (0.5, 4.0)),
    "idf_peak_rel_thresh": ParamRule("idf_peak_rel_thresh", float, (0.005, 0.3)),
    "idf_valley_rel_thresh": ParamRule("idf_valley_rel_thresh", float, (0.005, 0.3)),
    "tangent_lc_min_nm": ParamRule("tangent_lc_min_nm", float, (0.5, 8.0)),
    "T_melt_expected": ParamRule("T_melt_expected", float, (0.0, 500.0)),
    "savgol_window": ParamRule("savgol_window", int, (3, 31)),
    "savgol_order": ParamRule("savgol_order", int, (1, 5)),
    "lorentz_fit_method": ParamRule("lorentz_fit_method", str, ("lmfit", "scipy")),
}

NMR_PARAM_MAP: dict[str, ParamRule] = {
    "baseline_method": ParamRule("baseline_method", str, ("polynomial", "linear", "spline", "simple_polynomial")),
    "baseline_order": ParamRule("baseline_order", int, (1, 9)),
    "apodization": ParamRule("apodization", str, ("exponential", "gaussian", "none")),
    "lb_Hz": ParamRule("lb_Hz", float, (0.5, 40.0)),
    "line_broadening": ParamRule("lb_Hz", float, (0.1, 10.0)),
    "zero_filling": ParamRule("fid_zero_fill_factor", int, (1024, 65536)),
    "fid_zero_fill_factor": ParamRule("fid_zero_fill_factor", int, (1, 32)),
    "gb": ParamRule("gb", float, (0.0, 1.0)),
    "peak_distance_ppm": ParamRule("peak_distance_ppm", float, (0.01, 5.0)),
    "peak_height_min": ParamRule("peak_height_min", float, (0.001, 0.2)),
    "peak_threshold": ParamRule("peak_height_min", float, (0.01, 0.5)),
    "deconvolution_method": ParamRule("deconvolution_method", str, ("lorentzian", "gaussian", "mixed")),
    "max_peaks": ParamRule("max_peaks", int, (4, 60)),
}

IR_PARAM_MAP: dict[str, ParamRule] = {
    "baseline_method": ParamRule("baseline_method", str, ("rubberband", "linear", "polynomial", "als", "mute_zone", "none")),
    "smooth_window": ParamRule("smooth_window", int, (3, 31)),
    "peak_threshold": ParamRule("peak_height_min", float, (0.001, 0.20)),
    "peak_height_min": ParamRule("peak_height_min", float, (0.001, 0.20)),
    "peak_prominence": ParamRule("peak_prominence_min", float, (0.001, 0.20)),
    "peak_prominence_min": ParamRule("peak_prominence_min", float, (0.001, 0.20)),
    "peak_distance": ParamRule("peak_distance", float, (3.0, 80.0)),
    "peak_fit_window_cm1": ParamRule("peak_fit_window_cm1", float, (8.0, 120.0)),
    "assignment_tolerance_cm1": ParamRule("assignment_tolerance_cm1", float, (5.0, 30.0)),
    "cross_peak_exclusion_cm1": ParamRule("cross_peak_exclusion_cm1", float, (15.0, 80.0)),
    "sequence_axis_mode": ParamRule("sequence_axis_mode", str, ("auto", "filename", "metadata")),
    "sequence_axis_metadata_path": ParamRule("sequence_axis_metadata_path", str, None),
    "wavenumber_min": ParamRule("wavenumber_range", float, (350.0, 2000.0)),
    "wavenumber_max": ParamRule("wavenumber_range", float, (1800.0, 4500.0)),
    "normalization_method": ParamRule("normalization_method", str, ("minmax", "area", "peak", "none")),
    "lineshape": ParamRule("lineshape", str, ("lorentzian", "gaussian", "pseudo_voigt")),
    "peak_function": ParamRule("lineshape", str, ("lorentzian", "gaussian", "pseudo_voigt")),
}


def apply_changes(config: Any, changes_dict: dict[str, Any], technique: str | None = None) -> tuple[bool, str]:
    """Validate and apply LLM parameter changes to a technique config object."""
    if not isinstance(changes_dict, dict):
        return False, "changes_dict must be a dict"
    if not changes_dict:
        return True, ""

    param_map, technique_name = _param_map_for_config(config, technique)
    pending: dict[str, tuple[str, Any]] = {}
    for param_name, new_value in changes_dict.items():
        rule = param_map.get(param_name)
        if rule is None:
            return False, f"Unknown {technique_name} parameter: {param_name}"
        if not hasattr(config, rule.field_name):
            return False, f"Config has no field: {rule.field_name}"

        ok, coerced, error = _validate_value(param_name, new_value, rule)
        if not ok:
            return False, error
        pending[param_name] = (rule.field_name, coerced)

    probe = deepcopy(config)
    for param_name, (field_name, value) in pending.items():
        _set_config_value(probe, field_name, param_name, value)

    dependency_error = _check_dependencies(probe, changes_dict, technique_name)
    if dependency_error:
        return False, dependency_error

    for param_name, (field_name, value) in pending.items():
        _set_config_value(config, field_name, param_name, value)
    return True, ""


def _param_map_for_config(config: Any, technique: str | None) -> tuple[dict[str, ParamRule], str]:
    if technique:
        name = technique.upper()
    else:
        class_name = type(config).__name__.upper()
        if "DSC" in class_name or hasattr(config, "Tm_method"):
            name = "DSC"
        elif "SAXS" in class_name or hasattr(config, "q_bragg_min"):
            name = "SAXS"
        elif "WAXS" in class_name or hasattr(config, "two_theta_offset"):
            name = "WAXS"
        elif "IR" in class_name or (hasattr(config, "peak_height_min") and hasattr(config, "normalization_method")):
            name = "IR"
        elif "NMR" in class_name or hasattr(config, "peak_distance_ppm"):
            name = "NMR"
        else:
            name = "WAXS"
    if name == "DSC":
        return DSC_PARAM_MAP, "DSC"
    if name == "SAXS":
        return SAXS_PARAM_MAP, "SAXS"
    if name == "IR":
        return IR_PARAM_MAP, "IR"
    if name == "NMR":
        return NMR_PARAM_MAP, "NMR"
    return WAXS_PARAM_MAP, "WAXS"


def _set_config_value(config: Any, field_name: str, param_name: str, value: Any) -> None:
    if param_name == "wavenumber_min":
        current = getattr(config, field_name)
        setattr(config, field_name, (float(value), float(current[1])))
        return
    if param_name == "wavenumber_max":
        current = getattr(config, field_name)
        setattr(config, field_name, (float(current[0]), float(value)))
        return
    setattr(config, field_name, value)


def _validate_value(param_name: str, value: Any, rule: ParamRule) -> tuple[bool, Any, str]:
    expected = rule.value_type
    if expected is int:
        if isinstance(value, bool) or not isinstance(value, int):
            return False, None, f"{param_name}: expected int, got {type(value).__name__}"
        coerced = int(value)
    elif expected is float:
        if isinstance(value, bool) or not isinstance(value, Real):
            return False, None, f"{param_name}: expected float, got {type(value).__name__}"
        coerced = float(value)
    elif expected is bool:
        if not isinstance(value, bool):
            return False, None, f"{param_name}: expected bool, got {type(value).__name__}"
        coerced = bool(value)
    elif expected is str:
        if not isinstance(value, str):
            return False, None, f"{param_name}: expected str, got {type(value).__name__}"
        coerced = value
    else:
        return False, None, f"{param_name}: unsupported expected type {expected}"

    constraint = rule.constraint
    if constraint is None:
        return True, coerced, ""
    if _is_choice_constraint(constraint):
        if coerced not in constraint:
            return False, None, f"{param_name}: '{coerced}' not in {list(constraint)}"
    else:
        lower, upper = float(constraint[0]), float(constraint[1])
        if not (lower <= float(coerced) <= upper):
            return False, None, f"{param_name}: {coerced} out of range [{lower}, {upper}]"
    return True, coerced, ""


def _is_choice_constraint(constraint: tuple[float, float] | tuple[str, ...] | None) -> bool:
    if constraint is None:
        return False
    return all(isinstance(item, str) for item in constraint)


def _check_dependencies(config: Any, changes: dict[str, Any], technique_name: str) -> str:
    if technique_name == "DSC":
        return _check_dsc_dependencies(config, changes)
    if technique_name == "SAXS":
        return _check_saxs_dependencies(config, changes)
    if technique_name == "IR":
        return _check_ir_dependencies(config, changes)
    if technique_name == "NMR":
        return _check_nmr_dependencies(config, changes)
    return _check_waxs_dependencies(config, changes)


def _check_waxs_dependencies(config: Any, changes: dict[str, Any]) -> str:
    if "smooth_window" in changes and config.smooth_window % 2 == 0:
        return "Dependency [smooth]: smooth_window must be odd"

    if {"peak_distance", "max_peaks"} <= set(changes):
        return "Dependency [peak_detection]: adjust peak_distance before changing max_peaks"

    if {"amorphous_subtraction", "amorphous_n_peaks"} <= set(changes):
        return "Dependency [amorphous]: adjust amorphous_subtraction before amorphous_n_peaks"

    arpls_diff_order = getattr(config, "arpls_diff_order", 2)
    if "arpls_lam" in changes and arpls_diff_order not in {1, 2}:
        return "Dependency [arpls]: arpls_diff_order must be 1 or 2"

    return ""


def _check_dsc_dependencies(config: Any, changes: dict[str, Any]) -> str:
    low_tm = getattr(config, "Tm_search_low_C", None)
    high_tm = getattr(config, "Tm_search_high_C", None)
    if low_tm is not None and high_tm is not None and float(low_tm) >= float(high_tm):
        return "Dependency [tm_search_range]: tm_search_low_C must be lower than tm_search_high_C"

    low_tc = getattr(config, "Tc_search_low_C", None)
    high_tc = getattr(config, "Tc_search_high_C", None)
    if low_tc is not None and high_tc is not None and float(low_tc) >= float(high_tc):
        return "Dependency [tc_search_range]: tc_search_low_C must be lower than tc_search_high_C"

    if "smooth_window" in changes and getattr(config, "smooth_window", 1) % 2 == 0:
        return "Dependency [smooth]: smooth_window must be odd"

    return ""


def _check_saxs_dependencies(config: Any, changes: dict[str, Any]) -> str:
    q_bragg_min = getattr(config, "q_bragg_min", None)
    q_bragg_max = getattr(config, "q_bragg_max", None)
    if q_bragg_min is not None and q_bragg_max is not None and float(q_bragg_min) >= float(q_bragg_max):
        return "Dependency [q_bragg_range]: q_bragg_min must be lower than q_bragg_max"

    q_corr_min = getattr(config, "q_corr_min", None)
    q_corr_max = getattr(config, "q_corr_max", None)
    if q_corr_min is not None and q_corr_max is not None and float(q_corr_min) >= float(q_corr_max):
        return "Dependency [q_corr_range]: q_corr_min must be lower than q_corr_max"

    if "savgol_window" in changes and getattr(config, "savgol_window", 1) % 2 == 0:
        return "Dependency [smooth]: savgol_window must be odd"

    if getattr(config, "savgol_window", 3) <= getattr(config, "savgol_order", 2):
        return "Dependency [smooth]: savgol_window must be greater than savgol_order"

    return ""


def _check_ir_dependencies(config: Any, changes: dict[str, Any]) -> str:
    if "smooth_window" in changes and getattr(config, "smooth_window", 1) % 2 == 0:
        return "Dependency [smooth]: smooth_window must be odd"

    if getattr(config, "smooth_window", 3) <= getattr(config, "smooth_order", 2):
        return "Dependency [smooth]: smooth_window must be greater than smooth_order"

    wavenumber_range = getattr(config, "wavenumber_range", None)
    if wavenumber_range is not None and len(wavenumber_range) == 2:
        low, high = float(wavenumber_range[0]), float(wavenumber_range[1])
        if low >= high:
            return "Dependency [wavenumber_range]: wavenumber_min must be lower than wavenumber_max"

    return ""


def _check_nmr_dependencies(config: Any, changes: dict[str, Any]) -> str:
    if "baseline_order" in changes and getattr(config, "baseline_order", 1) < 1:
        return "Dependency [baseline_order]: baseline_order must be positive"
    if "peak_distance_ppm" in changes and getattr(config, "peak_distance_ppm", 0.0) <= 0:
        return "Dependency [peak_distance_ppm]: peak_distance_ppm must be positive"
    if getattr(config, "max_peaks", 0) < 4:
        return "Dependency [max_peaks]: max_peaks must be at least 4"
    return ""
