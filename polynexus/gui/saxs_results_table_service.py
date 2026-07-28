"""Build immutable, localized table presentations from SAXS result payloads."""

from __future__ import annotations

import json
import math
from collections import Counter
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
    scope = str(payload.get("metric_evidence_scope") or "").strip().lower()
    static_batch = scope == "static_batch"
    aligned_batch = scope == "aligned_batch"
    if static_batch:
        scope_label = "Batch quality" if not zh else "\u6279\u6b21\u8d28\u91cf"
        detail = f"{scope_label}: {detail}"
    elif aligned_batch:
        scope_label = "Aligned batch quality" if not zh else "\u5bf9\u9f50\u6279\u6b21\u8d28\u91cf"
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
        if aligned_batch:
            next_text = tr_for_language(
                "RESULTS_REVIEW_NEXT",
                language,
                "\u5728\u4f7f\u7528\u5bf9\u9f50\u6279\u6b21\u8d28\u91cf\u6458\u8981\u524d\uff0c\u5148\u590d\u6838\u7f3a\u5931\u5e27\u548c\u8bca\u65ad\u5e27"
                if zh
                else "Review missing and diagnostic frames before using the aligned batch quality summary",
            )
            return risk, next_text
        next_text = tr_for_language(
            "RESULTS_REVIEW_NEXT",
            language,
            "先复核缺帧和诊断帧" if zh else "Review missing and diagnostic frames before using the series trend",
        )
        return risk, next_text
    return "", tr_for_language("RESULTS_REVIEW_NEXT", language, detail)


