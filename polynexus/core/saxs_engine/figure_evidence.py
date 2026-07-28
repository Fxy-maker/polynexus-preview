"""Compact, read-only quality provenance for SAXS figure definitions."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np

from ..figures.contracts import FigureDefinition
from .figure_common import SAXSFrameView


_QUALITY_EVIDENCE_FILE = "quality_evidence.json"
_QUALITY_LEVELS = frozenset({"Quantitative", "Trend", "Diagnostic", "Unusable"})
_COMMON_EVIDENCE_FIELDS = (
    "metric_name",
    "level",
    "applicable",
    "value",
    "unit",
    "uncertainty",
    "reason_codes",
    "source_ref",
    "data_quality_ref",
    "processing_ref",
    "fit_evidence",
    "physical_checks",
    "condition_axis",
)
_DETECTOR_EVIDENCE_FIELDS = (
    "metric_name",
    "level",
    "applicable",
    "value",
    "unit",
    "reason_codes",
    "source_ref",
    "source_kind",
    "source_kinds",
    "shape",
    "pixel_count",
    "finite_pixel_count",
    "nonfinite_pixel_count",
    "nonpositive_pixel_count",
    "masked_pixel_count",
    "saturated_pixel_count",
    "valid_pixel_count",
    "coverage_fraction",
    "saturation_detection_available",
    "beam_center_available",
    "beam_center",
    "geometry_provenance",
    "mask_provenance",
    "frame_count",
    "evidence_frame_count",
    "missing_frame_count",
    "usable_frame_count",
    "diagnostic_frame_count",
    "unusable_frame_count",
    "evidence_frame_indices",
    "missing_frame_indices",
)
_DATA_QUALITY_FIELDS = (
    "source_id",
    "raw_data_ref",
    "processed_data_ref",
    "processing_config_ref",
    "level",
    "reason_codes",
    "actions",
)
_GUINIER_FIELDS = (
    "rg_nm",
    "i0",
    "q_min_nm1",
    "q_max_nm1",
    "q_rg_max",
    "point_count",
    "r_squared",
    "slope",
    "slope_uncertainty",
    "rg_uncertainty_nm",
    "assumption_supported",
    "level",
    "reason_codes",
    "source_ref",
    "metric",
)
_SEQUENCE_FIELDS = (
    "frame_count",
    "finite_temperature_count",
    "valid_frame_count",
    "missing_frame_indices",
    "diagnostic_frame_indices",
    "invalid_temperature_indices",
    "duplicate_temperature_indices",
    "nonmonotonic_temperature_indices",
    "continuity_break_indices",
    "frame_source_indices",
    "temperature_min_C",
    "temperature_max_C",
    "rg_min_nm",
    "rg_max_nm",
    "relative_change_stats",
    "level",
    "reason_codes",
    "metric",
    "source_ref",
)
_AI_PLAN_FIELDS = (
    "policy_version",
    "automation_state",
    "candidate_only",
    "original_preserved",
    "physical_validation_required",
    "reason_codes",
)
_AI_DECISION_FIELDS = (
    "decision",
    "simulated_decision",
    "confidence_band",
    "apply_allowed",
    "original_preserved",
    "physical_validation_required",
    "hard_guard_results",
    "reason_codes",
)
_AI_REPLAY_FIELDS = (
    "candidate_id",
    "mode",
    "run_status",
    "decision",
    "apply_performed",
    "reason_codes",
)
_AI_RERUN_FIELDS = (
    "candidate_id",
    "mode",
    "phase",
    "apply_performed",
    "physical_gate_status",
    "quality_gate_status",
    "rollback_reason",
    "before_config_hash",
    "after_config_hash",
)
_MISSING = object()


def _json_safe(value: Any) -> Any:
    """Return a detached value accepted by strict ``json.dumps``."""

    if isinstance(value, Enum):
        return _json_safe(value.value)
    if isinstance(value, np.ndarray):
        return [_json_safe(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, Mapping):
        return {
            str(key): _json_safe(item)
            for key, item in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return [_json_safe(item) for item in sorted(value, key=repr)]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, float):
        return value if np.isfinite(value) else None
    if isinstance(value, (int, str, bool)) or value is None:
        return value
    return None


def _project_mapping(
    payload: Any,
    fields: Sequence[str],
) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {}
    projected: dict[str, Any] = {}
    for key in fields:
        if key not in payload:
            continue
        value = payload[key]
        if key == "level":
            level = value.value if isinstance(value, Enum) else value
            if str(level) not in _QUALITY_LEVELS:
                continue
            value = str(level)
        elif key == "metric" and isinstance(value, Mapping):
            value = _project_mapping(value, _COMMON_EVIDENCE_FIELDS)
        projected[key] = _json_safe(value)
    return projected


def _project_metric_collection(payload: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(payload, Mapping):
        return {}
    if "metric_name" in payload or "level" in payload:
        metric_name = str(payload.get("metric_name") or "metric")
        return {metric_name: _project_mapping(payload, _COMMON_EVIDENCE_FIELDS)}
    projected: dict[str, dict[str, Any]] = {}
    for name in sorted(payload, key=str):
        item = payload[name]
        if not isinstance(item, Mapping):
            continue
        record = _project_mapping(item, _COMMON_EVIDENCE_FIELDS)
        if record:
            projected[str(name)] = record
    return projected


def _detector_evidence_fields(
    field: str,
    payload: Any,
) -> Sequence[str]:
    """Keep raw-only provenance out of the sector-map detector contract."""
    if field == "raw_detector_quality_report":
        return _DETECTOR_EVIDENCE_FIELDS
    return tuple(
        name
        for name in _DETECTOR_EVIDENCE_FIELDS
        if name not in {"geometry_provenance", "mask_provenance"}
    )


def _first_frame_value(frame: SAXSFrameView, field: str) -> Any:
    sources: list[Mapping[str, Any]] = []
    if isinstance(frame.parameters, Mapping):
        sources.append(frame.parameters)
    analysis_parameters = getattr(frame.analysis, "final_parameters", None)
    if isinstance(analysis_parameters, Mapping):
        sources.append(analysis_parameters)
    for source in sources:
        value = source.get(field, _MISSING)
        if value is not _MISSING and value not in ({}, None, ()):
            return value
    return getattr(frame.analysis, field, None)


def _temperature_source_index(
    frame_index: int,
    series: Any,
) -> int | None:
    """Resolve only an already-emitted temperature point source index."""

    points = getattr(series, "temp_points", ()) if series is not None else ()
    if not isinstance(points, Sequence) or isinstance(points, (str, bytes)):
        return None
    for point in points:
        try:
            source_index = int(getattr(point, "source_index"))
        except (AttributeError, TypeError, ValueError):
            continue
        if source_index == int(frame_index):
            return source_index
    return None


def _frame_record(
    frame: SAXSFrameView,
    *,
    mode: str,
    series: Any,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "frame_index": int(frame.index),
        "condition": _json_safe(frame.condition),
        "source_path": str(frame.source_path or ""),
        "metric_evidence": _project_metric_collection(
            _first_frame_value(frame, "metric_evidence")
        ),
    }
    if mode == "temperature":
        source_index = _temperature_source_index(frame.index, series)
        if source_index is not None:
            record["source_index"] = source_index

    guinier = _project_mapping(
        _first_frame_value(frame, "guinier_evidence"),
        _GUINIER_FIELDS,
    )
    if guinier:
        record["guinier_evidence"] = guinier
    for field in (
        "data_quality_report",
        "detector_quality_report",
        "raw_detector_quality_report",
        "orientation_evidence",
    ):
        value = _first_frame_value(frame, field)
        if field == "data_quality_report":
            fields = _DATA_QUALITY_FIELDS
        elif field in {"detector_quality_report", "raw_detector_quality_report"}:
            fields = _detector_evidence_fields(field, value)
        else:
            fields = _COMMON_EVIDENCE_FIELDS
        projected = _project_mapping(value, fields)
        if projected:
            record[field] = projected
    return record


def _series_record(series: Any) -> dict[str, Any]:
    if series is None:
        return {}
    record: dict[str, Any] = {}
    metric_evidence = _project_metric_collection(
        getattr(series, "metric_evidence", None)
    )
    if metric_evidence:
        record["metric_evidence"] = metric_evidence
    sequence = _project_mapping(
        getattr(series, "guinier_sequence_evidence", None),
        _SEQUENCE_FIELDS,
    )
    if sequence:
        record["guinier_sequence_evidence"] = sequence
    for field in (
        "detector_quality_report",
        "raw_detector_quality_report",
        "orientation_evidence",
    ):
        projected = _project_mapping(
            getattr(series, field, None),
            _detector_evidence_fields(field, getattr(series, field, None))
            if field in {"detector_quality_report", "raw_detector_quality_report"}
            else _COMMON_EVIDENCE_FIELDS,
        )
        if projected:
            record[field] = projected
    return record


def _project_ai_rescue_evidence(payload: Any) -> dict[str, Any]:
    """Project only compact, non-executable AI audit metadata."""

    if not isinstance(payload, Mapping):
        return {}
    projected: dict[str, Any] = {}

    plan = payload.get("saxs_ai_rescue_plan")
    if isinstance(plan, Mapping):
        plan_record = _project_mapping(plan, _AI_PLAN_FIELDS)
        candidates = plan.get("candidates")
        candidate_ids = [
            str(item.get("candidate_id")).strip()
            for item in candidates
            if isinstance(item, Mapping) and str(item.get("candidate_id") or "").strip()
        ] if isinstance(candidates, (list, tuple)) else []
        if candidate_ids:
            plan_record["candidate_count"] = len(candidate_ids)
            plan_record["candidate_ids"] = candidate_ids
        if plan_record:
            projected["plan"] = plan_record

    decision = payload.get("saxs_ai_rescue_decision")
    if isinstance(decision, Mapping):
        decision_record = _project_mapping(decision, _AI_DECISION_FIELDS)
        if decision_record:
            projected["decision"] = decision_record

    replay_rows: list[dict[str, Any]] = []
    replay = payload.get("saxs_ai_rescue_replay")
    if isinstance(replay, (list, tuple)):
        for item in replay:
            if not isinstance(item, Mapping):
                continue
            if not str(item.get("candidate_id") or "").strip():
                continue
            row = _project_mapping(item, _AI_REPLAY_FIELDS)
            if row:
                replay_rows.append(row)
    if replay_rows:
        projected["replay"] = replay_rows

    rerun = payload.get("saxs_confirmed_rerun_audit")
    if isinstance(rerun, Mapping):
        rerun_record = _project_mapping(rerun, _AI_RERUN_FIELDS)
        if rerun_record and any(
            key in rerun_record
            for key in ("candidate_id", "mode", "phase", "rollback_reason")
        ):
            projected["confirmed_rerun"] = rerun_record

    return projected


def build_saxs_figure_evidence(
    frames: Sequence[SAXSFrameView],
    *,
    mode: str,
    series: Any = None,
    ai_rescue: Mapping[str, Any] | None = None,
    acceptance_audit: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build detached provenance for existing SAXS frame/series evidence."""

    normalized_mode = str(mode or "").strip().lower()
    if normalized_mode not in {"static", "temperature", "strain"}:
        normalized_mode = "static"
    frame_records = tuple(
        _frame_record(frame, mode=normalized_mode, series=series)
        for frame in frames
        if isinstance(frame, SAXSFrameView)
    )
    payload: dict[str, Any] = {
        "schema_version": 1,
        "mode": normalized_mode,
        "quality_evidence_file": _QUALITY_EVIDENCE_FILE,
        "frame_indices": [record["frame_index"] for record in frame_records],
        "frame_records": list(frame_records),
    }
    if normalized_mode == "temperature":
        payload["source_indices"] = [
            record["source_index"]
            for record in frame_records
            if "source_index" in record
        ]
    series_record = _series_record(series)
    if series_record:
        payload["series_record"] = series_record
    ai_record = _project_ai_rescue_evidence(ai_rescue)
    if ai_record:
        payload["ai_rescue"] = ai_record
    if isinstance(acceptance_audit, Mapping):
        payload["scientific_acceptance_audit"] = _json_safe(acceptance_audit)
    return _json_safe(payload)


