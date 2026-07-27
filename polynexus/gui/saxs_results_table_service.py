"""Build immutable, localized table presentations from SAXS result payloads."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np

from .analysis_history_service import saxs_lc_status_text
from .i18n import tr_for_language
from .result_table_models import (
    HeroMetric,
    ResultsTablePresentation,
    ResultTableSection,
    TableCell,
    TableColumn,
    TableScalar,
    format_table_value,
    normalize_table_scalar,
)
from .result_table_templates import ResultFieldSpec, ResultTableTemplate, saxs_template


_RELIABLE_STATUSES = {"usable", "ok", "passed"}
_REVIEW_STATUSES = {"low_confidence", "near_onset", "calibrated", "qstar_calibrated"}
_BLOCKED_STATUSES = {"diagnostic_only", "post_end", "failed", "error"}

_EXACT_DIAGNOSTIC_KEYS = {
    "Q_star_valid",
    "calibrated_fallback_active",
    "condition_confidence",
    "condition_continuity_score",
    "condition_missing_frames",
    "condition_source",
    "condition_source_key",
    "condition_source_text",
    "dominant_phase",
    "effective_q_min",
    "frame_low_conf_count",
    "lc_confidence",
    "lc_method",
    "lc_reliability_reason",
    "lc_reliability_status",
    "low_q_void_dominant",
    "melting_window_reason",
    "melting_window_status",
    "paper_conclusion_candidate",
    "paper_figure_candidate",
    "q_max",
    "q_min",
    "q_peak_snr",
    "quality_flag",
    "row_scope",
    "strain_monotonic",
    "strain_reliability_reason",
    "strain_reliability_status",
    "strain_void_lamellar_conflict",
    "validation_summary",
    "void_dominant_frame_count",
}
_DIAGNOSTIC_PREFIXES = (
    "beam_stop_",
    "beamstop_",
    "calibrated_",
    "calibration_",
    "condition_axis_",
    "effective_q_",
    "fallback_",
    "lc_candidate_",
    "lc_path_",
    "mask_",
    "melting_window_",
    "low_q_",
    "phase_",
    "q_mask_",
    "recommended_q_",
    "strain_axis_",
    "strain_duplicate_",
    "strain_missing_",
    "strain_quality_",
    "strain_void_",
)
_KNOWN_LC_METHODS = {"raw", "calibrated", "qstar_calibrated"}
_JSON_MAX_DEPTH = 32


@dataclass(frozen=True)
class _ResolvedLc:
    value: TableScalar
    source: TableScalar
    provenance: str
    ambiguous: bool = False
    tooltip: str = ""


def _language_code(language: str) -> str:
    return "zh" if str(language or "").strip().lower().startswith("zh") else "en"


def _copied_rows(params: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = dict(params) if isinstance(params, dict) else {}
    batch_data = payload.get("_batch_data")
    if isinstance(batch_data, list):
        return payload, [dict(row) for row in batch_data if isinstance(row, dict)]
    return payload, [dict(payload)] if payload else []


def _as_scalar(value: Any) -> tuple[bool, TableScalar]:
    try:
        return True, normalize_table_scalar(value)
    except TypeError:
        return False, None


def _field_value(row: Mapping[str, Any], field: ResultFieldSpec) -> TableScalar:
    for source_key in field.source_keys:
        if source_key in row:
            is_scalar, value = _as_scalar(row[source_key])
            if is_scalar and value not in {None, ""}:
                return value
    return None


def _batch_view_rows(
    payload: dict[str, Any],
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not isinstance(payload.get("_batch_data"), list):
        return rows
    summary_row = {
        key: value
        for key, value in payload.items()
        if isinstance(key, str) and not key.startswith("_")
    }
    if not summary_row:
        return rows
    view_rows: list[dict[str, Any]] = []
    for row in rows:
        view_row = dict(row)
        view_row["row_scope"] = "frame"
        view_rows.append(view_row)
    summary_row["row_scope"] = "batch_summary"
    view_rows.append(summary_row)
    return view_rows


def _linked_value(row: Mapping[str, Any], key: str) -> TableScalar:
    if not key or key not in row:
        return None
    is_scalar, value = _as_scalar(row[key])
    return value if is_scalar else None


def _scalar_candidate(row: Mapping[str, Any], key: str) -> tuple[bool, TableScalar]:
    if key not in row:
        return False, None
    is_scalar, value = _as_scalar(row[key])
    return is_scalar and value not in {None, ""}, value


def _resolve_lc(row: Mapping[str, Any], *, language: str) -> _ResolvedLc:
    declared = _linked_value(row, "lc_method")
    declared_source = str(declared).strip() if declared not in {None, ""} else ""
    method = declared_source.lower()
    canonical_valid, canonical = _scalar_candidate(row, "lc_nm")
    if canonical_valid:
        if not declared_source:
            return _ResolvedLc(
                canonical,
                None,
                "",
                ambiguous=True,
                tooltip=tr_for_language(
                    "TABLE_TOOLTIP_LC_METHOD_MISSING",
                    language,
                    "lc_nm",
                ),
            )
        if method not in _KNOWN_LC_METHODS:
            return _ResolvedLc(
                canonical,
                declared_source,
                declared_source,
                ambiguous=True,
                tooltip=tr_for_language(
                    "TABLE_TOOLTIP_LC_METHOD_UNKNOWN",
                    language,
                    declared_source,
                    "lc_nm",
                ),
            )
        return _ResolvedLc(canonical, declared_source, declared_source)

    raw_valid, raw_value = _scalar_candidate(row, "lc_nm_raw")
    calibrated_valid, calibrated_value = _scalar_candidate(row, "lc_nm_calibrated")
    if method == "raw" and raw_valid:
        return _ResolvedLc(raw_value, "raw", "raw")
    if method in {"calibrated", "qstar_calibrated"} and calibrated_valid:
        return _ResolvedLc(calibrated_value, declared_source, declared_source)

    if method == "raw" and calibrated_valid:
        return _ResolvedLc(
            calibrated_value,
            "calibrated",
            "calibrated",
            ambiguous=True,
            tooltip=tr_for_language(
                "TABLE_TOOLTIP_LC_METHOD_CONTRADICTS",
                language,
                "raw",
                "lc_nm_calibrated",
            ),
        )
    if method in {"calibrated", "qstar_calibrated"} and raw_valid:
        return _ResolvedLc(
            raw_value,
            "raw",
            "raw",
            ambiguous=True,
            tooltip=tr_for_language(
                "TABLE_TOOLTIP_LC_METHOD_CONTRADICTS",
                language,
                declared_source,
                "lc_nm_raw",
            ),
        )

    selected_value = raw_value if raw_valid else calibrated_value
    selected_source = "raw" if raw_valid else ("calibrated" if calibrated_valid else None)
    selected_key = "lc_nm_raw" if raw_valid else "lc_nm_calibrated"
    if selected_source is None:
        return _ResolvedLc(
            None,
            None,
            "",
            ambiguous=True,
            tooltip=tr_for_language("TABLE_TOOLTIP_LC_VALUE_MISSING", language),
        )
    if not declared_source:
        tooltip = tr_for_language(
            "TABLE_TOOLTIP_LC_METHOD_MISSING",
            language,
            selected_key,
        )
    else:
        tooltip = tr_for_language(
            "TABLE_TOOLTIP_LC_METHOD_UNKNOWN",
            language,
            declared_source,
            selected_key,
        )
    return _ResolvedLc(
        selected_value,
        selected_source,
        str(selected_source),
        ambiguous=True,
        tooltip=tooltip,
    )


def _status_token(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in _RELIABLE_STATUSES:
        return "reliable"
    if text in _REVIEW_STATUSES:
        return "review"
    if text in _BLOCKED_STATUSES:
        return "blocked"
    return "neutral"


def _status_with_source_review(status: str, *, ambiguous: bool) -> str:
    if not ambiguous or status == "blocked":
        return status
    return "review"


def _source_text(value: Any, *, language: str) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    if language == "zh":
        mapping = {
            "raw": "\u539f\u59cb",
            "calibrated": "\u5df2\u6821\u51c6",
            "qstar_calibrated": "Q* \u6821\u51c6",
            "unknown": "\u672a\u77e5",
        }
    else:
        mapping = {
            "raw": "raw",
            "calibrated": "calibrated",
            "qstar_calibrated": "Q* calibrated",
            "unknown": "unknown",
        }
    return mapping.get(text, text.replace("_", "-"))


def _melting_window_text(value: Any, *, language: str) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    if language == "zh":
        mapping = {
            "outside_window": "\u7a97\u53e3\u5916",
            "near_onset": "\u63a5\u8fd1\u8d77\u70b9",
            "within_window": "\u7a97\u53e3\u5185",
            "post_end": "\u8d85\u8fc7\u7ec8\u70b9",
            "undetermined": "\u672a\u786e\u5b9a",
        }
    else:
        mapping = {
            "outside_window": "outside window",
            "near_onset": "near onset",
            "within_window": "within window",
            "post_end": "past end",
            "undetermined": "undetermined",
        }
    return mapping.get(text, text.replace("_", "-"))


def _localized_display_value(key: str, value: TableScalar, *, language: str) -> TableScalar:
    if value is None or value == "":
        return value
    if key == "lc_method":
        return _source_text(value, language=language)
    if key.endswith(("lc_reliability_status", "strain_reliability_status")):
        return saxs_lc_status_text(value, language=language)
    if "melting_window_status" in key:
        return _melting_window_text(value, language=language)
    return value


def _formatted(
    key: str,
    value: TableScalar,
    *,
    digits: int | None,
    language: str,
) -> str:
    display_value = _localized_display_value(key, value, language=language)
    if isinstance(display_value, complex) and (
        not math.isfinite(display_value.real) or not math.isfinite(display_value.imag)
    ):
        display_value = float("nan")
    return format_table_value(
        display_value,
        digits=digits,
        missing_text="\N{EM DASH}",
        unavailable_text="\u4e0d\u53ef\u7528" if language == "zh" else "Unavailable",
        true_text=tr_for_language("COMMON_YES", language),
        false_text=tr_for_language("COMMON_NO", language),
    )


def _series_metric_review_text(
    payload: Mapping[str, Any],
    *,
    language: str,
) -> tuple[str, str]:
    """Format existing series evidence for the Workbench review channels."""

    evidence = payload.get("metric_evidence") if isinstance(payload, Mapping) else None
    if not isinstance(evidence, Mapping):
        return "", ""

    zh = language == "zh"
    level_labels = {
        "Quantitative": "定量" if zh else "Quantitative",
        "Trend": "趋势" if zh else "Trend",
        "Diagnostic": "诊断" if zh else "Diagnostic",
        "Unusable": "不可用" if zh else "Unusable",
    }
    metric_lines: list[str] = []
    downgraded = False

    def _count(summary: Mapping[str, Any], key: str) -> int:
        try:
            return max(0, int(summary.get(key, 0) or 0))
        except (TypeError, ValueError):
            return 0

    for raw_name, summary in sorted(evidence.items(), key=lambda item: str(item[0])):
        if not isinstance(summary, Mapping):
            continue
        name = str(raw_name)
        metric_name = str(summary.get("metric_name") or name).strip() or name
        if name.strip().lower() == "guinier" or metric_name.lower() == "guinier":
            metric_name = "Rg"
        level = str(summary.get("level") or "Unusable").strip() or "Unusable"
        evidence_frames = _count(summary, "evidence_frame_count")
        frame_count = _count(summary, "frame_count")
        coverage = summary.get("coverage_fraction")
        coverage_text = f"{evidence_frames}/{frame_count}"
        try:
            coverage_number = float(coverage)
        except (TypeError, ValueError):
            coverage_number = None
        if coverage_number is not None and math.isfinite(coverage_number):
            coverage_text += f" ({coverage_number * 100:.0f}%)"

        parts = [
            f"{metric_name}: {level_labels.get(level, level)}",
            f"{'覆盖' if zh else 'coverage'}={coverage_text}",
        ]
        diagnostic_count = _count(summary, "diagnostic_frame_count")
        unusable_count = _count(summary, "unusable_frame_count")
        missing_count = _count(summary, "missing_frame_count")
        if diagnostic_count:
            parts.append(f"{'诊断帧' if zh else 'diagnostic frames'}={diagnostic_count}")
        if unusable_count:
            parts.append(f"{'不可用帧' if zh else 'unusable frames'}={unusable_count}")
        if missing_count:
            parts.append(f"{'缺帧' if zh else 'missing frames'}={missing_count}")

        reason_codes = summary.get("reason_codes")
        if isinstance(reason_codes, str):
            reason_codes = (reason_codes,)
        elif not isinstance(reason_codes, (list, tuple)):
            reason_codes = ()
        reasons = [str(reason).strip() for reason in reason_codes if str(reason).strip()]
        if level in {"Diagnostic", "Unusable"} or diagnostic_count or unusable_count or missing_count:
            downgraded = True
            if reasons:
                parts.append(f"{'原因' if zh else 'reasons'}=" + ",".join(reasons[:3]))
        metric_lines.append("; ".join(parts))

    if not metric_lines:
        return "", ""
    detail = " | ".join(metric_lines)
    static_batch = str(payload.get("metric_evidence_scope") or "").strip().lower() == "static_batch"
    if static_batch:
        scope_label = "Batch quality" if not zh else "\u6279\u6b21\u8d28\u91cf"
        detail = f"{scope_label}: {detail}"
    if downgraded:
        risk = tr_for_language("RESULTS_REVIEW_RISK", language, detail)
        if static_batch:
            next_text = tr_for_language(
                "RESULTS_REVIEW_NEXT",
                language,
                "在使用静态批次质量摘要前，先复核缺失帧和诊断帧"
                if zh
                else "Review missing and diagnostic frames before using the static batch quality summary",
            )
            return risk, next_text
        next_text = tr_for_language(
            "RESULTS_REVIEW_NEXT",
            language,
            "先复核缺帧和诊断帧" if zh else "Review missing and diagnostic frames before using the series trend",
        )
        return risk, next_text
    return "", tr_for_language("RESULTS_REVIEW_NEXT", language, detail)


def _field_column(field: ResultFieldSpec, *, language: str) -> TableColumn:
    alignment = "right" if field.digits is not None or bool(field.unit) else "left"
    return TableColumn(
        key=field.key,
        label=tr_for_language(field.label_key, language),
        unit=field.unit,
        digits=field.digits,
        alignment=alignment,
    )


def _field_cell(row: Mapping[str, Any], field: ResultFieldSpec, *, language: str) -> TableCell:
    if field.key in {"lc_nm", "lc_method"}:
        resolved = _resolve_lc(row, language=language)
        if field.key == "lc_nm":
            value = resolved.value
            status = _status_with_source_review(
                _status_token(_linked_value(row, field.status_key)),
                ambiguous=resolved.ambiguous,
            )
        else:
            value = resolved.source
            reliability_status = _status_token(
                _linked_value(row, "lc_reliability_status")
            )
            source_status = _status_token(value)
            if value is None or reliability_status == "blocked":
                source_status = reliability_status
            status = _status_with_source_review(
                source_status,
                ambiguous=resolved.ambiguous,
            )
        return TableCell(
            raw=value,
            display=_formatted(field.key, value, digits=field.digits, language=language),
            status=status,
            provenance=resolved.provenance,
            tooltip=resolved.tooltip,
        )
    value = _field_value(row, field)
    linked_status = _linked_value(row, field.status_key)
    cell_status_value = linked_status if field.status_key else value
    provenance_value = _linked_value(row, field.provenance_key)
    provenance = str(provenance_value).strip() if provenance_value not in {None, ""} else ""
    return TableCell(
        raw=value,
        display=_formatted(field.key, value, digits=field.digits, language=language),
        status=_status_token(cell_status_value),
        provenance=provenance,
    )


def _primary_section(
    rows: list[dict[str, Any]],
    template: ResultTableTemplate,
    *,
    language: str,
) -> ResultTableSection:
    if not rows:
        return ResultTableSection.empty()
    columns = tuple(
        _field_column(field, language=language)
        for field in template.primary_fields
    )
    table_rows = tuple(
        tuple(_field_cell(row, field, language=language) for field in template.primary_fields)
        for row in rows
    )
    return ResultTableSection(columns=columns, rows=table_rows)


def _stable_scalar_keys(rows: list[dict[str, Any]]) -> list[str]:
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


def _numeric_alignment(rows: list[dict[str, Any]], key: str) -> str:
    for row in rows:
        if key not in row:
            continue
        is_scalar, value = _as_scalar(row[key])
        if is_scalar and isinstance(value, (int, float, complex)) and not isinstance(value, bool):
            return "right"
    return "left"


def _dynamic_section(
    rows: list[dict[str, Any]],
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
    table_rows: list[tuple[TableCell, ...]] = []
    for row in rows:
        cells: list[TableCell] = []
        for key in keys:
            original = row.get(key)
            is_scalar, value = _as_scalar(original)
            if not is_scalar:
                value = _serialize_json(original) if serialize_nested and key in row else None
            cells.append(
                TableCell(
                    raw=value,
                    display=_formatted(key, value, digits=None, language=language),
                    status=_status_token(value),
                )
            )
        table_rows.append(tuple(cells))
    return ResultTableSection(columns=columns, rows=tuple(table_rows))


def _json_ready(
    value: Any,
    *,
    active: set[int] | None = None,
    depth: int = 0,
) -> Any:
    active = active if active is not None else set()
    if isinstance(value, np.generic):
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
    is_container = isinstance(
        value,
        (Mapping, list, tuple, set, frozenset, np.ndarray),
    )
    if not is_container:
        return str(value)
    if depth >= _JSON_MAX_DEPTH:
        return "<max-depth>"
    identity = id(value)
    if identity in active:
        return "<cycle>"
    active.add(identity)
    try:
        if isinstance(value, np.ndarray):
            return _json_ready(value.tolist(), active=active, depth=depth + 1)
        if isinstance(value, Mapping):
            return {
                str(key): _json_ready(item, active=active, depth=depth + 1)
                for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            }
        if isinstance(value, (list, tuple)):
            return [
                _json_ready(item, active=active, depth=depth + 1)
                for item in value
            ]
        items = [
            _json_ready(item, active=active, depth=depth + 1)
            for item in value
        ]
        return sorted(
            items,
            key=lambda item: json.dumps(
                item,
                ensure_ascii=False,
                sort_keys=True,
                allow_nan=False,
            ),
        )
    finally:
        active.remove(identity)


def _serialize_json(value: Any) -> str:
    return json.dumps(
        _json_ready(value),
        ensure_ascii=False,
        sort_keys=True,
        allow_nan=False,
    )


def _is_diagnostic_key(key: str) -> bool:
    return (
        key in _EXACT_DIAGNOSTIC_KEYS
        or key.startswith(_DIAGNOSTIC_PREFIXES)
        or "melting_window" in key
        or key.endswith("_reliability_status")
        or key.endswith("_reliability_reason")
    )


def _diagnostic_keys(rows: list[dict[str, Any]]) -> list[str]:
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key, value in row.items():
            if not isinstance(key, str) or key.startswith("_") or key in seen:
                continue
            is_scalar, _ = _as_scalar(value)
            if _is_diagnostic_key(key) or not is_scalar:
                seen.add(key)
                keys.append(key)
    return keys


def _is_hero_value(value: TableScalar) -> bool:
    if value is None or value == "":
        return False
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, complex):
        return math.isfinite(value.real) and math.isfinite(value.imag)
    return True


def _hero_metrics(
    payload: dict[str, Any],
    rows: list[dict[str, Any]],
    template: ResultTableTemplate,
    *,
    language: str,
) -> tuple[HeroMetric, ...]:
    if not rows:
        return ()
    first_row = rows[0]
    heroes: list[HeroMetric] = []
    for field in template.hero_fields:
        selected_row: Mapping[str, Any] | None = None
        selected_lc: _ResolvedLc | None = None
        value: TableScalar = None
        for candidate in (payload, first_row):
            candidate_lc = (
                _resolve_lc(candidate, language=language)
                if field.key == "lc_nm"
                else None
            )
            candidate_value = (
                candidate_lc.value
                if candidate_lc is not None
                else _field_value(candidate, field)
            )
            if _is_hero_value(candidate_value):
                selected_row = candidate
                selected_lc = candidate_lc
                value = candidate_value
                break
        if selected_row is None:
            continue
        status_value = _linked_value(selected_row, field.status_key)
        if selected_lc is not None:
            provenance = selected_lc.provenance
            status = _status_with_source_review(
                _status_token(status_value),
                ambiguous=selected_lc.ambiguous,
            )
            tooltip = selected_lc.tooltip
        else:
            provenance_value = _linked_value(selected_row, field.provenance_key)
            provenance = (
                str(provenance_value).strip()
                if provenance_value not in {None, ""}
                else ""
            )
            status = _status_token(status_value)
            tooltip = ""
        heroes.append(
            HeroMetric(
                key=field.key,
                label=tr_for_language(field.label_key, language),
                raw=value,
                display=_formatted(field.key, value, digits=field.digits, language=language),
                unit=field.unit,
                status=status,
                provenance=provenance,
                tooltip=tooltip,
            )
        )
    return tuple(heroes[: len(template.hero_fields)])


def build_saxs_results_presentation(
    params: dict[str, Any],
    *,
    submodule: str,
    language: str,
) -> ResultsTablePresentation:
    """Return a presentation-only SAXS result model without changing *params*."""
    template = saxs_template(submodule)
    payload, rows = _copied_rows(params)
    target_language = _language_code(language)
    primary = _primary_section(rows, template, language=target_language)
    view_rows = _batch_view_rows(payload, rows)
    detail = _dynamic_section(
        view_rows,
        _stable_scalar_keys(view_rows),
        language=target_language,
    )
    diagnostics = _dynamic_section(
        view_rows,
        _diagnostic_keys(view_rows),
        language=target_language,
        serialize_nested=True,
    )
    heroes = _hero_metrics(
        payload,
        rows,
        template,
        language=target_language,
    )
    risk_text, next_text = _series_metric_review_text(
        payload,
        language=target_language,
    )

    row_count = len(rows)
    has_rows = row_count > 0
    return ResultsTablePresentation(
        kind=template.key,
        primary=primary,
        detail=detail,
        diagnostics=diagnostics,
        hero_metrics=heroes,
        risk_text=risk_text,
        next_text=next_text,
        summary_count=row_count,
        sortable=row_count > 1,
        copy_enabled=has_rows,
        export_enabled=has_rows,
    )
