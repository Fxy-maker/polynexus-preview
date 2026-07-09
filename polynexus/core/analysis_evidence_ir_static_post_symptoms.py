from __future__ import annotations

from typing import Any

from .analysis_evidence_ir_static_post_symptom_bridge import _ir_symptom_bridge_lines
from .analysis_evidence_ir_static_post_symptom_residual import _ir_residual_constraint_symptoms
from .analysis_evidence_ir_static_post_symptom_support import _ir_support_constraint_symptoms


def _ir_symptoms_from_constraints(
    constraints: list[dict[str, Any]],
    output: dict[str, Any],
    residual: dict[str, Any],
    validation: dict[str, Any],
) -> list[dict[str, Any]]:
    from .analysis_evidence_ir import _ir_band_support_metrics

    triggered = {
        str(item.get("name", "") or "").strip(): item
        for item in constraints
        if isinstance(item, dict) and item.get("triggered")
    }
    support = _ir_band_support_metrics(output, validation)
    residual_type = str(output.get("residual_type", "") or "").strip()
    symptom_list: list[dict[str, Any]] = []
    symptom_list.extend(_ir_support_constraint_symptoms(triggered, support))
    symptom_list.extend(_ir_residual_constraint_symptoms(triggered, residual, residual_type))
    return symptom_list


__all__ = [
    "_ir_symptom_bridge_lines",
    "_ir_support_constraint_symptoms",
    "_ir_residual_constraint_symptoms",
    "_ir_symptoms_from_constraints",
]