def _detector_evidence_review_text(
    payload: Mapping[str, Any],
    *,
    language: str,
) -> tuple[str, str]:
    """Present existing raw/sector detector evidence without interpreting it."""

    if not isinstance(payload, Mapping):
        return "", ""

    zh = language == "zh"
    level_labels = {
        "Quantitative": "定量" if zh else "Quantitative",
        "Trend": "趋势" if zh else "Trend",
        "Diagnostic": "诊断" if zh else "Diagnostic",
        "Unusable": "不可用" if zh else "Unusable",
    }
    details: list[str] = []
    needs_review = False

    def _count(report: Mapping[str, Any], key: str) -> int | None:
        if key not in report:
            return None
        try:
            return max(0, int(report.get(key) or 0))
        except (TypeError, ValueError):
            return None

    def _fraction(report: Mapping[str, Any]) -> float | None:
        try:
            value = float(report.get("coverage_fraction"))
        except (TypeError, ValueError):
            return None
        return value if math.isfinite(value) else None

    def _provenance_text(report: Mapping[str, Any]) -> str:
        """Project raw-detector provenance without assessing scientific validity."""
        geometry = report.get("geometry_provenance")
        mask = report.get("mask_provenance")
        if not isinstance(geometry, Mapping) and not isinstance(mask, Mapping):
            return ""

        if zh:
            parts: list[str] = []
            geometry_label = "几何来源"
            field_label = "几何字段来源"
            mask_label = "掩膜来源"
            configured_label = "已配置"
            shape_label = "形状"
            validity_label = "证据状态"
        else:
            parts = []
            geometry_label = "geometry source"
            field_label = "geometry fields"
            mask_label = "mask source"
            configured_label = "configured"
            shape_label = "shape"
            validity_label = "validity"

        if isinstance(geometry, Mapping):
            source = str(geometry.get("source") or "").strip()
            if source:
                parts.append(f"{geometry_label}={source}")
            field_sources = geometry.get("field_sources")
            if isinstance(field_sources, Mapping):
                counts = {
                    name: 0
                    for name in ("header", "config_default", "invalid_header")
                }
                for value in field_sources.values():
                    name = str(value or "").strip()
                    if name in counts:
                        counts[name] += 1
                count_text = ", ".join(
                    f"{name}={counts[name]}"
                    for name in ("header", "config_default", "invalid_header")
                    if counts[name]
                )
                if count_text:
                    parts.append(f"{field_label}={count_text}")
            validity = str(geometry.get("validity") or "").strip()
            if validity:
                parts.append(f"{validity_label}={validity}")

        if isinstance(mask, Mapping):
            source = str(mask.get("source") or "").strip()
            if source:
                parts.append(f"{mask_label}={source}")
            if "configured" in mask:
                parts.append(f"{configured_label}={bool(mask.get('configured'))}")
            shape = mask.get("shape")
            if isinstance(shape, (list, tuple)) and len(shape) == 2:
                try:
                    shape_text = f"{int(shape[0])}x{int(shape[1])}"
                except (TypeError, ValueError):
                    shape_text = "Unavailable"
            elif shape is None:
                shape_text = "Unavailable"
            else:
                shape_text = str(shape)
            parts.append(f"{shape_label}={shape_text}")
            validity = str(mask.get("validity") or "").strip()
            if validity:
                parts.append(f"{validity_label}={validity}")
        return ", ".join(parts)

    for field_name, default_source in (
        ("raw_detector_quality_report", "raw detector"),
        ("detector_quality_report", "sector map"),
    ):
        report = payload.get(field_name)
        if not isinstance(report, Mapping):
            continue

        level = str(report.get("level") or "Unusable").strip() or "Unusable"
        source_kind = str(report.get("source_kind") or "").strip().lower()
        source = (
            "raw detector"
            if source_kind == "raw_detector" or field_name.startswith("raw_")
            else "sector map"
            if source_kind == "sector_map"
            else default_source
        )
        if zh:
            source = "原始探测器" if source == "raw detector" else "扇区图"

        parts = [f"{source}: {level_labels.get(level, level)}"]
        evidence_count = _count(report, "evidence_frame_count")
        frame_count = _count(report, "frame_count")
        coverage_text = ""
        if evidence_count is not None and frame_count is not None:
            coverage_text = f"{'覆盖' if zh else 'coverage'}={evidence_count}/{frame_count}"
        coverage = _fraction(report)
        if coverage is not None:
            coverage_text += f" ({coverage * 100:.0f}%)" if coverage_text else f"{coverage * 100:.0f}%"
        if coverage_text:
            parts.append(coverage_text)

        raw_reasons = report.get("reason_codes")
        if isinstance(raw_reasons, str):
            reasons = (raw_reasons,)
        elif isinstance(raw_reasons, (list, tuple)):
            reasons = tuple(raw_reasons)
        else:
            reasons = ()
        reason_text = ",".join(
            str(reason).strip() for reason in reasons[:3] if str(reason).strip()
        )
        if reason_text:
            parts.append(f"{'原因' if zh else 'reasons'}={reason_text[:240]}")

        if field_name == "raw_detector_quality_report":
            provenance_text = _provenance_text(report)
            if provenance_text:
                parts.append(provenance_text)

        incomplete = (
            evidence_count is not None
            and frame_count is not None
            and evidence_count < frame_count
        )
        needs_review = needs_review or level in {"Diagnostic", "Unusable"} or bool(reason_text) or incomplete
        details.append("; ".join(parts))

    if not details:
        return "", ""
    detail = " | ".join(details)
    if needs_review:
        next_instruction = (
            "在使用 detector evidence 前先复核来源、缺失帧和原因；几何与 mask 有效性仍需人工确认"
            if zh
            else "Review detector evidence sources, missing frames, and reasons before use; geometry and mask validity still require human confirmation"
        )
        return tr_for_language("RESULTS_REVIEW_RISK", language, detail), tr_for_language(
            "RESULTS_REVIEW_NEXT", language, next_instruction
        )
    return "", tr_for_language("RESULTS_REVIEW_NEXT", language, detail)


