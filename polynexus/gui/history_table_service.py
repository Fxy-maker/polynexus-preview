"""Pure helpers for building history-table row data for the GUI."""

from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from .analysis_history_service import (
    extract_result_r2,
    format_history_timestamp,
    format_r2_value,
)
from .table_export_service import write_table_export


@dataclass(frozen=True)
class HistoryTableRow:
    values: list[str]
    tooltips: list[str]


def build_history_table_rows(
    rows: Iterable[dict[str, Any]],
    *,
    metrics_tooltip_fn: Callable[[dict[str, Any]], str],
    technique_text_fn: Callable[[str], str],
    submodule_text_fn: Callable[[str], str],
    status_text_fn: Callable[[dict[str, Any]], str],
    validation_summary_fn: Callable[[dict[str, Any]], str],
    confirmation_label_fn: Callable[[dict[str, Any]], str],
    has_source_fn: Callable[[dict[str, Any]], bool],
) -> list[HistoryTableRow]:
    table_rows: list[HistoryTableRow] = []
    for run in rows if isinstance(rows, Iterable) else []:
        if not isinstance(run, dict):
            continue
        submodule_id = str(run.get("submodule") or "")
        technique_id = str(run.get("technique") or "")
        status_value = str(run.get("status") or "")
        metrics_tooltip = str(metrics_tooltip_fn(run) or "")
        values = [
            format_history_timestamp(run.get("created_at")),
            technique_text_fn(technique_id),
            submodule_text_fn(submodule_id),
            format_r2_value(extract_result_r2(run.get("results_summary") if isinstance(run.get("results_summary"), dict) else {})),
            status_text_fn(run),
            validation_summary_fn(run),
            confirmation_label_fn(run),
        ]
        tooltips = list(values)
        if metrics_tooltip:
            tooltips[0] = metrics_tooltip
            tooltips[3] = metrics_tooltip
        if technique_id:
            tooltips[1] = technique_id
        if submodule_id:
            tooltips[2] = submodule_id
        if not has_source_fn(run):
            status_bits = [values[4]]
        else:
            status_bits = [status_value] if status_value else []
        if technique_id == "saxs" and metrics_tooltip:
            status_bits.append(metrics_tooltip)
        tooltips[4] = " | ".join(bit for bit in status_bits if bit)
        tooltips[5] = values[5]
        tooltips[6] = values[6]
        table_rows.append(HistoryTableRow(values=values, tooltips=tooltips))
    return table_rows


def write_history_export_table(
    path,
    headers: list[str],
    matrix: list[list[str]],
    *,
    selected_filter: str = "",
) -> str:
    return write_table_export(
        path,
        headers,
        matrix,
        selected_filter=selected_filter,
    )
