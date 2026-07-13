from __future__ import annotations

from typing import Any, Iterable

from polynexus.core.preprocess_optimization import (
    ContractValidationError,
    parse_preprocess_intent,
)


PREPROCESS_ACTION_NAMES = {
    "stabilize_baseline",
    "stabilize_matrix_baseline",
    "reduce_noise",
    "denoise_2dcos",
    "rebalance_baseline",
    "trim_low_angle_drift",
    "stabilize_instrument_background",
    "rebalance_background_scale",
    "reduce_profile_noise",
    "stabilize_spectral_baseline",
    "reduce_spectral_noise",
    "protect_weak_resonances",
}

PREPROCESS_PARAMETER_NAMES = {
    "apodization",
    "arpls_diff_order",
    "arpls_lam",
    "background_method",
    "baseline_corr",
    "baseline_degree",
    "baseline_end",
    "baseline_lam",
    "baseline_method",
    "baseline_order",
    "baseline_p",
    "baseline_start",
    "baseline_type",
    "bg_scale_value",
    "gb",
    "instrument_background_method",
    "lb_Hz",
    "savgol_order",
    "savgol_window",
    "smooth_method",
    "smooth_order",
    "smooth_span",
    "smooth_window",
    "smoothing_method",
}


def normalize_preprocess_intent(
    advice: dict[str, Any],
) -> tuple[dict[str, Any] | None, str]:
    payload = advice.get("preprocess_intent")
    if payload in (None, {}):
        return None, ""
    try:
        return parse_preprocess_intent(payload).to_dict(), ""
    except ContractValidationError as exc:
        return None, str(exc)


def contains_preprocess_action(actions: Iterable[object]) -> bool:
    for item in actions:
        name = item.get("name") if isinstance(item, dict) else item
        if str(name or "").strip() in PREPROCESS_ACTION_NAMES:
            return True
    return False


def strip_numeric_preprocess_changes(changes: dict[str, Any]) -> dict[str, Any]:
    return {
        str(name): value
        for name, value in changes.items()
        if str(name) not in PREPROCESS_PARAMETER_NAMES
    }