def attach_saxs_figure_evidence(
    definitions: Sequence[FigureDefinition],
    frames: Sequence[SAXSFrameView],
    *,
    mode: str,
    series: Any = None,
    ai_rescue: Mapping[str, Any] | None = None,
    acceptance_audit: Mapping[str, Any] | None = None,
) -> tuple[FigureDefinition, ...]:
    """Merge quality provenance into recipes without changing figure roles."""

    try:
        provenance = build_saxs_figure_evidence(
            frames,
            mode=mode,
            series=series,
            ai_rescue=ai_rescue,
            acceptance_audit=acceptance_audit,
        )
    except Exception:
        provenance = {
            "schema_version": 1,
            "mode": str(mode or "static"),
            "quality_evidence_file": _QUALITY_EVIDENCE_FILE,
            "frame_indices": [],
            "frame_records": [],
            "attachment_reason": "evidence_attachment_failed",
        }
    attached: list[FigureDefinition] = []
    for definition in definitions:
        recipe = dict(definition.recipe)
        evidence = recipe.get("evidence", {})
        evidence_mapping = dict(evidence) if isinstance(evidence, Mapping) else {}
        evidence_mapping["quality_provenance"] = provenance
        recipe["evidence"] = evidence_mapping
        attached.append(replace(definition, recipe=recipe))
    return tuple(attached)


def existing_saxs_acceptance_audit(source: Any) -> dict[str, Any] | None:
    """Return a detached existing audit snapshot without recalculating it."""

    result = getattr(source, "result", source)
    parameters = getattr(result, "parameters", None)
    if not isinstance(parameters, Mapping):
        return None
    audit = parameters.get("scientific_acceptance_audit")
    if not isinstance(audit, Mapping):
        return None
    projected = _json_safe(audit)
    return projected if isinstance(projected, dict) else None


__all__ = [
    "attach_saxs_figure_evidence",
    "build_saxs_figure_evidence",
    "existing_saxs_acceptance_audit",
]
