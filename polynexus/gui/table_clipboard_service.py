"""Helpers for copying Qt table selections as tab-separated text."""

from __future__ import annotations

from typing import Any


def extract_table_text_matrix(table: Any, *, start_column: int = 0) -> tuple[list[str], list[list[str]]]:
    if table is None:
        return [], []

    cols = int(table.columnCount() or 0)
    rows = int(table.rowCount() or 0)
    if cols <= start_column or rows <= 0:
        return [], []

    headers: list[str] = []
    for col in range(start_column, cols):
        header_item = table.horizontalHeaderItem(col)
        headers.append(header_item.text() if header_item is not None else "")

    selection = table.selectionModel()
    selected_rows: list[int] = []
    if selection is not None:
        selected_rows = sorted(index.row() for index in selection.selectedRows())
    row_indexes = selected_rows if selected_rows else list(range(rows))

    matrix: list[list[str]] = []
    for row in row_indexes:
        values: list[str] = []
        for col in range(start_column, cols):
            item = table.item(row, col)
            values.append(item.text() if item is not None else "")
        matrix.append(values)

    return headers, matrix


def build_table_tab_separated_text(table: Any, *, start_column: int = 0) -> str:
    headers, matrix = extract_table_text_matrix(table, start_column=start_column)
    if not headers or not matrix:
        return ""

    lines = ["\t".join(headers)]
    for row in matrix:
        lines.append("\t".join(row))

    return "\n".join(lines)


def copy_table_selection_to_clipboard(table: Any, *, start_column: int = 0) -> tuple[bool, int, int]:
    text = build_table_tab_separated_text(table, start_column=start_column)
    if not text:
        return False, 0, 0

    from PySide6.QtWidgets import QApplication

    QApplication.clipboard().setText(text)
    headers, matrix = extract_table_text_matrix(table, start_column=start_column)
    return True, len(matrix), len(headers)
