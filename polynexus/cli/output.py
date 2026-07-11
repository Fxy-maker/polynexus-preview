"""Formatting helpers for CLI output."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def format_technique_result_lines(technique: str, output: str, parameters: dict[str, Any]) -> list[str]:
    lines = ["", "=" * 50, f"{technique.upper()} Results:"]
    for key, value in parameters.items():
        lines.append(f"  {key}: {value}")
    lines.append(f"Output: {output}")
    return lines


def format_batch_progress_line(row: dict[str, Any]) -> str:
    tag = "OK" if row.get("status") == "OK" else "FAIL"
    return f"  [{tag}] {row.get('file', '')}  {row.get('elapsed', '')}s"


def format_batch_summary_lines(results_summary: Iterable[dict[str, Any]]) -> list[str]:
    rows = list(results_summary)
    ok_rows = [row for row in rows if row.get("status") == "OK"]
    bad_rows = [row for row in rows if row.get("status") != "OK"]

    lines = [
        "",
        f"{'File':<40} {'Technique':<10} {'Status':<12} {'R2':<10} {'Elapsed(s)'}",
        "-" * 90,
    ]
    for row in rows:
        r2 = row.get("r2")
        r2_str = f"{float(r2):.4f}" if isinstance(r2, (int, float)) else "-"
        lines.append(
            f"{str(row.get('file', '')):<40} {str(row.get('technique', '')):<10} "
            f"{str(row.get('status', '')):<12} {r2_str:<10} {row.get('elapsed', '')}"
        )
    lines.extend(
        [
            "-" * 90,
            f"Completed: {len(ok_rows)} succeeded, {len(bad_rows)} failed, {len(rows)} total.",
        ]
    )
    if bad_rows:
        lines.append("")
        lines.append("Failed files:")
        for row in bad_rows:
            lines.append(f"  {row.get('file', '')} -> {row.get('status', '')}")
    return lines

