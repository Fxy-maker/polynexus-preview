from __future__ import annotations

from typing import Any

from .analysis_evidence_ir_temperature_2d_constraint_interpretation import (
    _ir_temperature_2d_interpretation_constraint_rows,
)
from .analysis_evidence_ir_temperature_2d_constraint_matrix import (
    _ir_temperature_2d_matrix_constraint_rows,
)
from .analysis_evidence_ir_temperature_2d_constraint_sequence import (
    _ir_temperature_2d_sequence_constraint_rows,
)


def _ir_temperature_2d_constraint_rows(ir_2d_metrics: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    rows.extend(_ir_temperature_2d_sequence_constraint_rows(ir_2d_metrics))
    rows.extend(_ir_temperature_2d_matrix_constraint_rows(ir_2d_metrics))
    rows.extend(_ir_temperature_2d_interpretation_constraint_rows(ir_2d_metrics))
    return rows


__all__ = [
    "_ir_temperature_2d_sequence_constraint_rows",
    "_ir_temperature_2d_matrix_constraint_rows",
    "_ir_temperature_2d_interpretation_constraint_rows",
    "_ir_temperature_2d_constraint_rows",
]
