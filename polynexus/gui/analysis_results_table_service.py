"""Pure presentation adapter for DSC, IR, WAXS, and NMR results.

The adapter deliberately does not calculate scientific values.  It only maps
the existing result payload (and optional evidence attached to an
``AnalysisResult``-like object) to the shared immutable table contract used by
the Qt results panel and export layer.
"""

from __future__ import annotations

import json
import logging
import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np

from .analysis_result_table_templates import AnalysisFieldSpec, AnalysisResultTemplate, analysis_template
from .i18n import tr_for_language
from .result_table_models import (
    HeroMetric,
    ResultTableSection,
    ResultsTablePresentation,
    TableCell,
    TableColumn,
    TableScalar,
    format_table_value,
    normalize_table_scalar,
)


logger = logging.getLogger(__name__)
_JSON_MAX_DEPTH = 32
_RELIABLE = {"ok", "usable", "passed", "reliable", "success", "confirmed", "accepted"}
_REVIEW = {
    "warn",
    "warning",
    "review",
    "low_confidence",
    "pending",
    "uncertain",
    "needs_review",
    "calibrated",
}
_BLOCKED = {"error", "failed", "blocked", "diagnostic_only", "invalid", "rejected"}
_NOT_DETECTED = {"", "none", "missing", "not_detected", "unavailable", "no_data"}
_NOT_APPLICABLE = {"not_applicable", "na", "n/a"}
_DIAGNOSTIC_EXACT = {
    "analysis_evidence",
    "baseline_stability",
    "integration_sensitivity",
    "peak_decomposition",
    "thermodynamic_consistency",
    "validation_passed",
    "validation_summary",
    "validation_warnings",
    "quality_flags",
    "quality_flag",
    "status_reason",
    "event_support_reason",
    "fit_diagnostics",
    "peak_rows",
    "peaks",
    "band_assignments",
    "phase_assignment",
    "phase_composition",
    "assignment_coverage",
    "matrix",
    "matrix_shape",
    "map_shape",
    "nan_ratio",
}
_DIAGNOSTIC_PREFIXES = (
    "quality_",
    "validation_",
    "diagnostic_",
    "baseline_",
    "integration_",
    "peak_",
    "band_",
    "assignment_",
    "phase_",
    "event_",
    "support_",
    "fit_",
    "matrix_",
    "map_",
    "transition_",
    "low_confidence_",
)


@dataclass(frozen=True)
class _PayloadRows:
    payload: dict[str, Any]
    rows: tuple[dict[str, Any], ...]


def _is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value == "")


def _language_code(language: str) -> str:
    return "zh" if str(language or "").strip().lower().startswith("zh") else "en"


def _as_scalar(value: Any) -> tuple[bool, TableScalar]:
    try:
        return True, normalize_table_scalar(value)
    except TypeError:
        return False, None


def _field_value(row: Mapping[str, Any], field: AnalysisFieldSpec) -> TableScalar:
    for key in field.source_keys:
        if key not in row:
            continue
        is_scalar, value = _as_scalar(row[key])
        if is_scalar and value not in {None, ""}:
            return value
    return None


