from __future__ import annotations

from typing import Any

import numpy as np

from .analysis_evidence_saxs_condition_values import _condition_values
from .analysis_evidence_utils import _clean_float, _non_empty_mapping, _relative_spread


def _saxs_strain_sequence_evidence(
    output: dict[str, Any],
    batch_rows: list[dict[str, Any]],
    *,
    condition_label: str,
    condition_source: str,
    condition_source_key: str,
    condition_source_text: str,
    condition_confidence: float | None,
    condition_missing_frames: Any,
    condition_continuity_score: float | None,
) -> dict[str, Any]:
    strain_values = _condition_values(output, batch_rows, "strain")
    strain_pct = _clean_float(output.get("strain_pct"))
    if not (strain_values or condition_label.lower() == "strain" or strain_pct is not None):
        return {}

    strain_missing_count = output.get("strain_missing_count")
    if strain_missing_count is None and batch_rows:
        strain_missing_count = sum(
            1
            for row in batch_rows
            if isinstance(row, dict)
            and _clean_float(row.get("strain_pct")) is None
            and _clean_float(row.get("condition_value")) is None
        )
    strain_duplicate_count = output.get("strain_duplicate_count")
    if strain_duplicate_count is None and strain_values:
        strain_duplicate_count = max(0, len(strain_values) - len({str(value) for value in strain_values}))
    strain_axis_confidence = _clean_float(
        output.get("strain_axis_confidence", output.get("condition_confidence"))
    )
    if strain_axis_confidence is None:
        strain_axis_confidence = condition_confidence

    if strain_values:
        strain_array = np.asarray(strain_values, dtype=float)
        strain_min = float(np.min(strain_array))
        strain_max = float(np.max(strain_array))
        if strain_array.size >= 2:
            diffs = np.diff(strain_array)
            increasing = bool(np.all(diffs >= 0))
            decreasing = bool(np.all(diffs <= 0))
            if increasing:
                sequence_direction = "increasing"
            elif decreasing:
                sequence_direction = "decreasing"
            else:
                sequence_direction = "mixed"
            strain_step_median = float(np.median(diffs))
            strain_step_spread = _relative_spread(diffs.tolist()) if diffs.size >= 2 else None
        else:
            sequence_direction = "unknown"
            strain_step_median = None
            strain_step_spread = None
        strain_monotonic = sequence_direction in {"increasing", "decreasing"}
    else:
        strain_min = strain_max = None
        strain_step_median = None
        strain_step_spread = None
        sequence_direction = (
            str(output.get("sequence_direction", "") or "").strip().lower() or "unknown"
        )
        strain_monotonic = bool(output.get("strain_monotonic", False))

    strain_axis_evidence = _non_empty_mapping(
        [
            ("condition_label", condition_label or None),
            ("condition_unit", str(output.get("condition_unit", "") or "").strip() or None),
            ("condition_source", condition_source or None),
            ("condition_source_key", condition_source_key or None),
            ("condition_source_text", condition_source_text or None),
            ("condition_confidence", condition_confidence),
            ("condition_missing_frames", condition_missing_frames),
            ("condition_continuity_score", condition_continuity_score),
            ("strain_values", strain_values if strain_values else None),
            ("strain_min_pct", strain_min),
            ("strain_max_pct", strain_max),
            ("strain_missing_count", _clean_float(strain_missing_count)),
            ("strain_duplicate_count", _clean_float(strain_duplicate_count)),
            ("strain_monotonic", strain_monotonic),
            ("strain_step_median_pct", strain_step_median),
            ("strain_step_spread", strain_step_spread),
            ("sequence_order_source", str(output.get("sequence_order_source", "") or "").strip() or None),
            ("sequence_direction", sequence_direction),
            ("strain_axis_confidence", strain_axis_confidence),
        ]
    )
    if not strain_axis_evidence:
        return {}

    return {
        "condition_evidence": strain_axis_evidence,
        "feature_evidence": {
            "sequence_evidence": strain_axis_evidence,
            "condition_evidence": strain_axis_evidence,
        },
        "confidence_signals": [
            {
                "name": "strain_axis_confidence",
                "value": strain_axis_confidence,
                "source": "SAXS_strain",
            }
        ],
    }


__all__ = ["_saxs_strain_sequence_evidence"]