def _data_quality_review_text(
    payload: Mapping[str, Any],
    *,
    language: str,
) -> tuple[str, str]:
    """Present existing q/I data-quality reports without reclassification."""

    if not isinstance(payload, Mapping):
        return "", ""

    zh = language == "zh"
    level_labels = {
        "Quantitative": "定量",
        "Trend": "趋势",
        "Diagnostic": "诊断",
        "Unusable": "不可用",
    }

    def _items(value: Any) -> tuple[str, ...]:
        if isinstance(value, str):
            values = (value,)
        elif isinstance(value, (list, tuple)):
            values = tuple(value)
        else:
            values = ()
        return tuple(str(item).strip() for item in values if str(item).strip())

    def _ordered_unique(values: list[str]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(value for value in values if value))

    reports: list[Mapping[str, Any]] = []
    top_report = payload.get("data_quality_report")
    if isinstance(top_report, Mapping):
        reports.append(top_report)

    batch_data = payload.get("_batch_data")
    batch_rows = (
        tuple(batch_data)
        if isinstance(batch_data, (list, tuple))
        else ()
    )
    batch_reports = tuple(
        row["data_quality_report"]
        for row in batch_rows
        if isinstance(row, Mapping) and isinstance(row.get("data_quality_report"), Mapping)
    )
    if not reports and not batch_reports:
        return "", ""

    lines: list[str] = []
    needs_review = False
    for report in reports:
        level = str(report.get("level") or "Unusable").strip() or "Unusable"
        level_text = level_labels.get(level, level) if zh else level
        parts = [f"{'数据质量' if zh else 'Data quality'}: {level_text}"]
        source_id = str(report.get("source_id") or "").strip()
        if source_id:
            parts.append(f"{'来源' if zh else 'source'}={source_id}")
        for ref_key, label in (
            ("raw_data_ref", "原始引用" if zh else "raw ref"),
            ("processed_data_ref", "处理后引用" if zh else "processed ref"),
            ("processing_config_ref", "处理配置引用" if zh else "config ref"),
        ):
            ref = str(report.get(ref_key) or "").strip()
            if ref:
                parts.append(f"{label}={ref}")

        try:
            original_count = int(report.get("original_point_count"))
            usable_count = int(report.get("usable_point_count"))
            invalid_count = int(report.get("invalid_point_count"))
        except (TypeError, ValueError):
            original_count = usable_count = invalid_count = None
        if original_count is not None and usable_count is not None:
            parts.append(
                f"{'可用点' if zh else 'usable points'}={usable_count}/{original_count}"
            )
        if invalid_count is not None:
            parts.append(f"{'无效点' if zh else 'invalid'}={invalid_count}")

        reasons = _items(report.get("reason_codes"))
        actions = _items(report.get("actions"))
        if reasons:
            parts.append(f"{'原因' if zh else 'reasons'}=" + ",".join(reasons[:5]))
        if actions:
            parts.append(f"{'动作' if zh else 'actions'}=" + ",".join(actions[:5]))
        lines.append("; ".join(parts))
        needs_review = needs_review or level in {"Diagnostic", "Unusable"} or bool(reasons)

    if batch_data is not None and batch_rows:
        level_counts = Counter(
            str(report.get("level") or "Unusable").strip() or "Unusable"
            for report in batch_reports
        )
        batch_reasons = _ordered_unique(
            [reason for report in batch_reports for reason in _items(report.get("reason_codes"))]
        )
        batch_actions = _ordered_unique(
            [action for report in batch_reports for action in _items(report.get("actions"))]
        )
        coverage = f"{len(batch_reports)}/{len(batch_rows)}"
        level_text = ", ".join(
            f"{level_labels.get(level, level) if zh else level}={count}"
            for level, count in level_counts.items()
        )
        batch_line = f"{'数据质量帧' if zh else 'Data-quality frames'}: {coverage}"
        if level_text:
            batch_line += f"; {'等级' if zh else 'levels'}={level_text}"
        if batch_reasons:
            batch_line += f"; {'原因' if zh else 'reasons'}=" + ",".join(batch_reasons[:5])
        if batch_actions:
            batch_line += f"; {'动作' if zh else 'actions'}=" + ",".join(batch_actions[:5])
        lines.append(batch_line)
        needs_review = needs_review or len(batch_reports) < len(batch_rows) or bool(batch_reasons)

    detail = " | ".join(lines)
    risk = tr_for_language("RESULTS_REVIEW_RISK", language, detail) if needs_review else ""
    next_text = tr_for_language(
        "RESULTS_REVIEW_NEXT",
        language,
        "Review q/I data quality sources, reasons, and actions before interpretation; existing SAXS physical gates remain authoritative"
        if not zh
        else "解释前请先复核 q/I 数据质量来源、原因和处理动作；现有 SAXS 物理门槛仍然有效",
    )
    return risk, next_text