def _payload_from_input(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        payload = dict(value)
        evidence = payload.get("analysis_evidence")
        if isinstance(evidence, Mapping):
            for key, item in evidence.items():
                normalized_key = str(key)
                existing = payload.get(normalized_key)
                if normalized_key not in payload or _is_missing(existing):
                    payload[normalized_key] = item
        return payload

    parameters = getattr(value, "parameters", None)
    evidence = getattr(value, "analysis_evidence", None)
    payload = dict(parameters) if isinstance(parameters, Mapping) else {}
    for key in (
        "validation_passed",
        "quality_flags",
        "validation_warnings",
        "validation_summary",
    ):
        if hasattr(value, key):
            payload[key] = getattr(value, key)
    if isinstance(evidence, Mapping):
        payload.setdefault("analysis_evidence", dict(evidence))
        for key, item in evidence.items():
            normalized_key = str(key)
            existing = payload.get(normalized_key)
            if normalized_key not in payload or _is_missing(existing):
                payload[normalized_key] = item
    return payload


def _payload_rows(value: Any) -> _PayloadRows:
    payload = _payload_from_input(value)
    batch_data = payload.get("_batch_data")
    if isinstance(batch_data, list):
        rows = tuple(dict(row) for row in batch_data if isinstance(row, Mapping))
    else:
        rows = (dict(payload),) if payload else ()
    return _PayloadRows(payload, rows)


def _view_rows(payload: Mapping[str, Any], rows: tuple[dict[str, Any], ...]) -> list[dict[str, Any]]:
    if not isinstance(payload.get("_batch_data"), list):
        return [dict(row) for row in rows]
    view = []
    for row in rows:
        item = dict(row)
        item["row_scope"] = "frame"
        view.append(item)
    summary = {
        key: value
        for key, value in payload.items()
        if isinstance(key, str) and not key.startswith("_")
    }
    if summary:
        summary["row_scope"] = "batch_summary"
        view.append(summary)
    return view


def _json_ready(value: Any, *, active: set[int] | None = None, depth: int = 0) -> Any:
    active = active if active is not None else set()
    if isinstance(value, np.generic):
        kind = getattr(value.dtype, "kind", "")
        if kind in {"f", "i", "u"}:
            try:
                scalar = float(value) if kind == "f" else int(value)
            except (TypeError, ValueError, OverflowError):
                return None
            return None if isinstance(scalar, float) and not math.isfinite(scalar) else scalar
        if kind == "c":
            try:
                scalar = complex(value)
            except (TypeError, ValueError, OverflowError):
                return None
            if not math.isfinite(scalar.real) or not math.isfinite(scalar.imag):
                return None
            return str(scalar)
        if kind == "b":
            return bool(value)
        if kind in {"U", "S"}:
            return str(value)
        return _json_ready(value.item(), active=active, depth=depth)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, complex):
        if not math.isfinite(value.real) or not math.isfinite(value.imag):
            return None
        return str(value)
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if not isinstance(value, (Mapping, list, tuple, set, frozenset, np.ndarray)):
        return str(value)
    if depth >= _JSON_MAX_DEPTH:
        return "<max-depth>"
    marker = id(value)
    if marker in active:
        return "<cycle>"
    active.add(marker)
    try:
        if isinstance(value, np.ndarray):
            return _json_ready(value.tolist(), active=active, depth=depth + 1)
        if isinstance(value, Mapping):
            return {
                str(key): _json_ready(item, active=active, depth=depth + 1)
                for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            }
        if isinstance(value, (list, tuple)):
            return [_json_ready(item, active=active, depth=depth + 1) for item in value]
        items = [_json_ready(item, active=active, depth=depth + 1) for item in value]
        return sorted(
            items,
            key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True, allow_nan=False),
        )
    finally:
        active.remove(marker)


def _serialize_json(value: Any) -> str:
    return json.dumps(_json_ready(value), ensure_ascii=False, sort_keys=True, allow_nan=False)


