from __future__ import annotations

from typing import Any

from .analysis_evidence_utils import _clean_float


def _condition_values(
    output: dict[str, Any],
    batch_rows: list[dict[str, Any]],
    label: str,
) -> list[float]:
    values: list[float] = []
    if batch_rows:
        for row in batch_rows:
            if not isinstance(row, dict):
                continue
            value = _clean_float(row.get("condition_value"))
            if value is None and label == "temperature":
                value = _clean_float(row.get("temperature_C"))
            if value is None and label == "strain":
                value = _clean_float(row.get("strain_pct"))
            if value is not None:
                values.append(value)
        return values

    for key in ("condition_value", "temperature_C", "strain_pct"):
        value = _clean_float(output.get(key))
        if value is not None:
            values.append(value)
            break
    return values


__all__ = ["_condition_values"]
