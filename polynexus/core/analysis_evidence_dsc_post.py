from __future__ import annotations

from typing import Any

from .analysis_evidence_dsc_post_constraint_context import _dsc_constraint_context
from .analysis_evidence_dsc_post_constraint_event import _evaluate_dsc_event_constraint
from .analysis_evidence_dsc_post_constraint_quality import _evaluate_dsc_quality_constraint
from .analysis_evidence_dsc_post_guidance import _dsc_actionable_lines, _dsc_summary_details


_DSC_CONSTRAINT_NAMES = {
    "baseline_sensitive_result",
    "Tg_without_DCp_step",
    "Tg_outside_supported_window",
    "melting_without_supported_event",
    "cold_crystallization_conflicts_with_melting",
    "event_polarity_conflict",
    "peak_components_too_sparse",
    "peak_width_nonphysical",
    "multi_scan_inconsistent",
    "crystallinity_without_event_support",
    "dsc_baseline_sensitive_xc",
    "quality_score_without_event_support",
}


def _evaluate_dsc_constraint(
    item_name: str,
    output: dict[str, Any],
    residual_key: str,
    validation: dict[str, Any] | None = None,
) -> tuple[bool, Any]:
    context = _dsc_constraint_context(output, validation)
    quality_result = _evaluate_dsc_quality_constraint(item_name, output, residual_key, context)
    if quality_result is not None:
        return quality_result
    event_result = _evaluate_dsc_event_constraint(item_name, output, context)
    if event_result is not None:
        return event_result
    return False, None


__all__ = [
    "_dsc_actionable_lines",
    "_dsc_summary_details",
    "_DSC_CONSTRAINT_NAMES",
    "_dsc_constraint_context",
    "_evaluate_dsc_quality_constraint",
    "_evaluate_dsc_event_constraint",
    "_evaluate_dsc_constraint",
]
