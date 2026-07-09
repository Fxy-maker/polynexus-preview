from __future__ import annotations

from typing import Any


def _ir_temperature_2d_summary_details(temp_metrics: dict[str, Any]) -> dict[str, Any]:
    summary_bits: list[str] = []

    if temp_metrics.get("n_frames") is not None:
        summary_bits.append(f"frames={temp_metrics.get('n_frames')}")
    if temp_metrics.get("T_range_C"):
        summary_bits.append(f"T_range={temp_metrics.get('T_range_C')}")
    if temp_metrics.get("sequence_axis_score") is not None:
        summary_bits.append(f"sequence_axis={temp_metrics.get('sequence_axis_score')}")
    if temp_metrics.get("matrix_quality_score") is not None:
        summary_bits.append(f"matrix_quality={temp_metrics.get('matrix_quality_score')}")
    if temp_metrics.get("cos_signal_score") is not None:
        summary_bits.append(f"cos_signal={temp_metrics.get('cos_signal_score')}")
    if temp_metrics.get("sync_cross_peak_count") is not None:
        summary_bits.append(f"sync_peaks={temp_metrics.get('sync_cross_peak_count')}")
    if temp_metrics.get("async_cross_peak_count") is not None:
        summary_bits.append(f"async_peaks={temp_metrics.get('async_cross_peak_count')}")
    if temp_metrics.get("transition_count") is not None:
        summary_bits.append(f"transitions={temp_metrics.get('transition_count')}")
    if temp_metrics.get("band_index_transition_support_band_count") is not None:
        summary_bits.append(f"band_support={temp_metrics.get('band_index_transition_support_band_count')}")
    if temp_metrics.get("band_index_transition_reproducible") is not None:
        summary_bits.append(f"trend_reproducible={bool(temp_metrics.get('band_index_transition_reproducible'))}")
    if temp_metrics.get("neg_fraction") is not None:
        summary_bits.append(f"neg_fraction={temp_metrics.get('neg_fraction')}")
    if temp_metrics.get("interpretation_ready") is not None:
        summary_bits.append(f"interpretation_ready={bool(temp_metrics.get('interpretation_ready'))}")
    if temp_metrics.get("paper_conclusion_ready") is not None:
        summary_bits.append(f"paper_ready={bool(temp_metrics.get('paper_conclusion_ready'))}")

    return {"summary_bits": summary_bits}


__all__ = ["_ir_temperature_2d_summary_details"]
