from __future__ import annotations

from typing import Any

from .analysis_evidence_common import _clean_float
from .analysis_evidence_ir_temperature_2d_feature import _safe_int


def _ir_temperature_2d_sequence_constraint_rows(ir_2d_metrics: dict[str, Any]) -> list[dict[str, Any]]:
    sequence_ready = bool(ir_2d_metrics.get("sequence_axis_ready"))
    n_frames = _safe_int(ir_2d_metrics.get("n_frames"), 0)
    temperature_missing_count = _safe_int(ir_2d_metrics.get("temperature_missing_count"), 0)
    time_missing_count = _safe_int(ir_2d_metrics.get("time_missing_count"), 0)
    hold_time_missing_count = _safe_int(ir_2d_metrics.get("hold_time_missing_count"), 0)
    hold_time_estimated_count = _safe_int(ir_2d_metrics.get("hold_time_estimated_count"), 0)
    heating_monotonic = bool(ir_2d_metrics.get("heating_monotonic"))
    cooling_monotonic = bool(ir_2d_metrics.get("cooling_monotonic"))
    hold_monotonic = bool(ir_2d_metrics.get("hold_monotonic"))
    sequence_order_source = str(ir_2d_metrics.get("sequence_order_source", "") or "").strip()

    return [
        {
            "name": "sequence_axis_incomplete",
            "kind": "hard_fail",
            "source": "IR_temperature_2d",
            "severity": "ERROR",
            "description": "The 2D IR sequence axis is incomplete, so perturbation ordering is not yet trustworthy.",
            "field": "n_frames",
            "rationale": "2D-COS interpretation depends on a stable temperature/time ordering.",
            "triggered": not sequence_ready,
            "observed": {
                "n_frames": n_frames,
                "stage_counts": ir_2d_metrics.get("stage_counts"),
                "temperature_missing_count": temperature_missing_count,
                "time_missing_count": time_missing_count,
                "heating_monotonic": heating_monotonic,
                "cooling_monotonic": cooling_monotonic,
                "hold_monotonic": hold_monotonic,
                "sequence_order_source": sequence_order_source,
            },
        },
        {
            "name": "temperature_axis_missing",
            "kind": "hard_fail",
            "source": "IR_temperature_2d",
            "severity": "ERROR",
            "description": "The temperature axis is missing or incomplete for this 2D IR sequence.",
            "field": "temperature_missing_count",
            "rationale": "A missing temperature axis means the perturbation ordering is not physically anchored.",
            "triggered": temperature_missing_count > 0,
            "observed": {
                "temperature_missing_count": temperature_missing_count,
                "sequence_order_source": sequence_order_source,
                "stage_counts": ir_2d_metrics.get("stage_counts"),
            },
        },
        {
            "name": "stage_order_ambiguous",
            "kind": "soft_warn",
            "source": "IR_temperature_2d",
            "severity": "WARN",
            "description": "Heating, hold, and cooling are not in a clean monotonic order.",
            "field": "stage_counts",
            "rationale": "Mixed perturbation direction weakens any synchronous/asynchronous ordering claim.",
            "triggered": not (heating_monotonic and cooling_monotonic and hold_monotonic),
            "observed": {
                "heating_monotonic": heating_monotonic,
                "cooling_monotonic": cooling_monotonic,
                "hold_monotonic": hold_monotonic,
                "sequence_order_source": sequence_order_source,
            },
        },
        {
            "name": "hold_time_missing_or_estimated",
            "kind": "soft_warn",
            "source": "IR_temperature_2d",
            "severity": "WARN",
            "description": "Hold-segment timing is missing or only estimated.",
            "field": "time_missing_count",
            "rationale": "Uncertain hold timing weakens any plateau or transition interpretation.",
            "triggered": hold_time_missing_count > 0 or hold_time_estimated_count > 0,
            "observed": {
                "time_missing_count": time_missing_count,
                "hold_time_missing_count": hold_time_missing_count,
                "hold_time_estimated_count": hold_time_estimated_count,
            },
        },
        {
            "name": "insufficient_perturbation_frames",
            "kind": "soft_warn",
            "source": "IR_temperature_2d",
            "severity": "WARN",
            "description": "There are not enough perturbation frames for stable 2D-COS interpretation.",
            "field": "n_frames",
            "rationale": "Too few frames can produce attractive maps with weak physical support.",
            "triggered": n_frames < 5,
            "observed": {
                "n_frames": n_frames,
                "stage_counts": ir_2d_metrics.get("stage_counts"),
            },
        },
    ]


__all__ = ["_ir_temperature_2d_sequence_constraint_rows"]