def _condition_axis_review_text(
    payload: Mapping[str, Any],
    *,
    language: str,
) -> tuple[str, str]:
    """Present existing condition-axis defects as advisory review text."""

    evidence = payload.get("metric_evidence") if isinstance(payload, Mapping) else None
    if not isinstance(evidence, Mapping):
        return "", ""

    zh = language == "zh"
    axis_lines: list[str] = []

    def _items(axis: Mapping[str, Any], key: str) -> list[Any]:
        value = axis.get(key)
        return list(value) if isinstance(value, (list, tuple)) else []

    def _positions_text(position_groups: list[list[Any]]) -> str:
        positions: list[str] = []
        for group in position_groups:
            for item in group:
                rendered = str(item).strip()
                if rendered and rendered not in positions:
                    positions.append(rendered)
        def _sort_key(item: str) -> tuple[int, float | str]:
            try:
                return 0, float(item)
            except ValueError:
                return 1, item

        positions.sort(key=_sort_key)
        suffix = ", ..." if len(positions) > 8 else ""
        return "[" + ", ".join(positions[:8]) + suffix + "]"

    for raw_name, summary in sorted(evidence.items(), key=lambda item: str(item[0])):
        if not isinstance(summary, Mapping):
            continue
        axis = summary.get("condition_axis")
        if not isinstance(axis, Mapping):
            continue
        status = str(axis.get("status") or "").strip().lower()
        if status not in {"diagnostic", "empty"}:
            continue

        name = str(raw_name)
        metric_name = str(summary.get("metric_name") or name).strip() or name
        if name.lower() == "guinier" or metric_name.lower() == "guinier":
            metric_name = "Rg"
        condition_name = str(axis.get("condition_name") or "condition").strip()
        invalid = _items(axis, "invalid_condition_indices")
        duplicate = _items(axis, "duplicate_condition_indices")
        nonmonotonic = _items(axis, "nonmonotonic_condition_indices")
        positions_text = _positions_text([invalid, duplicate, nonmonotonic])
        raw_reasons = summary.get("reason_codes")
        if isinstance(raw_reasons, str):
            reason_values = (raw_reasons,)
        elif isinstance(raw_reasons, (list, tuple)):
            reason_values = raw_reasons
        else:
            reason_values = ()
        axis_reasons = [
            str(reason).strip()
            for reason in reason_values
            if str(reason).strip().startswith("series_metric_condition_axis")
        ]
        if zh:
            detail = (
                f"{metric_name}: 条件轴 {condition_name} {status}；"
                f"无效={len(invalid)}；重复={len(duplicate)}；"
                f"非单调={len(nonmonotonic)}；位置={positions_text}"
            )
            reason_label = "原因"
            next_instruction = (
                "在解释序列趋势前先复核条件轴诊断；完整位置和值仍在 Diagnostics"
            )
        else:
            detail = (
                f"{metric_name}: condition axis {condition_name} {status}; "
                f"invalid={len(invalid)}; duplicate={len(duplicate)}; "
                f"non-monotonic={len(nonmonotonic)}; positions={positions_text}"
            )
            reason_label = "reasons"
            next_instruction = (
                "Review condition-axis diagnostics before interpreting sequence trends; "
                "full positions and values remain in Diagnostics"
            )
        if axis_reasons:
            detail += f"; {reason_label}=" + ",".join(axis_reasons[:3])
        axis_lines.append(detail)

    if not axis_lines:
        return "", ""
    detail = " | ".join(axis_lines)
    risk = tr_for_language("RESULTS_REVIEW_RISK", language, detail)
    next_text = tr_for_language("RESULTS_REVIEW_NEXT", language, next_instruction)
    return risk, next_text


