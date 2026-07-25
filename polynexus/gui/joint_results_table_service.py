"""Presentation adapter for the Joint analysis Workbench.

This module only maps the validated Joint report to the shared immutable table
contract.  Cross-technique calculations and evidence decisions remain in
``polynexus.core.joint``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .i18n import tr_for_language
from .result_table_models import (
    HeroMetric,
    ResultTableSection,
    ResultsTablePresentation,
    TableCell,
    TableColumn,
    normalize_table_scalar,
)


_PRIMARY_FIELDS = (
    ("sample", "JOINT_COL_SAMPLE"),
    ("batch", "JOINT_COL_BATCH"),
    ("condition", "JOINT_COL_CONDITION"),
    ("techniques", "JOINT_COL_TECHNIQUES"),
    ("opportunities", "JOINT_COL_ANALYSIS"),
    ("alerts", "JOINT_COL_ALERTS"),
)

_DIAGNOSTIC_FIELDS = (
    ("severity", "JOINT_DIAG_SEVERITY"),
    ("sample", "JOINT_DIAG_SAMPLE"),
    ("batch", "JOINT_DIAG_BATCH"),
    ("check", "JOINT_DIAG_CHECK"),
    ("message", "JOINT_DIAG_MESSAGE"),
)


def _language_code(language: str) -> str:
    return "zh" if str(language or "").strip().lower().startswith("zh") else "en"


def _display(value: Any, *, language: str) -> str:
    try:
        normalized = normalize_table_scalar(value)
    except TypeError:
        normalized = str(value) if value is not None else None
    if normalized is None or normalized == "":
        return "—"
    return str(normalized)


def _status(value: Any) -> str:
    token = str(value or "").strip().lower()
    if token in {"ok", "passed", "success", "confirmed"}:
        return "reliable"
    if token in {"warn", "warning", "review", "pending"}:
        return "review"
    if token in {"error", "failed", "blocked", "invalid"}:
        return "blocked"
    return "neutral"


def _section(
    rows: tuple[dict[str, Any], ...],
    fields: tuple[tuple[str, str], ...],
    *,
    language: str,
) -> ResultTableSection:
    if not rows:
        return ResultTableSection.empty()
    columns = tuple(
        TableColumn(key=key, label=tr_for_language(label_key, language))
        for key, label_key in fields
    )
    table_rows = []
    for row in rows:
        table_rows.append(
            tuple(
                TableCell(
                    raw=(row.get(key) if isinstance(row.get(key), (str, int, float, bool)) else None),
                    display=_display(row.get(key), language=language),
                    status=_status(row.get(f"{key}_status", row.get("severity"))),
                    provenance=str(row.get(f"{key}_provenance", row.get("source", "")) or ""),
                )
                for key, _label_key in fields
            )
        )
    return ResultTableSection(columns=columns, rows=tuple(table_rows))


def _detail_section(rows: tuple[dict[str, Any], ...], *, language: str) -> ResultTableSection:
    keys: list[str] = []
    for row in rows:
        for key, value in row.items():
            if key.startswith("_") or key in {field[0] for field in _PRIMARY_FIELDS}:
                continue
            try:
                normalize_table_scalar(value)
            except TypeError:
                continue
            if key not in keys:
                keys.append(key)
    if not keys or not rows:
        return ResultTableSection.empty()
    columns = tuple(TableColumn(key=key, label=key) for key in keys)
    return ResultTableSection(
        columns=columns,
        rows=tuple(
            tuple(
                TableCell(
                    raw=(row.get(key) if isinstance(row.get(key), (str, int, float, bool)) else None),
                    display=_display(row.get(key), language=language),
                    provenance=str(row.get(f"{key}_provenance", row.get("source", "")) or ""),
                )
                for key in keys
            )
            for row in rows
        ),
    )


def build_joint_results_presentation(
    report: Mapping[str, Any] | None,
    *,
    language: str = "en",
) -> ResultsTablePresentation:
    """Build the typed Joint Workbench presentation from a report payload."""
    target_language = _language_code(language)
    payload = dict(report) if isinstance(report, Mapping) else {}
    rows = tuple(dict(row) for row in payload.get("rows", ()) if isinstance(row, Mapping))
    validations = tuple(
        dict(row) for row in payload.get("validations", ()) if isinstance(row, Mapping)
    )
    errors = sum(str(row.get("severity", "")).upper() == "ERROR" for row in validations)
    warnings = sum(str(row.get("severity", "")).upper() == "WARN" for row in validations)
    heroes = (
        HeroMetric("joint_rows", "Joint rows", len(rows), str(len(rows))),
        HeroMetric("joint_checks", "Checks", len(validations), str(len(validations))),
        HeroMetric("joint_warnings", "Warnings", warnings, str(warnings), status="review" if warnings else "neutral"),
        HeroMetric("joint_errors", "Errors", errors, str(errors), status="blocked" if errors else "neutral"),
    )
    return ResultsTablePresentation(
        kind="joint",
        primary=_section(rows, _PRIMARY_FIELDS, language=target_language),
        detail=_detail_section(rows, language=target_language),
        diagnostics=_section(validations, _DIAGNOSTIC_FIELDS, language=target_language),
        hero_metrics=heroes if rows or validations else (),
        risk_text=str(payload.get("summary") or ""),
        next_text="Review WARN/ERROR validations before treating cross-technique consistency as confirmed." if warnings or errors else "",
        summary_count=len(rows),
        sortable=len(rows) > 1,
        copy_enabled=bool(rows or validations),
        export_enabled=bool(rows or validations),
    )


__all__ = ["build_joint_results_presentation"]