def _status_token(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in _RELIABLE:
        return "reliable"
    if text in _REVIEW:
        return "review"
    if text in _BLOCKED:
        return "blocked"
    return "neutral"


def _status_display(value: Any, *, language: str) -> str:
    text = str(value or "").strip().lower()
    if text in _RELIABLE:
        return tr_for_language("RESULTS_STATUS_RELIABLE", language)
    if text in _REVIEW:
        return tr_for_language("RESULTS_STATUS_REVIEW", language)
    if text in _BLOCKED:
        return tr_for_language("RESULTS_STATUS_BLOCKED", language)
    if text in _NOT_DETECTED:
        return tr_for_language("TABLE_ANALYSIS_NOT_DETECTED", language)
    if text in _NOT_APPLICABLE:
        return tr_for_language("TABLE_ANALYSIS_NOT_APPLICABLE", language)
    return str(value)


def _formatted(
    value: TableScalar,
    *,
    digits: int | None,
    language: str,
    key: str = "",
) -> str:
    if key == "status" or key.endswith("_status"):
        if value in {None, ""}:
            return _status_display(value, language=language)
        return _status_display(value, language=language)
    if isinstance(value, complex) and (
        not math.isfinite(value.real) or not math.isfinite(value.imag)
    ):
        return "不可用" if language == "zh" else "Unavailable"
    return format_table_value(
        value,
        digits=digits,
        missing_text="\N{EM DASH}",
        unavailable_text="不可用" if language == "zh" else "Unavailable",
        true_text=tr_for_language("COMMON_YES", language),
        false_text=tr_for_language("COMMON_NO", language),
    )


def _column(field: AnalysisFieldSpec, *, language: str) -> TableColumn:
    alignment = "right" if field.digits is not None or bool(field.unit) else "left"
    return TableColumn(
        key=field.key,
        label=tr_for_language(field.label_key, language),
        unit=field.unit,
        digits=field.digits,
        alignment=alignment,
    )


def _cell(row: Mapping[str, Any], field: AnalysisFieldSpec, *, language: str) -> TableCell:
    value = _field_value(row, field)
    linked_status = row.get(field.status_key) if field.status_key else row.get("status")
    status_value = linked_status if linked_status not in {None, ""} else value if field.key == "status" else None
    provenance_value = row.get(field.provenance_key) if field.provenance_key else None
    provenance = str(provenance_value).strip() if provenance_value not in {None, ""} else ""
    return TableCell(
        raw=value,
        display=_formatted(value, digits=field.digits, language=language, key=field.key),
        status=_status_token(status_value),
        provenance=provenance,
    )


def _primary(rows: tuple[dict[str, Any], ...], template: AnalysisResultTemplate, *, language: str) -> ResultTableSection:
    if not rows:
        return ResultTableSection.empty()
    columns = tuple(_column(field, language=language) for field in template.primary_fields)
    return ResultTableSection(
        columns=columns,
        rows=tuple(
            tuple(_cell(row, field, language=language) for field in template.primary_fields)
            for row in rows
        ),
    )


def _stable_scalar_keys(rows: list[Mapping[str, Any]]) -> list[str]:
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key, value in row.items():
            if not isinstance(key, str) or key.startswith("_") or key in seen:
                continue
            is_scalar, _ = _as_scalar(value)
            if is_scalar:
                seen.add(key)
                keys.append(key)
    return keys


def _is_diagnostic_key(key: str, template: AnalysisResultTemplate) -> bool:
    return (
        key in _DIAGNOSTIC_EXACT
        or key in template.diagnostic_keys
        or key.startswith(_DIAGNOSTIC_PREFIXES)
        or key.endswith(("_reason", "_diagnostics", "_status"))
    )


def _diagnostic_keys(rows: list[Mapping[str, Any]], template: AnalysisResultTemplate) -> list[str]:
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key, value in row.items():
            if not isinstance(key, str) or key.startswith("_") or key in seen:
                continue
            is_scalar, _ = _as_scalar(value)
            if not is_scalar or _is_diagnostic_key(key, template):
                seen.add(key)
                keys.append(key)
    return keys


def _numeric_alignment(rows: list[Mapping[str, Any]], key: str) -> str:
    for row in rows:
        if key not in row:
            continue
        is_scalar, value = _as_scalar(row[key])
        if is_scalar and isinstance(value, (int, float, complex)) and not isinstance(value, bool):
            return "right"
    return "left"


def _dynamic_section(
    rows: list[Mapping[str, Any]],
    keys: list[str],
    *,
    language: str,
    serialize_nested: bool = False,
) -> ResultTableSection:
    if not rows or not keys:
        return ResultTableSection.empty()
    columns = tuple(
        TableColumn(key=key, label=key, alignment=_numeric_alignment(rows, key))
        for key in keys
    )
    table_rows = []
    for row in rows:
        cells = []
        for key in keys:
            original = row.get(key)
            is_scalar, value = _as_scalar(original)
            if not is_scalar:
                value = _serialize_json(original) if serialize_nested and key in row else None
            linked_status = row.get(f"{key}_status", row.get("status"))
            linked_provenance = row.get(
                f"{key}_provenance",
                row.get(f"{key}_source", ""),
            )
            provenance = (
                str(linked_provenance).strip()
                if linked_provenance not in {None, ""}
                else ""
            )
            cells.append(
                TableCell(
                    raw=value,
                    display=_formatted(value, digits=None, language=language, key=key),
                    status=_status_token(linked_status if linked_status not in {None, ""} else value),
                    provenance=provenance,
                )
            )
        table_rows.append(tuple(cells))
    return ResultTableSection(columns=columns, rows=tuple(table_rows))


def _is_hero_value(value: TableScalar) -> bool:
    if value is None or value == "":
        return False
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, complex):
        return math.isfinite(value.real) and math.isfinite(value.imag)
    return True


