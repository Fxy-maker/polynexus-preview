"""Pure helpers for building results-table models for the GUI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .i18n import tr


@dataclass(frozen=True)
class ResultsTableModel:
    kind: str
    columns: list[str]
    display_rows: list[list[str]]
    stored_rows: list[list[Any]]
    summary_count: int = 0
    export_enabled: bool = False
    copy_enabled: bool = False
    sortable: bool = False


def _format_display_value(value, *, digits: int) -> str:
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def build_results_table_model(
    params,
    *,
    ordered_columns_fn: Callable[[list[str]], list[str]],
    flatten_params_fn: Callable[[Any], list[tuple[str, Any]]],
) -> ResultsTableModel:
    if isinstance(params, dict) and len(params) > 1 and all(isinstance(v, dict) for v in params.values()) and not any(
        str(k).startswith("_") for k in params
    ):
        sample_labels = list(params.keys())
        all_keys: list[str] = []
        for values in params.values():
            for key in values:
                if key not in all_keys:
                    all_keys.append(key)
        columns = ordered_columns_fn(["sample", *all_keys])
        display_rows: list[list[str]] = []
        stored_rows: list[list[Any]] = []
        for label in sample_labels:
            values = params[label]
            display_row = [str(label)]
            stored_row = [label]
            for key in columns[1:]:
                value = values.get(key, "")
                stored_row.append(value)
                display_row.append(_format_display_value(value, digits=2))
            display_rows.append(display_row)
            stored_rows.append(stored_row)
        return ResultsTableModel(
            kind="multi_sample",
            columns=columns,
            display_rows=display_rows,
            stored_rows=stored_rows,
            summary_count=len(sample_labels),
            export_enabled=True,
            copy_enabled=True,
            sortable=True,
        )

    batch_frames = params.get("batch_frames", 0) if isinstance(params, dict) else 0
    if isinstance(params, dict) and batch_frames > 1 and "_batch_data" in params:
        batch_data = params["_batch_data"] if isinstance(params.get("_batch_data"), list) else []
        all_keys: list[str] = []
        for row in batch_data:
            if not isinstance(row, dict):
                continue
            for key in row:
                if key not in all_keys:
                    all_keys.append(key)
        columns = ordered_columns_fn(all_keys if all_keys else ["file", "L_nm", "lc_nm", "Xc"])
        display_rows = []
        stored_rows = []
        for row in batch_data:
            row = row if isinstance(row, dict) else {}
            display_row = []
            stored_row = []
            for key in columns:
                value = row.get(key, "")
                stored_row.append(value)
                display_row.append(_format_display_value(value, digits=3))
            display_rows.append(display_row)
            stored_rows.append(stored_row)
        return ResultsTableModel(
            kind="batch",
            columns=columns,
            display_rows=display_rows,
            stored_rows=stored_rows,
            summary_count=len(batch_data) or int(batch_frames or 0),
            export_enabled=True,
            copy_enabled=True,
            sortable=True,
        )

    items = flatten_params_fn(params)
    columns = [tr("RESULTS_PARAM"), tr("RESULTS_VALUE")]
    display_rows = [[str(key), _format_display_value(value, digits=4)] for key, value in items]
    stored_rows = [[key, value] for key, value in items]
    has_items = bool(items)
    return ResultsTableModel(
        kind="single",
        columns=columns,
        display_rows=display_rows,
        stored_rows=stored_rows,
        summary_count=len(items),
        export_enabled=has_items,
        copy_enabled=has_items,
        sortable=False,
    )


def build_batch_results_table_model(
    all_results,
    *,
    ordered_columns_fn: Callable[[list[str]], list[str]],
) -> ResultsTableModel:
    all_keys: list[str] = []
    flat_rows: list[dict[str, Any]] = []

    for row in all_results if isinstance(all_results, list) else []:
        if not isinstance(row, dict):
            continue
        flat: dict[str, Any] = {}
        file_name = row.get("file", "")
        flat["file"] = file_name
        params = row.get("params", {})
        if isinstance(params, dict):
            for key, val in params.items():
                if isinstance(val, dict):
                    flat.update(val)
                else:
                    flat[key] = val
        for key in flat:
            if key not in all_keys:
                all_keys.append(key)
        flat_rows.append(flat)

    columns = ordered_columns_fn(all_keys)
    display_rows: list[list[str]] = []
    stored_rows: list[list[Any]] = []
    for flat in flat_rows:
        display_row: list[str] = []
        stored_row: list[Any] = []
        for key in columns:
            value = flat.get(key, "")
            stored_row.append(value)
            display_row.append(_format_display_value(value, digits=4))
        display_rows.append(display_row)
        stored_rows.append(stored_row)

    has_rows = bool(flat_rows)
    return ResultsTableModel(
        kind="batch",
        columns=columns,
        display_rows=display_rows,
        stored_rows=stored_rows,
        summary_count=len(flat_rows),
        export_enabled=has_rows,
        copy_enabled=has_rows,
        sortable=has_rows,
    )
