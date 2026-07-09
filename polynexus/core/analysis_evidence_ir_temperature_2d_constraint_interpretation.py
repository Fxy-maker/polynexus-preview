from __future__ import annotations

from typing import Any

from .analysis_evidence_common import _clean_float
from .analysis_evidence_ir_temperature_2d_feature import _safe_int


def _ir_temperature_2d_interpretation_constraint_rows(ir_2d_metrics: dict[str, Any]) -> list[dict[str, Any]]:
    dynamic_rms = _clean_float(ir_2d_metrics.get("dynamic_rms"))
    dynamic_signal_rms = _clean_float(ir_2d_metrics.get("dynamic_signal_rms", dynamic_rms))
    sync_cross_peak_count = _safe_int(ir_2d_metrics.get("sync_cross_peak_count"), 0)
    async_cross_peak_count = _safe_int(ir_2d_metrics.get("async_cross_peak_count"), 0)
    cross_peak_count = _safe_int(ir_2d_metrics.get("cross_peak_count"), 0)
    assigned_cross_peak_count = _safe_int(ir_2d_metrics.get("assigned_cross_peak_count"), 0)
    unassigned_cross_peak_count = _safe_int(ir_2d_metrics.get("unassigned_cross_peak_count"), 0)
    async_with_sync_support_count = _safe_int(ir_2d_metrics.get("async_with_sync_support_count"), 0)
    top_sync_diagonal_distance = _clean_float(ir_2d_metrics.get("top_sync_diagonal_distance_cm1"))
    top_async_diagonal_distance = _clean_float(ir_2d_metrics.get("top_async_diagonal_distance_cm1"))
    top_sync_assigned = bool(ir_2d_metrics.get("top_sync_assigned", False))
    top_async_assigned = bool(ir_2d_metrics.get("top_async_assigned", False))
    top_async_has_sync_support = bool(ir_2d_metrics.get("top_async_has_sync_support", False))
    noda_rule_interpretation_ready = bool(ir_2d_metrics.get("noda_rule_interpretation_ready", False))
    transition_count = _safe_int(ir_2d_metrics.get("transition_count"), 0)

    return [
        {
            "name": "weak_cos_signal",
            "kind": "soft_warn",
            "source": "IR_temperature_2d",
            "severity": "WARN",
            "description": "2D-COS signal is too weak for stable synchronous/asynchronous interpretation.",
            "field": "sync_cross_peak_count",
            "rationale": "A visible sync/async signal is required before promoting transition claims.",
            "triggered": (
                sync_cross_peak_count <= 0
                or async_cross_peak_count <= 0
                or (dynamic_signal_rms is not None and dynamic_signal_rms < 0.005)
            ),
            "observed": {
                "sync_cross_peak_count": sync_cross_peak_count,
                "async_cross_peak_count": async_cross_peak_count,
                "dynamic_rms": dynamic_signal_rms,
            },
        },
        {
            "name": "cross_peak_near_diagonal",
            "kind": "soft_warn",
            "source": "IR_temperature_2d",
            "severity": "WARN",
            "description": "The strongest 2D-COS cross peak sits too close to the diagonal.",
            "field": "top_async_diagonal_distance_cm1",
            "rationale": "A near-diagonal cross peak is often not distinct enough for a stable interpretation.",
            "triggered": (
                (top_sync_diagonal_distance is not None and top_sync_diagonal_distance < 45.0)
                or (top_async_diagonal_distance is not None and top_async_diagonal_distance < 45.0)
            ),
            "observed": {
                "top_sync_diagonal_distance_cm1": top_sync_diagonal_distance,
                "top_async_diagonal_distance_cm1": top_async_diagonal_distance,
            },
        },
        {
            "name": "cross_peak_without_band_assignment",
            "kind": "soft_warn",
            "source": "IR_temperature_2d",
            "severity": "WARN",
            "description": "The leading cross peaks are not assigned cleanly to reference bands.",
            "field": "assigned_cross_peak_count",
            "rationale": "Unassigned peaks can be useful for diagnosis, but they should not carry the final mechanistic story.",
            "triggered": (
                cross_peak_count > 0
                and (assigned_cross_peak_count <= 0 or unassigned_cross_peak_count >= assigned_cross_peak_count)
            ),
            "observed": {
                "cross_peak_count": cross_peak_count,
                "assigned_cross_peak_count": assigned_cross_peak_count,
                "unassigned_cross_peak_count": unassigned_cross_peak_count,
                "top_sync_assigned": top_sync_assigned,
                "top_async_assigned": top_async_assigned,
            },
        },
        {
            "name": "async_peak_without_sync_support",
            "kind": "soft_warn",
            "source": "IR_temperature_2d",
            "severity": "WARN",
            "description": "The asynchronous peak is not backed by enough synchronous support.",
            "field": "async_with_sync_support_count",
            "rationale": "Async peaks are weaker evidence when they are not paired with a stable synchronous relationship.",
            "triggered": async_cross_peak_count > 0 and (async_with_sync_support_count <= 0 or not top_async_has_sync_support),
            "observed": {
                "async_cross_peak_count": async_cross_peak_count,
                "async_with_sync_support_count": async_with_sync_support_count,
                "top_async_has_sync_support": top_async_has_sync_support,
            },
        },
        {
            "name": "noda_rule_not_applicable",
            "kind": "soft_warn",
            "source": "IR_temperature_2d",
            "severity": "WARN",
            "description": "Noda-rule interpretation is not yet supported by the current evidence chain.",
            "field": "noda_rule_interpretation_ready",
            "rationale": "Do not promote sequence-order claims until sync/async support and band assignment both hold.",
            "triggered": async_cross_peak_count > 0 and not noda_rule_interpretation_ready,
            "observed": {
                "noda_rule_interpretation_ready": noda_rule_interpretation_ready,
                "assigned_cross_peak_count": assigned_cross_peak_count,
                "top_async_has_sync_support": top_async_has_sync_support,
            },
        },
        {
            "name": "transition_candidate_present",
            "kind": "evidence_only",
            "source": "IR_temperature_2d",
            "severity": "INFO",
            "description": "A temperature-dependent transition candidate is present in the tracked bands.",
            "field": "transition_count",
            "rationale": "Treat this as evidence only until the matrix quality is stable.",
            "triggered": transition_count > 0,
            "observed": {
                "transition_count": transition_count,
                "transition_temperatures_C": ir_2d_metrics.get("transition_temperatures_C"),
            },
        },
    ]


__all__ = ["_ir_temperature_2d_interpretation_constraint_rows"]