def _heroes(
    payload: Mapping[str, Any],
    rows: tuple[dict[str, Any], ...],
    template: AnalysisResultTemplate,
    *,
    language: str,
) -> tuple[HeroMetric, ...]:
    if not rows:
        return ()
    metrics: list[HeroMetric] = []
    for field in template.hero_fields:
        value: TableScalar = None
        selected: Mapping[str, Any] | None = None
        for candidate in (payload, rows[0]):
            candidate_value = _field_value(candidate, field)
            if _is_hero_value(candidate_value):
                value = candidate_value
                selected = candidate
                break
        if selected is None:
            continue
        status_value = selected.get(field.status_key) if field.status_key else selected.get("status")
        provenance_value = selected.get(field.provenance_key) if field.provenance_key else None
        provenance = str(provenance_value).strip() if provenance_value not in {None, ""} else ""
        metrics.append(
            HeroMetric(
                key=field.key,
                label=tr_for_language(field.label_key, language),
                raw=value,
                display=_formatted(value, digits=field.digits, language=language),
                unit=field.unit,
                status=_status_token(status_value),
                provenance=provenance,
            )
        )
    return tuple(metrics)


def build_analysis_results_presentation(
    params: Any,
    *,
    technique: str,
    submodule: str = "",
    language: str = "en",
) -> ResultsTablePresentation | None:
    """Build a localized table presentation, or ``None`` for unsupported techniques."""
    template = analysis_template(technique, submodule)
    if template is None:
        return None
    target_language = _language_code(language)
    payload_rows = _payload_rows(params)
    rows = payload_rows.rows
    view_rows = _view_rows(payload_rows.payload, rows)
    return ResultsTablePresentation(
        kind=template.key,
        primary=_primary(rows, template, language=target_language),
        detail=_dynamic_section(
            view_rows,
            _stable_scalar_keys(view_rows),
            language=target_language,
        ),
        diagnostics=_dynamic_section(
            view_rows,
            _diagnostic_keys(view_rows, template),
            language=target_language,
            serialize_nested=True,
        ),
        hero_metrics=_heroes(payload_rows.payload, rows, template, language=target_language),
        summary_count=len(rows),
        sortable=len(rows) > 1,
        copy_enabled=bool(rows),
        export_enabled=bool(rows),
    )


def try_build_analysis_results_presentation(
    params: Any,
    *,
    technique: str,
    submodule: str = "",
    language: str = "en",
) -> ResultsTablePresentation | None:
    """Exception-safe adapter entry point for the generic results fallback."""
    try:
        return build_analysis_results_presentation(
            params,
            technique=technique,
            submodule=submodule,
            language=language,
        )
    except Exception:
        logger.warning(
            "Analysis results presentation failed; using generic results table.",
            exc_info=True,
        )
        return None