def _guinier_sequence_review_text(
    payload: Mapping[str, Any],
    *,
    language: str,
) -> tuple[str, str]:
    """Present existing temperature Guinier sequence evidence as advisory review."""

    sequence = payload.get("guinier_sequence_evidence") if isinstance(payload, Mapping) else None
    if not isinstance(sequence, Mapping):
        return "", ""

    zh = language == "zh"
    level = str(sequence.get("level") or "Unusable").strip() or "Unusable"

    def _count(key: str) -> int:
        try:
            return max(0, int(sequence.get(key, 0) or 0))
        except (TypeError, ValueError):
            return 0

    frame_count = _count("frame_count")
    valid_count = _count("valid_frame_count")
    missing = sequence.get("missing_frame_indices")
    diagnostic = sequence.get("diagnostic_frame_indices")
    source_indices = sequence.get("frame_source_indices")
    missing_count = len(missing) if isinstance(missing, (list, tuple)) else 0
    diagnostic_count = len(diagnostic) if isinstance(diagnostic, (list, tuple)) else 0
    source_text = (
        ",".join(str(item) for item in source_indices)
        if isinstance(source_indices, (list, tuple))
        else "unavailable"
    )
    reasons = sequence.get("reason_codes")
    if isinstance(reasons, str):
        reasons = (reasons,)
    elif not isinstance(reasons, (list, tuple)):
        reasons = ()
    reason_text = ",".join(str(reason) for reason in reasons if str(reason).strip())
    detail = (
        f"{'Rg sequence' if not zh else 'Rg序列'}: {level} ({valid_count}/{frame_count}); "
        f"{'missing' if not zh else '缺帧'}={missing_count}; "
        f"{'diagnostic' if not zh else '诊断帧'}={diagnostic_count}; "
        f"{'source indices' if not zh else '来源索引'}=[{source_text}]"
    )
    if reason_text:
        detail += f"; {'reasons' if not zh else '原因'}={reason_text}"

    needs_review = bool(
        level in {"Diagnostic", "Unusable"}
        or missing_count
        or diagnostic_count
        or reason_text
    )
    risk = tr_for_language("RESULTS_REVIEW_RISK", language, detail) if needs_review else ""
    next_text = tr_for_language(
        "RESULTS_REVIEW_NEXT",
        language,
        "Use Rg sequence evidence only as an advisory diagnostic; confirm frame-level SAXS physical and quality gates before interpretation"
        if not zh
        else "Rg序列证据仅作诊断性趋势提示；解释前须复核逐帧SAXS物理指标和质量门槛",
    )
    return risk, next_text


def _scientific_acceptance_audit_review_text(
    payload: Mapping[str, Any],
    *,
    language: str,
) -> tuple[str, str]:
    """Present the existing acceptance audit as advisory review evidence."""

    audit = payload.get("scientific_acceptance_audit")
    if not isinstance(audit, Mapping):
        return "", ""
    status = str(audit.get("status") or "").strip()
    if not status:
        return "", ""
    raw_reasons = audit.get("reason_codes")
    if isinstance(raw_reasons, str):
        reasons = (raw_reasons,)
    elif isinstance(raw_reasons, (list, tuple)):
        reasons = tuple(str(reason).strip() for reason in raw_reasons)
    else:
        reasons = ()
    reason_text = ",".join(reason[:100] for reason in reasons if reason) or "none"
    scope = str(audit.get("audit_scope") or "existing_gates_only").strip()
    if language == "zh":
        detail = f"科学验收审计：状态={status}；原因={reason_text}；范围={scope}"
        next_instruction = "该审计仅汇总已有门槛；解释或发表前仍需复核逐帧 SAXS 物理指标、质量门槛和人工审查"
    else:
        detail = (
            "Scientific acceptance audit: "
            f"status={status}; reasons={reason_text}; scope={scope}"
        )
        next_instruction = (
            "Use this existing gates audit as advisory evidence only; review "
            "frame-level SAXS physical and quality gates before interpretation or publication"
        )
    return tr_for_language("RESULTS_REVIEW_RISK", language, detail), tr_for_language(
        "RESULTS_REVIEW_NEXT", language, next_instruction
    )


