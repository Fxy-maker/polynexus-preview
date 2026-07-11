from __future__ import annotations

from typing import Any

from .analysis_evidence_utils import _clean_float


_QUALITY_CONSTRAINT_NAMES = {
    "baseline_sensitive_result",
    "multi_scan_inconsistent",
    "dsc_baseline_sensitive_xc",
    "quality_score_without_event_support",
}


def _evaluate_dsc_quality_constraint(
    item_name: str,
    output: dict[str, Any],
    residual_key: str,
    context: dict[str, Any],
) -> tuple[bool, Any] | None:
    if item_name not in _QUALITY_CONSTRAINT_NAMES:
        return None

    quality_flag_text = context["quality_flag_text"]
    quality = context["quality"]
    xc_pct = context["xc_pct"]
    baseline_sensitive = context["baseline_sensitive"]
    boundary_sensitive = context["boundary_sensitive"]
    tm_peak = context["tm_peak"]
    tc_peak = context["tc_peak"]
    tcc_peak = context["tcc_peak"]
    tg_c = context["tg_c"]
    supported_components = context["supported_components"]
    scan_rows = context["scan_rows"]

    if item_name == "baseline_sensitive_result":
        observed = {
            "residual_type": residual_key or None,
            "quality_flags": quality_flag_text or None,
            "fit_rmse": _clean_float(output.get("fit_rmse")),
        }
        triggered = residual_key in {
            "baseline_drift",
            "baseline_drift_low_t",
            "baseline_drift_high_t",
            "segment_split_issue",
        } or "baseline" in quality_flag_text or (quality is not None and quality < 0.55)
        return triggered, observed

    if item_name == "multi_scan_inconsistent":
        r2_values = context["r2_values"]
        r2_spread = context["r2_spread"]
        quality_spread = context["quality_spread"]
        min_r2 = min((float(value) for value in r2_values), default=None)
        max_r2 = max((float(value) for value in r2_values), default=None)
        observed = {
            "scan_count": len(scan_rows),
            "r_squared_spread": r2_spread,
            "quality_spread": quality_spread,
            "min_r_squared": min_r2,
            "max_r_squared": max_r2,
        }
        triggered = bool(
            scan_rows
            and (
                (r2_spread is not None and r2_spread > 0.06)
                or (quality_spread is not None and quality_spread > 0.10)
                or (min_r2 is not None and max_r2 is not None and (max_r2 - min_r2) > 0.08)
            )
        )
        return triggered, observed

    if item_name == "dsc_baseline_sensitive_xc":
        observed = {
            "Xc_pct": xc_pct,
            "baseline_sensitivity_pct": baseline_sensitive,
            "integration_boundary_sensitivity_pct": boundary_sensitive,
        }
        triggered = xc_pct is not None and (
            (baseline_sensitive is not None and baseline_sensitive >= 10.0)
            or (boundary_sensitive is not None and boundary_sensitive >= 8.0)
        )
        return triggered, observed

    event_count = len(supported_components)
    observed = {
        "quality_score": quality,
        "peak_component_count": event_count,
        "Tm_peak_C": tm_peak,
        "Tc_peak_C": tc_peak,
        "Tcc_peak_C": tcc_peak,
    }
    triggered = quality is not None and quality >= 0.75 and (
        event_count < 1
        or (tm_peak is None and tc_peak is None and tcc_peak is None and tg_c is None)
    )
    return triggered, observed


__all__ = ["_evaluate_dsc_quality_constraint"]
