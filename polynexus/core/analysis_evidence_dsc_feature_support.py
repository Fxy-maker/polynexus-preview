from __future__ import annotations

from typing import Any

from .analysis_evidence_utils import _clean_float, _clamp_unit, _non_empty_mapping, _relative_spread


def _dsc_feature_support_bundle(
    output: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    peak_components = context["peak_components"]
    supported_components = context["supported_components"]
    scan_rows = context["scan_rows"]
    baseline_corr = context["baseline_corr"]
    exo_up = context["exo_up"]
    residual_type = context["residual_type"]
    quality_flag_text = context["quality_flag_text"]
    scan_r_squared_median = context["scan_r_squared_median"]
    scan_r_squared_spread = context["scan_r_squared_spread"]

    event_support_score = _clamp_unit(
        0.45 * _clamp_unit(len(supported_components) / max(len(peak_components), 1))
        + 0.25 * _clamp_unit((_clean_float(output.get("quality_score")) or 0.0))
        + 0.30 * _clamp_unit(1.0 - (_relative_spread([row.get("r_squared") for row in scan_rows]) or 0.0))
    )
    quality_score = _clean_float(output.get("quality_score"))
    baseline_stability_score = _clamp_unit(
        0.45
        + (0.12 if baseline_corr and baseline_corr not in {"auto", "none", "unknown"} else 0.0)
        + (0.10 if exo_up is not None else 0.0)
        + (0.10 if residual_type not in {"baseline_drift", "baseline_drift_low_t", "baseline_drift_high_t"} else -0.15)
        + (0.10 if quality_score is not None and quality_score >= 0.75 else 0.0)
        - (0.10 if "baseline" in quality_flag_text else 0.0)
    )
    thermodynamic_consistency_score = _clamp_unit(
        0.4 * (1.0 if _clean_float(output.get("Tg_C")) is not None else 0.0)
        + 0.2 * (1.0 if _clean_float(output.get("Tm_peak_C")) is not None else 0.0)
        + 0.2 * (
            1.0
            if _clean_float(output.get("Tc_peak_C")) is not None or _clean_float(output.get("Tcc_peak_C")) is not None
            else 0.0
        )
        + 0.2 * event_support_score
    )
    supported_event_fraction = (len(supported_components) / max(len(peak_components), 1)) if peak_components else None
    structure_support_score = _clamp_unit(
        0.35 * event_support_score
        + 0.20 * baseline_stability_score
        + 0.20 * thermodynamic_consistency_score
        + 0.15 * _clamp_unit(scan_r_squared_median)
        + 0.10 * _clamp_unit(1.0 - (scan_r_squared_spread or 0.0))
    )
    event_support_evidence = _non_empty_mapping(
        [
            ("event_support_score", event_support_score),
            ("baseline_stability_score", baseline_stability_score),
            ("thermodynamic_consistency_score", thermodynamic_consistency_score),
            ("supported_component_count", len(supported_components)),
            ("supported_event_fraction", supported_event_fraction),
            ("scan_r_squared_median", scan_r_squared_median),
            ("scan_r_squared_spread", scan_r_squared_spread),
        ]
    )
    confidence_signals: list[dict[str, Any]] = []
    if event_support_evidence:
        confidence_signals.extend(
            [
                {"name": "event_support_score", "value": event_support_score, "source": "DSC"},
                {"name": "baseline_stability_score", "value": baseline_stability_score, "source": "DSC"},
                {"name": "thermodynamic_consistency_score", "value": thermodynamic_consistency_score, "source": "DSC"},
            ]
        )

    return {
        "event_support_score": event_support_score,
        "baseline_stability_score": baseline_stability_score,
        "thermodynamic_consistency_score": thermodynamic_consistency_score,
        "supported_event_fraction": supported_event_fraction,
        "structure_support_score": structure_support_score,
        "event_support_evidence": event_support_evidence,
        "confidence_signals": confidence_signals,
    }


__all__ = ["_dsc_feature_support_bundle"]