def _sequence_rescue_review_text(
    payload: Mapping[str, Any],
    *,
    language: str,
) -> tuple[str, str]:
    """Present existing sequence-rescue candidates without accepting them."""

    if not isinstance(payload, Mapping):
        return "", ""

    raw_candidates = payload.get("sequence_rescue_candidates")
    if not isinstance(raw_candidates, (list, tuple)):
        return "", ""

    zh = language == "zh"
    details: list[str] = []
    for raw_candidate in raw_candidates:
        if not isinstance(raw_candidate, Mapping):
            continue
        parameters = raw_candidate.get("parameters")
        if not isinstance(parameters, Mapping):
            continue

        candidate_id = str(raw_candidate.get("candidate_id") or "").strip()
        if not candidate_id:
            continue
        candidate_id = candidate_id[:120]
        frame_index = str(parameters.get("frame_index") or "").strip()
        proposed_source = str(parameters.get("proposed_source") or "").strip()
        proposed_value = str(parameters.get("proposed_value_nm") or "").strip()
        apply_mode = str(parameters.get("apply_mode") or "").strip()
        source = str(raw_candidate.get("source") or "").strip()
        reasons = raw_candidate.get("reason_codes")
        if isinstance(reasons, str):
            reason_values = (reasons,)
        elif isinstance(reasons, (list, tuple)):
            reason_values = tuple(reasons)
        else:
            reason_values = ()
        reason_text = ",".join(
            str(reason).strip()[:80]
            for reason in reason_values[:3]
            if str(reason).strip()
        )

        parts = [
            f"{'救援候选' if zh else 'Rescue candidate'}: {candidate_id}",
        ]
        if frame_index:
            parts.append(f"{'帧' if zh else 'frame'}={frame_index[:32]}")
        if proposed_source:
            parts.append(f"{'候选来源' if zh else 'source'}={proposed_source[:80]}")
        if proposed_value:
            parts.append(f"{'候选值(nm)' if zh else 'proposed nm'}={proposed_value[:32]}")
        if apply_mode:
            parts.append(f"{'模式' if zh else 'mode'}={apply_mode[:40]}")
        if "requires_validation" in raw_candidate:
            parts.append(
                f"{'需验证' if zh else 'requires validation'}="
                f"{bool(raw_candidate.get('requires_validation'))}"
            )
        if source:
            parts.append(f"{'证据来源' if zh else 'evidence source'}={source[:120]}")
        if reason_text:
            parts.append(f"{'原因' if zh else 'reasons'}={reason_text}")
        details.append("; ".join(parts))

    if not details:
        return "", ""

    detail = f"{'救援候选' if zh else 'Rescue candidates'}: {len(details)} | " + " | ".join(details[:5])
    next_instruction = (
        "请先对救援候选执行确定性重算，并复核现有物理、质量和序列门槛；候选值不会自动进入结果"
        if zh
        else "Perform deterministic re-analysis of rescue candidates and confirm existing physical, quality, and sequence gates before any action; candidate values remain advisory"
    )
    return tr_for_language("RESULTS_REVIEW_RISK", language, detail), tr_for_language(
        "RESULTS_REVIEW_NEXT", language, next_instruction
    )


