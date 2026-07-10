"""Helpers for writing GUI table exports."""

from __future__ import annotations

import csv


def write_table_export(
    path,
    headers: list[str],
    matrix: list[list[str]],
    *,
    selected_filter: str = "",
) -> str:
    if not path or not headers or not matrix:
        return ""

    output_path = str(path)
    delimiter = "\t"
    lower_path = output_path.lower()
    if lower_path.endswith(".csv") or "csv" in str(selected_filter).lower():
        delimiter = ","
        if not lower_path.endswith(".csv"):
            output_path = f"{output_path}.csv"
    elif not lower_path.endswith(".tsv"):
        output_path = f"{output_path}.tsv"

    with open(output_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, delimiter=delimiter)
        writer.writerow(headers)
        writer.writerows(matrix)

    return output_path
