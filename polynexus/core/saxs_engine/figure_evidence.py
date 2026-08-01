"""Compact, read-only quality provenance for SAXS figure definitions."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from enum import Enum
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import tempfile
from typing import Any

import numpy as np

from ..figures.contracts import FigureDefinition
from ..scientific_review import (
    promotion_decision,
    review_record_from_payload,
)
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
    "duplicate_source_index_indices",
    "invalid_source_index_indices",
    "source_index_order_reordered",
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
_AI_REFERENCE_FIELDS = (
    "mode",
    "status",
    "unresolved_ids",
    "reason_codes",
)
_MISSING = object()


def _review_source_candidates(frame: SAXSFrameView) -> tuple[str, ...]:
    """Return only already-emitted source references for one frame."""

    candidates: list[str] = []
    for value in (frame.source_path,):
        text = str(value or "").strip()
        if text and text not in candidates:
            candidates.append(text)
    report = _first_frame_value(frame, "data_quality_report")
    if isinstance(report, Mapping):
        for key in ("raw_data_ref", "source_id"):
            text = str(report.get(key) or "").strip()
            if text and text not in candidates:
                candidates.append(text)
    return tuple(candidates)


def _review_frame_decision(
    record: Any,
    frame: SAXSFrameView,
    *,
    expected_scope: str,
) -> dict[str, Any]:
    candidates = _review_source_candidates(frame)
    if not candidates:
        decision = {
            "allowed": False,
            "reason": "source_mismatch",
            "record_id": str(getattr(record, "record_id", "") or ""),
            "scope": expected_scope,
            "source_ref": "",
        }
    else:
        decisions = [
            promotion_decision(
                record,
                expected_scope=expected_scope,
                source_ref=source_ref,
            )
            for source_ref in candidates
        ]
        decision = next(
            (
                {
                    "allowed": bool(item.allowed),
                    "reason": str(item.reason),
                    "record_id": str(item.record_id),
                    "scope": str(item.scope or expected_scope),
                    "source_ref": candidates[index],
                }
                for index, item in enumerate(decisions)
                if item.allowed
            ),
            {
                "allowed": False,
                "reason": str(decisions[0].reason),
                "record_id": str(decisions[0].record_id),
                "scope": str(decisions[0].scope or expected_scope),
                "source_ref": candidates[0],
            },
        )
    decision["frame_index"] = int(frame.index)
    decision["source_candidates"] = list(candidates)
    return decision


def build_saxs_review_evidence(
    review_payload: Any,
    frames: Sequence[SAXSFrameView],
    *,
    expected_scope: str,
) -> dict[str, Any]:
    """Project one existing SAXS review scope onto all supplied frames."""

    if expected_scope not in {"saxs.1d", "saxs.2d"}:
        raise ValueError(f"unsupported SAXS review scope: {expected_scope}")

    if not isinstance(review_payload, Mapping) or not review_payload:
        return {
            "allowed": False,
            "reason": "review_missing",
            "record_id": "",
            "scope": expected_scope,
            "policy_version": "",
            "source_ref": "",
            "source_refs": [],
            "frame_decisions": [],
        }
    record = review_record_from_payload(review_payload)
    if record is None:
        return {
            "allowed": False,
            "reason": "review_missing",
            "record_id": "",
            "scope": expected_scope,
            "policy_version": "",
            "source_ref": "",
            "source_refs": [],
            "frame_decisions": [],
        }

    frame_decisions = [
        _review_frame_decision(
            record,
            frame,
            expected_scope=expected_scope,
        )
        for frame in frames
    ]
    observed_refs = []
    for decision in frame_decisions:
        for source_ref in decision["source_candidates"]:
            if source_ref not in observed_refs:
                observed_refs.append(source_ref)
    if not frame_decisions:
        aggregate = promotion_decision(
            record,
            expected_scope=expected_scope,
            source_ref="",
        )
        reason = str(aggregate.reason)
        allowed = False
    else:
        allowed = all(bool(item["allowed"]) for item in frame_decisions)
        reason = "review_accepted" if allowed else str(
            next(
                item["reason"]
                for item in frame_decisions
                if item["reason"] != "review_accepted"
            )
        )
    source_ref = (
        frame_decisions[0]["source_ref"]
        if len(frame_decisions) == 1
        else ""
    )
    return _json_safe(
        {
            "allowed": allowed,
            "reason": reason,
            "record_id": str(record.record_id),
            "scope": str(record.scope or expected_scope),
            "policy_version": str(record.policy_version or ""),
            "source_ref": source_ref,
            "source_refs": observed_refs,
            "frame_decisions": frame_decisions,
        }
    )


def build_saxs_1d_review_evidence(
    review_payload: Any,
    frames: Sequence[SAXSFrameView],
) -> dict[str, Any]:
    """Project an existing ``saxs.1d`` review onto all supplied frames."""

    return build_saxs_review_evidence(
        review_payload,
        frames,
        expected_scope="saxs.1d",
    )


def build_saxs_2d_review_evidence(
    review_payload: Any,
    frames: Sequence[SAXSFrameView],
) -> dict[str, Any]:
    """Project an existing ``saxs.2d`` review onto all supplied frames."""

    return build_saxs_review_evidence(
        review_payload,
        frames,
        expected_scope="saxs.2d",
    )


def _configured_saxs_review_payload(source: Any) -> Mapping[str, Any] | None:
    """Read the current result review, with a legacy config fallback."""

    result = getattr(source, "result", None)
    metadata = getattr(result, "metadata", None)
    if isinstance(metadata, Mapping):
        payload = metadata.get("scientific_review", _MISSING)
        if isinstance(payload, Mapping):
            return payload

    config = getattr(source, "cfg", source)
    if not hasattr(config, "scientific_review"):
        return None
    payload = getattr(config, "scientific_review")
    return payload if isinstance(payload, Mapping) else {}


def configured_saxs_1d_review(source: Any) -> Any:
    """Read the current result review, retaining config compatibility."""

    return _configured_saxs_review_payload(source)


def configured_saxs_review_evidence(
    source: Any,
    frames: Sequence[SAXSFrameView],
) -> dict[str, Any] | None:
    """Project one configured SAXS review onto existing frame sources.

    This is a consumer adapter only: it validates and source-matches the
    existing reviewer record, then returns the same detached fail-closed shape
    used by Figure provenance. Empty configuration remains absent so generic
    SAXS consumers do not present a missing optional review as a new gate.
    """

    payload = _configured_saxs_review_payload(source)
    if payload is None:
        return None
    declared_scope = str(payload.get("scope") or "").strip()
    expected_scope = (
        declared_scope
        if declared_scope in {"saxs.1d", "saxs.2d"}
        else "saxs.1d"
    )
    return build_saxs_review_evidence(
        payload,
        frames,
        expected_scope=expected_scope,
    )


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


def _series_frame_metric_evidence(
    frame: SAXSFrameView,
    *,
    mode: str,
    series: Any,
) -> Any:
    """Read emitted series-point metric evidence for the matching frame.

    Temperature points are condition-sorted and therefore bind through their
    existing source index. Strain points retain the engine's frame order and
    bind positionally. No metric is recalculated or inferred here.
    """

    if series is None or mode not in {"temperature", "strain"}:
        return None
    points = (
        getattr(series, "temp_points", ())
        if mode == "temperature"
        else getattr(series, "strain_points", ())
    )
    if not isinstance(points, Sequence) or isinstance(points, (str, bytes)):
        return None
    point = None
    if mode == "temperature":
        for candidate in points:
            try:
                source_index = int(getattr(candidate, "source_index"))
            except (AttributeError, TypeError, ValueError):
                continue
            if source_index == int(frame.index):
                point = candidate
                break
    elif 0 <= int(frame.index) < len(points):
        point = points[int(frame.index)]
    value = getattr(point, "metric_evidence", None) if point is not None else None
    if value not in ({}, None, ()):
        return value
    return None


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
    metric_evidence = _series_frame_metric_evidence(
        frame,
        mode=mode,
        series=series,
    )
    if metric_evidence in ({}, None, ()):
        metric_evidence = _first_frame_value(frame, "metric_evidence")
    record: dict[str, Any] = {
        "frame_index": int(frame.index),
        "condition": _json_safe(frame.condition),
        "source_path": str(frame.source_path or ""),
        "metric_evidence": _project_metric_collection(
            metric_evidence
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

    resolution = payload.get("saxs_candidate_reference_resolution")
    if isinstance(resolution, Mapping):
        resolution_record = _project_mapping(resolution, _AI_REFERENCE_FIELDS)
        resolved_ids = [
            str(item.get("candidate_id") or "").strip()
            for item in resolution.get("resolved", ())
            if isinstance(item, Mapping) and str(item.get("candidate_id") or "").strip()
        ]
        if resolved_ids:
            resolution_record["resolved_candidate_ids"] = resolved_ids
        if resolution_record:
            projected["candidate_reference_resolution"] = resolution_record

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
    scientific_review: Mapping[str, Any] | None = None,
    scientific_review_scope: str = "saxs.1d",
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
    if isinstance(scientific_review, Mapping):
        payload["scientific_review"] = build_saxs_review_evidence(
            scientific_review,
            tuple(frame for frame in frames if isinstance(frame, SAXSFrameView)),
            expected_scope=scientific_review_scope,
        )
    return _json_safe(payload)


def _definition_uses_2d_review(definition: FigureDefinition) -> bool:
    """Identify existing detector/orientation recipes without inference."""

    figure_id = str(definition.figure_id or "")
    recipe = definition.recipe if isinstance(definition.recipe, Mapping) else {}
    parameters = recipe.get("parameters", {})
    parameters = parameters if isinstance(parameters, Mapping) else {}
    return bool(
        recipe.get("source_capability") == "detector_2d"
        or parameters.get("source_capability") == "detector_2d"
        or figure_id.endswith(".2d")
        or figure_id.endswith(".azimuthal")
    )


def attach_saxs_figure_evidence(
    definitions: Sequence[FigureDefinition],
    frames: Sequence[SAXSFrameView],
    *,
    mode: str,
    series: Any = None,
    ai_rescue: Mapping[str, Any] | None = None,
    acceptance_audit: Mapping[str, Any] | None = None,
    scientific_review: Mapping[str, Any] | None = None,
) -> tuple[FigureDefinition, ...]:
    """Merge quality provenance into recipes without changing figure roles."""

    try:
        provenance = build_saxs_figure_evidence(
            frames,
            mode=mode,
            series=series,
            ai_rescue=ai_rescue,
            acceptance_audit=acceptance_audit,
            scientific_review=scientific_review,
            scientific_review_scope="saxs.1d",
        )
        two_d_provenance = (
            build_saxs_figure_evidence(
                frames,
                mode=mode,
                series=series,
                ai_rescue=ai_rescue,
                acceptance_audit=acceptance_audit,
                scientific_review=scientific_review,
                scientific_review_scope="saxs.2d",
            )
            if isinstance(scientific_review, Mapping)
            and any(_definition_uses_2d_review(item) for item in definitions)
            else None
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
        two_d_provenance = None
    attached: list[FigureDefinition] = []
    for definition in definitions:
        recipe = dict(definition.recipe)
        evidence = recipe.get("evidence", {})
        evidence_mapping = dict(evidence) if isinstance(evidence, Mapping) else {}
        evidence_mapping["quality_provenance"] = (
            two_d_provenance
            if two_d_provenance is not None
            and _definition_uses_2d_review(definition)
            else provenance
        )
        recipe["evidence"] = evidence_mapping
        attached.append(replace(definition, recipe=recipe))
    return tuple(attached)


def _safe_manifest_document_path(manifest_path: Path, value: Any) -> Path | None:
    """Resolve one manifest-owned POSIX document path without path guessing."""

    text = str(value or "")
    if not text or "\\" in text:
        return None
    posix_path = PurePosixPath(text)
    windows_path = PureWindowsPath(text)
    if (
        posix_path.is_absolute()
        or windows_path.is_absolute()
        or ".." in posix_path.parts
        or posix_path.as_posix() != text
    ):
        return None
    root = manifest_path.parent.resolve()
    candidate = (root / posix_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def _document_uses_2d_review(document: Mapping[str, Any], figure_id: Any) -> bool:
    """Classify a persisted detector/orientation recipe without inference."""

    recipe = document.get("recipe", {})
    recipe = recipe if isinstance(recipe, Mapping) else {}
    parameters = recipe.get("parameters", {})
    parameters = parameters if isinstance(parameters, Mapping) else {}
    figure_text = str(figure_id or "")
    return bool(
        recipe.get("source_capability") == "detector_2d"
        or parameters.get("source_capability") == "detector_2d"
        or figure_text.endswith(".2d")
        or figure_text.endswith(".azimuthal")
    )


def _atomic_write_figure_document(path: Path, document: Mapping[str, Any]) -> None:
    """Persist one Figure document without exposing a half-written JSON file."""

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(document, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def sync_saxs_review_evidence_to_existing_figures(
    manifest_path: str | Path,
    frames: Sequence[SAXSFrameView],
    review_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Refresh review provenance in ready documents selected by a manifest.

    The structural manifest is read but never rewritten. Only the detached
    ``scientific_review`` field under an existing Figure provenance payload is
    changed; all frame, metric, role, revision, and source fields remain owned
    by the already-published document.
    """

    path = Path(manifest_path)
    report: dict[str, Any] = {
        "status": "ok",
        "updated_count": 0,
        "skipped_count": 0,
        "reason_codes": [],
    }

    def skip(reason: str) -> None:
        report["skipped_count"] += 1
        if reason not in report["reason_codes"]:
            report["reason_codes"].append(reason)

    if not path.is_file():
        report["status"] = "skipped"
        skip("manifest_missing")
        return report
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        report["status"] = "skipped"
        skip("manifest_unreadable")
        return report
    entries = manifest.get("figures") if isinstance(manifest, Mapping) else None
    if not isinstance(entries, list):
        report["status"] = "skipped"
        skip("manifest_figures_missing")
        return report

    for entry in entries:
        if not isinstance(entry, Mapping) or str(entry.get("status") or "") != "ready":
            continue
        document_path = _safe_manifest_document_path(path, entry.get("document"))
        if document_path is None:
            skip("document_path_invalid")
            continue
        if not document_path.is_file():
            skip("document_missing")
            continue
        try:
            document = json.loads(document_path.read_text(encoding="utf-8"))
            if not isinstance(document, dict):
                skip("document_invalid")
                continue
            recipe = document.get("recipe")
            evidence = recipe.get("evidence") if isinstance(recipe, dict) else None
            provenance = (
                evidence.get("quality_provenance")
                if isinstance(evidence, dict)
                else None
            )
            if not isinstance(provenance, dict):
                skip("review_provenance_missing")
                continue
            projected = build_saxs_review_evidence(
                review_payload,
                tuple(frame for frame in frames if isinstance(frame, SAXSFrameView)),
                expected_scope=(
                    "saxs.2d"
                    if _document_uses_2d_review(document, entry.get("figure_id"))
                    else "saxs.1d"
                ),
            )
            provenance["scientific_review"] = projected
            _atomic_write_figure_document(document_path, document)
            report["updated_count"] += 1
        except (OSError, TypeError, ValueError):
            skip("document_sync_failed")

    if report["skipped_count"] and not report["updated_count"]:
        report["status"] = "skipped"
    return report


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
    "build_saxs_review_evidence",
    "build_saxs_1d_review_evidence",
    "build_saxs_2d_review_evidence",
    "configured_saxs_1d_review",
    "configured_saxs_review_evidence",
    "existing_saxs_acceptance_audit",
    "sync_saxs_review_evidence_to_existing_figures",
]
