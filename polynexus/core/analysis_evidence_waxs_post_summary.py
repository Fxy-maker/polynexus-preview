from __future__ import annotations

from typing import Any

from .analysis_evidence_common import _clean_float


def _waxs_summary_details(
    output: dict[str, Any],
    peak_evidence: dict[str, Any],
    structure_evidence: dict[str, Any],
    condition_evidence: dict[str, Any],
) -> dict[str, Any]:
    summary_bits: list[str] = []
    confidence_signals: list[dict[str, Any]] = []

    if peak_evidence and peak_evidence.get("peak_count") is not None:
        peak_count_value = _clean_float(peak_evidence.get("peak_count"))
        if peak_count_value is not None:
            confidence_signals.append({"name": "peak_evidence_peak_count", "value": peak_count_value, "source": "WAXS"})
        if output.get("temperature_axis_confidence") is not None:
            summary_bits.append(f"temperature_axis={output.get('temperature_axis_confidence')}")
        elif output.get("condition_confidence") is not None:
            summary_bits.append(f"condition_confidence={output.get('condition_confidence')}")
        if condition_evidence.get("condition_source"):
            summary_bits.append(f"condition_source={condition_evidence.get('condition_source')}")
        if structure_evidence.get("physical_support_pass") is not None:
            summary_bits.append(f"physical_support={bool(structure_evidence.get('physical_support_pass'))}")
        if structure_evidence.get("paper_ready_candidate") is not None:
            summary_bits.append(f"paper_ready={bool(structure_evidence.get('paper_ready_candidate'))}")

    if output.get("frame_count") is not None:
        summary_bits.append(f"frames={output.get('frame_count')}")
    if output.get("frame_low_conf_count") is not None:
        summary_bits.append(f"low_conf_frames={output.get('frame_low_conf_count')}")
    if output.get("dominant_frame_failure_type"):
        summary_bits.append(f"dominant_failure={output.get('dominant_frame_failure_type')}")
    if output.get("peak_family_count") is not None:
        summary_bits.append(f"peak_families={output.get('peak_family_count')}")
    if output.get("peak_family_continuity_score") is not None:
        summary_bits.append(f"family_continuity={output.get('peak_family_continuity_score')}")
    if output.get("peak_family_identity_swap_count") is not None:
        summary_bits.append(f"family_swaps={output.get('peak_family_identity_swap_count')}")
    if output.get("D_trend_support_score") is not None:
        summary_bits.append(f"D_trend={output.get('D_trend_support_score')}")
    if output.get("D_trend_monotonicity"):
        summary_bits.append(f"D_trend_mode={output.get('D_trend_monotonicity')}")
    if output.get("Xc_trend_support_score") is not None:
        summary_bits.append(f"xc_trend={output.get('Xc_trend_support_score')}")
    if output.get("transition_support_score") is not None:
        summary_bits.append(f"transition_support={output.get('transition_support_score')}")
    if output.get("Xc_trend_monotonicity"):
        summary_bits.append(f"xc_trend_mode={output.get('Xc_trend_monotonicity')}")

    return {
        "summary_bits": summary_bits,
        "confidence_signals": confidence_signals,
    }


__all__ = ["_waxs_summary_details"]