def _saxs_ai_rescue_review_text(
    payload: Mapping[str, Any],
    *,
    language: str,
) -> tuple[str, str]:
    """Present existing AI rescue audit metadata as advisory evidence only."""

    if not isinstance(payload, Mapping):
        return "", ""

    details: list[str] = []
    plan = payload.get("saxs_ai_rescue_plan")
    if isinstance(plan, Mapping):
        candidates = plan.get("candidates")
        candidate_ids = tuple(
            str(item.get("candidate_id") or "").strip()
            for item in candidates
            if isinstance(item, Mapping) and str(item.get("candidate_id") or "").strip()
        ) if isinstance(candidates, (list, tuple)) else ()
        if candidate_ids:
            details.append(
                "AI rescue plan: candidates="
                f"{len(candidate_ids)} [{','.join(candidate_ids[:5])}]"
            )

    decision = payload.get("saxs_ai_rescue_decision")
    if isinstance(decision, Mapping):
        decision_name = str(decision.get("decision") or "").strip()
        if decision_name:
            decision_parts = [f"decision={decision_name}"]
            if "apply_allowed" in decision:
                decision_parts.append(f"apply_allowed={bool(decision.get('apply_allowed'))}")
            if decision.get("original_preserved") is True:
                decision_parts.append("original_preserved=True")
            details.append("AI rescue decision: " + ", ".join(decision_parts))

    replay = payload.get("saxs_ai_rescue_replay")
    if isinstance(replay, (list, tuple)):
        replay_details: list[str] = []
        for item in replay:
            if not isinstance(item, Mapping):
                continue
            candidate_id = str(item.get("candidate_id") or "").strip()
            run_status = str(item.get("run_status") or "").strip()
            if not candidate_id or not run_status:
                continue
            replay_details.append(f"{candidate_id}:{run_status}")
        if replay_details:
            details.append("AI rescue replay: " + ", ".join(replay_details[:5]))

    audit = payload.get("saxs_confirmed_rerun_audit")
    if isinstance(audit, Mapping):
        audit_parts: list[str] = []
        for key in (
            "mode",
            "phase",
            "physical_gate_status",
            "quality_gate_status",
            "rollback_reason",
        ):
            value = str(audit.get(key) or "").strip()
            if value:
                audit_parts.append(f"{key}={value}")
        if audit_parts:
            details.append("AI confirmed-rerun audit: " + ", ".join(audit_parts))

    if not details:
        return "", ""

    detail = " | ".join(details)
    next_instruction = (
        "Review the existing SAXS physical and quality gates and perform deterministic validation before any rescue action; this AI evidence is advisory"
    )
    return tr_for_language("RESULTS_REVIEW_RISK", language, detail), tr_for_language(
        "RESULTS_REVIEW_NEXT", language, next_instruction
    )


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
    metric_risk, metric_next = _series_metric_review_text(
        payload,
        language=target_language,
    )
    axis_risk, axis_next = _condition_axis_review_text(
        payload,
        language=target_language,
    )
    sequence_risk, sequence_next = _guinier_sequence_review_text(
        payload,
        language=target_language,
    )
    audit_risk, audit_next = _scientific_acceptance_audit_review_text(
        payload,
        language=target_language,
    )
    rescue_risk, rescue_next = _sequence_rescue_review_text(
        payload,
        language=target_language,
    )
    ai_risk, ai_next = _saxs_ai_rescue_review_text(
        payload,
        language=target_language,
    )
    detector_risk, detector_next = _detector_evidence_review_text(
        payload,
        language=target_language,
    )
    data_quality_risk, data_quality_next = _data_quality_review_text(
        payload,
        language=target_language,
    )
    risk_sections = (
        audit_risk,
        axis_risk,
        metric_risk,
        sequence_risk,
        rescue_risk,
        ai_risk,
        detector_risk,
        data_quality_risk,
    )
    next_sections = (
        audit_next,
        axis_next,
        metric_next,
        sequence_next,
        rescue_next,
        ai_next,
        detector_next,
        data_quality_next,
    )
    risk_text = "\n".join(text for text in risk_sections if text)
    next_text = "\n".join(text for text in next_sections if text)

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
