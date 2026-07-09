from __future__ import annotations

from typing import Any

from .analysis_evidence_ir_temperature_2d_post_symptom_bridge import (
    _ir_temperature_2d_symptom_bridge_lines,
)
from .analysis_evidence_ir_temperature_2d_post_symptom_interpretation import (
    _ir_temperature_2d_interpretation_constraint_symptoms,
)
from .analysis_evidence_ir_temperature_2d_post_symptom_sequence import (
    _ir_temperature_2d_sequence_constraint_symptoms,
)
from .analysis_evidence_ir_temperature_2d_post_symptom_transition import (
    _ir_temperature_2d_transition_constraint_symptoms,
)


def _ir_temperature_2d_symptoms_from_constraints(
    constraints: list[dict[str, Any]],
    metrics: dict[str, Any],
) -> list[dict[str, Any]]:
    triggered = {
        str(item.get("name", "") or "").strip(): item
        for item in constraints
        if isinstance(item, dict) and item.get("triggered")
    }
    symptom_list: list[dict[str, Any]] = []
    symptom_list.extend(_ir_temperature_2d_sequence_constraint_symptoms(triggered, metrics))
    symptom_list.extend(_ir_temperature_2d_interpretation_constraint_symptoms(triggered, metrics))
    symptom_list.extend(_ir_temperature_2d_transition_constraint_symptoms(triggered, metrics))
    return symptom_list


__all__ = [
    "_ir_temperature_2d_symptom_bridge_lines",
    "_ir_temperature_2d_sequence_constraint_symptoms",
    "_ir_temperature_2d_interpretation_constraint_symptoms",
    "_ir_temperature_2d_transition_constraint_symptoms",
    "_ir_temperature_2d_symptoms_from_constraints",
]
