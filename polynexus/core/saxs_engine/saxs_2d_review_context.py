"""Detached reviewer context for existing SAXS 2D evidence."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
from typing import Any

from ..scientific_review import (
    review_decision_snapshot,
    review_record_from_payload,
)


_EXPECTED_SCOPE = "saxs.2d"
_LEVELS = frozenset({"Quantitative", "Trend", "Diagnostic", "Unusable"})
_RAW_KEYS = frozenset(
    {
        "q",
        "i",
        "raw_q",
        "raw_i",
        "q_values",
        "intensity_values",
        "detector_pixels",
        "pixel_values",
        "pixels",
        "image",
        "source_path",
        "source_paths",
        "source_file",
        "file_path",
        "filepath",
    }
)
_DETECTOR_FIELDS = (
    "level",
    "source_kind",
    "shape",
    "pixel_count",
    "valid_pixel_count",
    "coverage_fraction",
    "saturation_detection_available",
    "beam_center_available",
    "reason_codes",
)
_ORIENTATION_FIELDS = (
    "metric_name",
    "level",
    "applicable",
    "unit",
    "uncertainty",
    "source_ref",
    "data_quality_ref",
    "reason_codes",
)
_ORIENTATION_FIT_FIELDS = frozenset(
    {
        "f_herman",
        "f_herman_raw",
        "P2",
        "P4",
        "anisotropy_ratio",
        "anisotropy_index",
        "confidence",
        "orientation_axis_deg",
        "orientation_axis_source",
        "orientation_axis_strength",
        "orientation_axis_confidence",
        "orientation_harmonic_significance",
        "orientation_effective_bins",
        "orientation_azimuthal_coverage",
        "orientation_axis_drift_deg",
        "pattern_type",
        "method_used",
    }
)
_ORIENTATION_CHECK_FIELDS = frozenset(
    {
        "detector_source_kind",
        "detector_quality_level",
        "detector_coverage_fraction",
        "detector_saturation_detection_available",
        "detector_beam_center_available",
        "applicability_supported",
        "orientation_metrics_present",
        "orientation_reliability_status",
        "orientation_reliability_reason_codes",
    }
)
_AUDIT_FIELDS = (
    "status",
    "automated_validation_passed",
    "existing_publication_gate",
    "evidence_levels",
    "provenance_validity",
    "physical_gate_evidence",
    "method_gate_status",
    "reliability",
    "reason_codes",
    "audit_scope",
    "publication_decision_changed",
    "detector_provenance_audit",
)
_REVIEW_DECISION_FIELDS = (
    "allowed",
    "reason",
    "record_id",
    "scope",
    "policy_version",
    "source_ref",
)
_REVIEW_RECORD_DECISION_FIELDS = (
    "geometry_reference",
    "beam_center_policy",
    "mask_policy",
    "saturation_policy",
    "orientation_applicability",
    "promotion_rule",
)
_PROVENANCE_FIELDS = ("validity", "source", "field_sources", "missing_field_sources")
_MASK_PROVENANCE_FIELDS = ("validity", "source", "configured", "shape", "shape_matches_detector")
_BEAM_CENTER_FIELDS = ("status", "available")
_DETECTOR_CONTEXT_FIELDS = frozenset((*_DETECTOR_FIELDS, "status"))
_ORIENTATION_CONTEXT_FIELDS = frozenset((*_ORIENTATION_FIELDS, "fit_evidence", "physical_checks", "status"))
_GATE_CONTEXT_FIELDS = frozenset(
    {
        "audit_status",
        "automated_validation_passed",
        "quality_gate_status",
        "physical_gate_status",
        *_AUDIT_FIELDS,
    }
)
_REVIEW_CONTEXT_FIELDS = frozenset({"status", "scope", "decision", "record"})
_REVIEW_RECORD_FIELDS = (
    "record_id",
    "scope",
    "reviewer",
    "reviewed_at",
    "policy_version",
    "status",
    "conditions",
    "decisions",
)
_ADVISORY_CANDIDATE_FIELDS = (
    "candidate_id", "feature_kind", "q_min_nm1", "q_max_nm1", "q_center_nm1",
    "f_reference", "f_principal_raw", "reference_axis_kind", "reference_axis_deg",
    "level", "reason_codes",
)
_ADVISORY_TRACK_FIELDS = (
    "track_id", "feature_kind", "convention", "reference_axis_kind",
    "reference_axis_deg", "reliability_status", "reason_codes",
)
_ADVISORY_OBSERVATION_FIELDS = (
    "candidate_id", "condition_value", "q_range_nm1", "q_center_nm1",
    "f_reference", "f_principal_raw", "delta_f_from_zero",
    "delta_stability_interval", "reliability_status", "reason_codes",
)
_ADVISORY_LEDGER_FIELDS = (
    "operation", "status", "input_digest", "output_digest", "reason_codes",
)


def _mapping_value(source: Any, name: str, default: Any = None) -> Any:
    if isinstance(source, Mapping):
        return source.get(name, default)
    return getattr(source, name, default)


def _owner(source: Any) -> Any:
    if isinstance(source, Mapping):
        return source
    result = getattr(source, "result", None)
    return result if result is not None else source


def _parameters(source: Any) -> Mapping[str, Any]:
    owner = _owner(source)
    parameters = _mapping_value(owner, "parameters", None)
    return parameters if isinstance(parameters, Mapping) else {}


def _read(source: Any, parameters: Mapping[str, Any], name: str) -> Any:
    if name in parameters:
        return parameters[name]
    return _mapping_value(_owner(source), name, None)


def _raw_key(name: Any) -> bool:
    normalized = str(name).strip().lower()
    if normalized in _RAW_KEYS:
        return True
    return any(token in normalized for token in ("path", "filepath", "pixels"))


def _safe(value: Any, *, depth: int = 0) -> Any:
    """Copy only JSON-safe values while dropping known raw-data fields."""

    if depth > 8:
        return None
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    enum_value = getattr(value, "value", None)
    if enum_value is not None and enum_value is not value:
        return _safe(enum_value, depth=depth + 1)
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return _safe(item(), depth=depth + 1)
        except (TypeError, ValueError, OverflowError):
            return None
    if isinstance(value, Mapping):
        return {
            str(key): _safe(item, depth=depth + 1)
            for key, item in value.items()
            if not _raw_key(key)
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_safe(item, depth=depth + 1) for item in value]
    return None


def _text(value: Any) -> str:
    safe = _safe(value)
    return safe.strip() if isinstance(safe, str) else ""


def _level(value: Any) -> str:
    value_text = _text(value)
    return value_text if value_text in _LEVELS else ""


def _reason_codes(value: Any) -> list[str]:
    if isinstance(value, str):
        values = (value,)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        values = value
    else:
        values = ()
    return list(dict.fromkeys(str(item).strip() for item in values if str(item).strip()))


def _safe_identifier(value: Any) -> str:
    text = _text(value)
    if not text or "/" in text or "\\" in text or ":" in text:
        return ""
    return text


def _optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _fixed_fields(value: Any, fields: Sequence[str]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return {field: _safe(value[field]) for field in fields if field in value and not _raw_key(field)}


def _sanitize_provenance(value: Any, *, kind: str) -> dict[str, Any]:
    source = value if isinstance(value, Mapping) else {}
    fields = _MASK_PROVENANCE_FIELDS if kind == "mask" else _PROVENANCE_FIELDS
    result = _fixed_fields(source, fields)
    if "source" in result:
        result["source"] = _safe_identifier(source.get("source")) or None
    if kind == "geometry":
        field_sources = source.get("field_sources")
        result["field_sources"] = (
            {
                str(key): _safe_identifier(item) or None
                for key, item in field_sources.items()
                if not _raw_key(key)
            }
            if isinstance(field_sources, Mapping)
            else {}
        )
        result["missing_field_sources"] = _reason_codes(source.get("missing_field_sources"))
    return result


def sanitize_saxs_2d_review_context(value: Any) -> dict[str, Any]:
    """Keep only the fixed, summary-only 2D DTO at the prompt boundary."""

    if not isinstance(value, Mapping):
        return {}
    if (
        value.get("schema_version") != "saxs-2d-review-v1"
        or str(value.get("technique", "")).upper() != "SAXS"
        or value.get("scope") != _EXPECTED_SCOPE
    ):
        return {}
    nested_fields = (
        "detector",
        "geometry",
        "mask",
        "beam_center",
        "orientation",
        "gates",
        "scientific_review",
    )
    if any(not isinstance(value.get(field), Mapping) for field in nested_fields):
        return {}

    context: dict[str, Any] = {
        "schema_version": "saxs-2d-review-v1",
        "technique": "SAXS",
        "scope": _EXPECTED_SCOPE,
        "status": _text(value.get("status")) or "unavailable",
        "reason_codes": _reason_codes(value.get("reason_codes")),
        "detector": _fixed_fields(
            value.get("detector"),
            tuple(_DETECTOR_CONTEXT_FIELDS),
        ),
        "geometry": _sanitize_provenance(value.get("geometry"), kind="geometry"),
        "mask": _sanitize_provenance(value.get("mask"), kind="mask"),
        "beam_center": _fixed_fields(value.get("beam_center"), _BEAM_CENTER_FIELDS),
        "orientation": _fixed_fields(
            value.get("orientation"),
            tuple(_ORIENTATION_CONTEXT_FIELDS),
        ),
        "gates": _fixed_fields(value.get("gates"), tuple(_GATE_CONTEXT_FIELDS)),
        "scientific_review": _fixed_fields(
            value.get("scientific_review"),
            tuple(_REVIEW_CONTEXT_FIELDS),
        ),
        "raw_profile_included": False,
        "raw_detector_data_included": False,
    }
    review = value.get("scientific_review")
    if isinstance(review, Mapping):
        decision = _fixed_fields(review.get("decision"), _REVIEW_DECISION_FIELDS)
        record = _fixed_fields(review.get("record"), _REVIEW_RECORD_FIELDS)
        if decision:
            context["scientific_review"]["decision"] = decision
        if record:
            record_decisions = record.get("decisions")
            if isinstance(record_decisions, Mapping):
                record["decisions"] = _fixed_fields(record_decisions, _REVIEW_RECORD_DECISION_FIELDS)
            context["scientific_review"]["record"] = record
    advisory_sources = value.get("orientation_advisory_sources")
    if isinstance(advisory_sources, Mapping):
        context["orientation_advisory_sources"] = _sanitize_orientation_advisory_sources(
            advisory_sources
        )
    return _safe(context)


def _object_payload(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    if hasattr(value, "to_dict"):
        payload = value.to_dict()
        return payload if isinstance(payload, Mapping) else {}
    return {}


def _advisory_candidate_projection(value: Any) -> dict[str, Any]:
    source = _object_payload(value)
    result = _fixed_fields(source, _ADVISORY_CANDIDATE_FIELDS)
    result["candidate_id"] = _safe_identifier(source.get("candidate_id")) or None
    result["reason_codes"] = _reason_codes(source.get("reason_codes"))
    return result if result.get("candidate_id") else {}


def _advisory_track_projection(value: Any) -> dict[str, Any]:
    source = _object_payload(value)
    result = _fixed_fields(source, _ADVISORY_TRACK_FIELDS)
    result["track_id"] = _safe_identifier(source.get("track_id")) or None
    result["reason_codes"] = _reason_codes(source.get("reason_codes"))
    observations = []
    for item in source.get("observations", ()):
        observation = _object_payload(item)
        projected = _fixed_fields(observation, _ADVISORY_OBSERVATION_FIELDS)
        projected["candidate_id"] = _safe_identifier(observation.get("candidate_id")) or None
        projected["reason_codes"] = _reason_codes(observation.get("reason_codes"))
        if projected["candidate_id"]:
            observations.append(projected)
    result["observations"] = observations
    return result if result.get("track_id") else {}


def _sanitize_orientation_advisory_sources(value: Mapping[str, Any]) -> dict[str, Any]:
    candidates = [
        item for item in (_advisory_candidate_projection(raw) for raw in value.get("q_band_candidates", ()))
        if item
    ]
    tracks = [
        item for item in (_advisory_track_projection(raw) for raw in value.get("tracks", ()))
        if item
    ]
    ledger = []
    for item in value.get("correction_ledger", ()):
        source = _object_payload(item)
        projected = _fixed_fields(source, _ADVISORY_LEDGER_FIELDS)
        projected["reason_codes"] = _reason_codes(source.get("reason_codes"))
        if projected.get("operation") and projected.get("status"):
            ledger.append(projected)
    return {
        "q_band_candidates": candidates,
        "tracks": tracks,
        "correction_ledger": ledger,
        "reliability_status": _text(value.get("reliability_status")) or "unavailable",
        "reason_codes": _reason_codes(value.get("reason_codes")),
    }


def _project_provenance(value: Any, *, kind: str) -> dict[str, Any]:
    source = value if isinstance(value, Mapping) else {}
    validity = _text(source.get("validity")).lower() or "not_assessed"
    payload: dict[str, Any] = {
        "validity": validity,
        "source": _safe_identifier(source.get("source")) or None,
    }
    if kind == "geometry":
        field_sources = source.get("field_sources")
        payload["field_sources"] = (
            {
                str(key): _safe_identifier(item) or None
                for key, item in field_sources.items()
                if not _raw_key(key)
            }
            if isinstance(field_sources, Mapping)
            else {}
        )
        payload["missing_field_sources"] = _reason_codes(source.get("missing_field_sources"))
    else:
        payload["configured"] = _optional_bool(source.get("configured"))
        shape = source.get("shape")
        payload["shape"] = _safe(shape) if isinstance(shape, (list, tuple)) else None
        payload["shape_matches_detector"] = _optional_bool(source.get("shape_matches_detector"))
    return payload


def _project_detector(value: Any) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[str]]:
    if not isinstance(value, Mapping):
        return (
            {"status": "unavailable", "reason_codes": ["detector_quality_missing"]},
            _project_provenance(None, kind="geometry"),
            _project_provenance(None, kind="mask"),
            ["detector_quality_missing"],
        )
    level = _level(value.get("level"))
    report = {
        key: _safe(value.get(key))
        for key in _DETECTOR_FIELDS
        if key in value and not _raw_key(key)
    }
    report["level"] = level or None
    report["reason_codes"] = _reason_codes(value.get("reason_codes"))
    report["status"] = {
        "Quantitative": "trend",
        "Trend": "trend",
        "Diagnostic": "diagnostic",
        "Unusable": "unusable",
    }.get(level, "unavailable")
    geometry = _project_provenance(value.get("geometry_provenance"), kind="geometry")
    mask = _project_provenance(value.get("mask_provenance"), kind="mask")
    reasons = list(report["reason_codes"])
    if "geometry_provenance" not in value:
        reasons.append("geometry_provenance_missing")
    if "mask_provenance" not in value:
        reasons.append("mask_provenance_missing")
    return report, geometry, mask, list(dict.fromkeys(reasons))


def _project_orientation(value: Any) -> tuple[dict[str, Any], list[str]]:
    if not isinstance(value, Mapping):
        return {"status": "unavailable", "reason_codes": ["orientation_evidence_missing"]}, [
            "orientation_evidence_missing"
        ]
    level = _level(value.get("level"))
    evidence = {
        key: _safe(value.get(key))
        for key in _ORIENTATION_FIELDS
        if key in value and key != "source_ref"
    }
    evidence["level"] = level or None
    evidence["source_ref"] = _safe_identifier(value.get("source_ref")) or None
    evidence["reason_codes"] = _reason_codes(value.get("reason_codes"))
    fit = value.get("fit_evidence")
    evidence["fit_evidence"] = (
        {str(key): _safe(item) for key, item in fit.items() if key in _ORIENTATION_FIT_FIELDS}
        if isinstance(fit, Mapping)
        else {}
    )
    checks = value.get("physical_checks")
    evidence["physical_checks"] = (
        {str(key): _safe(item) for key, item in checks.items() if key in _ORIENTATION_CHECK_FIELDS}
        if isinstance(checks, Mapping)
        else {}
    )
    evidence["status"] = {
        "Quantitative": "trend",
        "Trend": "trend",
        "Diagnostic": "diagnostic",
        "Unusable": "unusable",
    }.get(level, "unavailable")
    return evidence, list(evidence["reason_codes"])


def _project_audit(value: Any, source: Any, parameters: Mapping[str, Any]) -> dict[str, Any]:
    audit = value if isinstance(value, Mapping) else {}
    gates: dict[str, Any] = {
        "audit_status": _text(audit.get("status")) or "unavailable",
        "automated_validation_passed": _optional_bool(audit.get("automated_validation_passed")),
        "quality_gate_status": _safe(_read(source, parameters, "quality_gate_status")),
        "physical_gate_status": _safe(_read(source, parameters, "physical_gate_status")),
    }
    for key in _AUDIT_FIELDS:
        if key in audit and key != "status":
            gates[key] = _safe(audit[key])
    if not audit:
        gates["reason_codes"] = ["scientific_acceptance_audit_missing"]
    return gates


def _existing_decision(value: Mapping[str, Any], *, source_ref: str) -> dict[str, Any]:
    scope = _text(value.get("scope")) or _EXPECTED_SCOPE
    reason = _text(value.get("reason")) or "review_missing"
    allowed = bool(value.get("allowed"))
    supplied_source = _text(value.get("source_ref"))
    if scope != _EXPECTED_SCOPE:
        allowed = False
        reason = "scope_mismatch"
    elif source_ref and supplied_source != source_ref:
        allowed = False
        reason = "source_mismatch"
    elif not allowed:
        reason = reason or "review_missing"
    return {
        key: (_safe_identifier(value.get(key)) if key == "source_ref" else _safe(value.get(key)))
        for key in _REVIEW_DECISION_FIELDS
        if key in value and key != "source_ref"
    } | {
        "source_ref": _safe_identifier(supplied_source) or None,
        "allowed": allowed,
        "reason": reason,
        "scope": scope,
    }


def _review_record_projection(record: Any) -> dict[str, Any]:
    try:
        payload = record.to_dict() if hasattr(record, "to_dict") else {}
    except (TypeError, ValueError):
        return {}
    if not isinstance(payload, Mapping):
        return {}
    return {
        "record_id": _safe_identifier(payload.get("record_id")) or None,
        "scope": _text(payload.get("scope")) or None,
        "reviewer": _text(payload.get("reviewer")) or None,
        "reviewed_at": _text(payload.get("reviewed_at")) or None,
        "policy_version": _text(payload.get("policy_version")) or None,
        "status": _text(payload.get("status")) or None,
        "conditions": _safe(payload.get("conditions")) or [],
        "decisions": {
            key: _safe(payload.get("decisions", {}).get(key))
            for key in _REVIEW_RECORD_DECISION_FIELDS
            if isinstance(payload.get("decisions"), Mapping) and key in payload["decisions"]
        },
    }


def _project_review(
    value: Any,
    *,
    source_ref: str,
) -> tuple[dict[str, Any], list[str]]:
    if value is None:
        decision = {
            "allowed": False,
            "reason": "review_missing",
            "record_id": "",
            "scope": _EXPECTED_SCOPE,
            "policy_version": "",
            "source_ref": _safe_identifier(source_ref) or None,
        }
        return {"status": "review_missing", "scope": _EXPECTED_SCOPE, "decision": decision}, [
            "review_missing"
        ]

    record = review_record_from_payload(value)
    if record is not None:
        decision = review_decision_snapshot(
            record,
            expected_scope=_EXPECTED_SCOPE,
            source_ref=source_ref,
        )
        projected = {
            "status": "accepted" if decision["allowed"] else decision["reason"],
            "scope": _EXPECTED_SCOPE,
            "decision": _existing_decision(decision, source_ref=source_ref),
            "record": _review_record_projection(record),
        }
        reasons = [] if decision["allowed"] else [str(decision["reason"])]
        return projected, reasons

    if isinstance(value, Mapping) and (
        "allowed" in value or "reason" in value or "record_id" in value
    ):
        decision = _existing_decision(value, source_ref=source_ref)
        return {
            "status": "accepted" if decision["allowed"] else decision["reason"],
            "scope": decision["scope"],
            "decision": decision,
        }, [] if decision["allowed"] else [decision["reason"]]

    decision = {
        "allowed": False,
        "reason": "review_invalid",
        "record_id": "",
        "scope": _EXPECTED_SCOPE,
        "policy_version": "",
        "source_ref": _safe_identifier(source_ref) or None,
    }
    return {"status": "review_invalid", "scope": _EXPECTED_SCOPE, "decision": decision}, [
        "review_invalid"
    ]


def _envelope_status(levels: Sequence[str], *, evidence_present: bool, review_allowed: bool) -> str:
    if not evidence_present:
        return "unavailable"
    if "Unusable" in levels:
        status = "unusable"
    elif "Diagnostic" in levels:
        status = "diagnostic"
    elif any(level in {"Trend", "Quantitative"} for level in levels):
        status = "trend"
    else:
        status = "unavailable"
    return "review_required" if status not in {"unavailable", "unusable"} and not review_allowed else status


def build_saxs_2d_review_context(
    source: Any,
    *,
    source_ref: str = "",
    scientific_review: Any = None,
) -> dict[str, Any]:
    """Project existing SAXS 2D evidence without performing analysis."""

    parameters = _parameters(source)
    detector_value = _read(source, parameters, "detector_quality_report")
    orientation_value = _read(source, parameters, "orientation_evidence")
    q_resolved_value = _read(source, parameters, "q_resolved_orientation_evidence")
    tracking_value = _read(source, parameters, "orientation_sequence_evidence")
    detector, geometry, mask, detector_reasons = _project_detector(detector_value)
    orientation, orientation_reasons = _project_orientation(orientation_value)
    review_value = scientific_review
    if review_value is None:
        review_value = _read(source, parameters, "scientific_review_record")
    if review_value is None:
        review_value = _read(source, parameters, "scientific_review")
    review, review_reasons = _project_review(review_value, source_ref=source_ref)
    audit = _project_audit(
        _read(source, parameters, "scientific_acceptance_audit"),
        source,
        parameters,
    )
    levels = [
        level
        for level in (_level(detector.get("level")), _level(orientation.get("level")))
        if level
    ]
    evidence_present = bool(levels)
    reasons = list(dict.fromkeys(detector_reasons + orientation_reasons + review_reasons))
    status = _envelope_status(
        levels,
        evidence_present=evidence_present,
        review_allowed=bool(review["decision"].get("allowed")),
    )
    q_resolved = _object_payload(q_resolved_value)
    tracking = _object_payload(tracking_value)
    advisory_sources = _sanitize_orientation_advisory_sources({
        "q_band_candidates": q_resolved.get("q_band_candidates", ()),
        "correction_ledger": q_resolved.get("correction_ledger", ()),
        "tracks": tracking.get("tracks", ()),
        "reliability_status": tracking.get("level", q_resolved.get("reliability_status")),
        "reason_codes": [
            *(_reason_codes(q_resolved.get("reason_codes"))),
            *(_reason_codes(tracking.get("reason_codes"))),
        ],
    })
    return {
        "schema_version": "saxs-2d-review-v1",
        "technique": "SAXS",
        "scope": _EXPECTED_SCOPE,
        "status": status,
        "reason_codes": reasons,
        "detector": detector,
        "geometry": geometry,
        "mask": mask,
        "beam_center": {
            "status": (
                "available"
                if detector.get("beam_center_available") is True
                else "invalid"
                if "beam_center_invalid" in detector.get("reason_codes", [])
                else "not_assessed"
            ),
            "available": detector.get("beam_center_available"),
        },
        "orientation": orientation,
        "gates": audit,
        "scientific_review": review,
        "orientation_advisory_sources": advisory_sources,
        "raw_profile_included": False,
        "raw_detector_data_included": False,
    }


__all__ = ["build_saxs_2d_review_context", "sanitize_saxs_2d_review_context"]
