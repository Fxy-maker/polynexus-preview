"""Read-only, evidence-bound AI advisory for SAXS orientation review."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import re
from types import MappingProxyType
from typing import Any, Mapping, Sequence

import numpy as np

from .saxs_2d_review_context import sanitize_saxs_2d_review_context


CONTEXT_SCHEMA = "saxs-orientation-advisory-context-v1"
RESPONSE_SCHEMA = "saxs-orientation-advisory-response-v1"
RATIONALE_CODES = frozenset({
    "stable_common_q_support",
    "wide_stability_bound",
    "artifact_sensitivity_present",
    "reference_axis_missing",
    "calibration_unavailable",
    "systematic_harmonic_suspected",
    "local_evidence_diagnostic",
})
REVIEW_ACTION_CODES = frozenset({
    "inspect_q_band",
    "verify_tensile_axis",
    "acquire_background_standard",
    "inspect_beam_center",
    "compare_mask_sensitivity",
    "request_scientific_review",
})
_CANDIDATE_FIELDS = (
    "candidate_id", "track_id", "feature_kind", "q_min_nm1", "q_max_nm1",
    "q_center_nm1", "f_reference", "f_principal_raw", "delta_f_from_zero",
    "stability_interval", "sensitivity_summary", "reference_axis_kind",
    "reference_axis_deg", "convention", "reliability_status", "reason_codes",
)
_LEDGER_FIELDS = (
    "operation", "status", "input_digest", "output_digest", "reason_codes",
)
_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]+$")


class OrientationAdvisoryValidationError(ValueError):
    """Raised when an advisory context or model response violates its DTO."""

    def __init__(self, *reason_codes: str):
        self.reason_codes = tuple(dict.fromkeys(str(item) for item in reason_codes if item))
        super().__init__(", ".join(self.reason_codes) or "orientation_advisory_invalid")


def _value(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _safe_id(value: Any) -> str:
    text = str(value or "").strip()
    return text if _ID_PATTERN.fullmatch(text) else ""


def _safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _safe(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe(child) for child in value]
    if isinstance(value, np.ndarray):
        return None
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return _finite(value)
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    return None


def _reasons(value: Any) -> list[str]:
    if isinstance(value, str):
        values = (value,)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        values = value
    else:
        values = ()
    return list(dict.fromkeys(str(item).strip() for item in values if str(item).strip()))


def _review_context(source: Mapping[str, Any]) -> dict[str, Any]:
    candidate = source.get("review_context", source.get("saxs_2d_review_context", source))
    if not isinstance(candidate, Mapping):
        return {}
    if candidate.get("schema_version") != "saxs-2d-review-v1":
        return {}
    return sanitize_saxs_2d_review_context(candidate)


def _candidate_sources(source: Mapping[str, Any]) -> list[Any]:
    candidates: list[Any] = []
    for key in ("candidates", "orientation_candidates", "q_band_candidates"):
        value = source.get(key)
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            candidates.extend(value)
    orientation = source.get("orientation")
    if isinstance(orientation, Mapping):
        for key in ("candidates", "q_band_candidates"):
            value = orientation.get(key)
            if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
                candidates.extend(value)
    q_evidence = source.get("q_resolved_orientation_evidence")
    if isinstance(q_evidence, Mapping):
        value = q_evidence.get("q_band_candidates")
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            candidates.extend(value)
    review = source.get("review_context", source.get("saxs_2d_review_context", {}))
    if isinstance(review, Mapping):
        advisory_sources = review.get("orientation_advisory_sources", {})
        if isinstance(advisory_sources, Mapping):
            for key in ("q_band_candidates", "tracks"):
                value = advisory_sources.get(key)
                if key == "q_band_candidates" and isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
                    candidates.extend(value)
                elif key == "tracks" and isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
                    for track in value:
                        track_id = _value(track, "track_id", "")
                        for observation in _value(track, "observations", ()) or ():
                            candidate = dict(_safe(observation) or {})
                            candidate.setdefault("track_id", track_id)
                            candidate.setdefault("feature_kind", _value(track, "feature_kind", "q_band"))
                            candidate.setdefault("convention", _value(track, "convention", ""))
                            candidate.setdefault("reference_axis_kind", _value(track, "reference_axis_kind", "unknown"))
                            candidate.setdefault("reference_axis_deg", _value(track, "reference_axis_deg"))
                            candidates.append(candidate)
    tracks = source.get("tracks", source.get("orientation_sequence", {}))
    if isinstance(tracks, Mapping):
        tracks = tracks.get("tracks", ())
    if isinstance(tracks, Sequence) and not isinstance(tracks, (str, bytes)):
        for track in tracks:
            track_id = _value(track, "track_id", "")
            observations = _value(track, "observations", ()) or ()
            for observation in observations:
                candidate = dict(_safe(observation) or {})
                candidate.setdefault("track_id", track_id)
                candidate.setdefault("feature_kind", _value(track, "feature_kind", "q_band"))
                candidate.setdefault("convention", _value(track, "convention", ""))
                candidate.setdefault("reference_axis_kind", _value(track, "reference_axis_kind", "unknown"))
                candidate.setdefault("reference_axis_deg", _value(track, "reference_axis_deg"))
                candidates.append(candidate)
    return candidates


def _project_candidate(candidate: Any, parent: Mapping[str, Any]) -> dict[str, Any] | None:
    candidate_id = _safe_id(_value(candidate, "candidate_id"))
    if not candidate_id:
        return None
    sensitivity = _value(candidate, "sensitivity_summary", parent.get("sensitivity_summary", {}))
    if not isinstance(sensitivity, Mapping):
        sensitivity = {}
    stability = _value(candidate, "stability_interval", {})
    if not isinstance(stability, Mapping):
        stability = {}
    output: dict[str, Any] = {"candidate_id": candidate_id}
    for field_name in _CANDIDATE_FIELDS[1:]:
        if field_name == "stability_interval":
            output[field_name] = {
                key: value for key in ("lower", "upper", "kind")
                if (value := _safe(stability.get(key))) is not None
            }
        elif field_name == "sensitivity_summary":
            output[field_name] = {
                key: _safe(sensitivity.get(key))
                for key in ("reliability_status", "reason_codes", "value_ranges")
                if sensitivity.get(key) is not None
            }
        elif field_name in {"track_id", "feature_kind", "reference_axis_kind", "convention", "reliability_status"}:
            output[field_name] = str(_value(candidate, field_name, "") or "")
        elif field_name == "reason_codes":
            output[field_name] = _reasons(_value(candidate, field_name, ()))
        else:
            output[field_name] = _finite(_value(candidate, field_name))
    return output


def _project_ledger(source: Mapping[str, Any]) -> list[dict[str, Any]]:
    values = source.get("correction_ledger")
    if values is None and isinstance(source.get("q_resolved_orientation_evidence"), Mapping):
        values = source["q_resolved_orientation_evidence"].get("correction_ledger")
    if values is None:
        review = source.get("review_context", source.get("saxs_2d_review_context", {}))
        if isinstance(review, Mapping):
            advisory_sources = review.get("orientation_advisory_sources", {})
            if isinstance(advisory_sources, Mapping):
                values = advisory_sources.get("correction_ledger")
    output: list[dict[str, Any]] = []
    for item in values or ():
        if not isinstance(item, Mapping):
            continue
        projected = {
            "operation": str(item.get("operation", "")),
            "status": str(item.get("status", "")),
            "input_digest": _safe(item.get("input_digest")),
            "output_digest": _safe(item.get("output_digest")),
            "reason_codes": _reasons(item.get("reason_codes", ())),
        }
        if projected["operation"] and projected["status"]:
            output.append(projected)
    return sorted(output, key=lambda item: (item["operation"], item["status"]))


def build_orientation_advisory_context(source: Any) -> dict[str, Any]:
    """Project existing orientation evidence into a fixed, detached DTO."""

    raw = source if isinstance(source, Mapping) else {}
    review = _review_context(raw)
    parent = raw.get("orientation", {}) if isinstance(raw.get("orientation"), Mapping) else {}
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in _candidate_sources(raw):
        projected = _project_candidate(item, parent)
        if projected is None or projected["candidate_id"] in seen:
            continue
        seen.add(projected["candidate_id"])
        candidates.append(projected)
    candidates.sort(key=lambda item: item["candidate_id"])
    eligible = [
        item for item in candidates
        if str(item.get("reliability_status", "")).lower() not in {"unavailable", "unusable"}
    ]
    reason_codes: list[str] = []
    if not candidates:
        reason_codes.append("orientation_advisory_candidates_missing")
    if not eligible:
        reason_codes.append("orientation_advisory_candidates_not_eligible")
    if not review:
        reason_codes.append("saxs_2d_review_context_missing")
    payload: dict[str, Any] = {
        "schema_version": CONTEXT_SCHEMA,
        "technique": "SAXS",
        "scope": "saxs.orientation.advisory",
        "status": "available" if eligible else "limited",
        "review_context": review,
        "candidates": candidates,
        "eligible_candidate_ids": [item["candidate_id"] for item in eligible],
        "correction_ledger": _project_ledger(raw),
        "gates": {
            key: _safe(raw.get("gates", {}).get(key))
            for key in ("quality_gate_status", "physical_gate_status", "publication_decision_changed")
            if isinstance(raw.get("gates"), Mapping) and key in raw["gates"]
        },
        "reason_codes": list(dict.fromkeys(reason_codes)),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    payload["source_evidence_digest"] = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return payload


@dataclass(frozen=True)
class ParsedOrientationAdvisoryResponse:
    ranked_candidate_ids: tuple[str, ...]
    candidate_rationale_codes: Mapping[str, tuple[str, ...]]
    review_action_codes: tuple[str, ...]


def parse_orientation_advisory_response(
    response: Any,
    source_context: Mapping[str, Any],
) -> ParsedOrientationAdvisoryResponse:
    if not isinstance(response, Mapping):
        raise OrientationAdvisoryValidationError("response_not_mapping")
    expected = {
        "schema_version", "source_evidence_digest", "ranked_candidate_ids",
        "candidate_rationale_codes", "review_action_codes",
    }
    reasons = [f"unknown_response_field:{key}" for key in response if key not in expected]
    if response.get("schema_version") != RESPONSE_SCHEMA:
        reasons.append("response_schema_invalid")
    if response.get("source_evidence_digest") != source_context.get("source_evidence_digest"):
        reasons.append("source_evidence_digest_mismatch")
    known = {
        str(item.get("candidate_id"))
        for item in source_context.get("candidates", ())
        if isinstance(item, Mapping)
    }
    ranked = response.get("ranked_candidate_ids")
    if not isinstance(ranked, list):
        reasons.append("ranked_candidate_ids_invalid")
        ranked = []
    ranked_ids = tuple(str(item) for item in ranked)
    if len(set(ranked_ids)) != len(ranked_ids):
        reasons.append("ranked_candidate_ids_duplicate")
    if any(item not in known for item in ranked_ids):
        reasons.append("candidate_id_unknown")
    rationale = response.get("candidate_rationale_codes")
    rationale_out: dict[str, tuple[str, ...]] = {}
    if not isinstance(rationale, Mapping):
        reasons.append("candidate_rationale_codes_invalid")
        rationale = {}
    for candidate_id, codes in rationale.items():
        if str(candidate_id) not in known:
            reasons.append("candidate_rationale_id_unknown")
            continue
        if not isinstance(codes, list) or any(str(code) not in RATIONALE_CODES for code in codes):
            reasons.append("rationale_code_invalid")
            continue
        rationale_out[str(candidate_id)] = tuple(dict.fromkeys(str(code) for code in codes))
    actions = response.get("review_action_codes")
    if not isinstance(actions, list) or any(str(code) not in REVIEW_ACTION_CODES for code in actions):
        reasons.append("review_action_code_invalid")
        actions = []
    actions_out = tuple(dict.fromkeys(str(code) for code in actions))
    if reasons:
        raise OrientationAdvisoryValidationError(*reasons)
    return ParsedOrientationAdvisoryResponse(ranked_ids, MappingProxyType(rationale_out), actions_out)


@dataclass(frozen=True)
class OrientationAdvisoryReport:
    schema_version: str
    ranked_candidate_ids: tuple[str, ...]
    candidate_observations: tuple[Mapping[str, Any], ...]
    comparison_summary_codes: tuple[str, ...]
    artifact_risk_codes: tuple[str, ...]
    recommended_review_action_codes: tuple[str, ...]
    limitation_codes: tuple[str, ...]
    source_evidence_digest: str
    status: str
    reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "ranked_candidate_ids": list(self.ranked_candidate_ids),
            "candidate_observations": [_safe(item) for item in self.candidate_observations],
            "comparison_summary_codes": list(self.comparison_summary_codes),
            "artifact_risk_codes": list(self.artifact_risk_codes),
            "recommended_review_action_codes": list(self.recommended_review_action_codes),
            "limitation_codes": list(self.limitation_codes),
            "source_evidence_digest": self.source_evidence_digest,
            "status": self.status,
            "reason_codes": list(self.reason_codes),
        }


def _source_risks(context: Mapping[str, Any]) -> tuple[str, ...]:
    risks: list[str] = []
    for item in context.get("correction_ledger", ()):
        if isinstance(item, Mapping) and str(item.get("status")) in {"unavailable", "rejected"}:
            risks.append(f"{item.get('operation')}_unavailable")
    for candidate in context.get("candidates", ()):
        if isinstance(candidate, Mapping):
            status = str(candidate.get("sensitivity_summary", {}).get("reliability_status", ""))
            if status == "artifact_sensitive":
                risks.append("orientation_sensitivity_artifact_sensitive")
    return tuple(dict.fromkeys(risks))


def build_orientation_advisory_report(
    source_context: Mapping[str, Any],
    model_response: Mapping[str, Any] | None,
) -> OrientationAdvisoryReport:
    candidates = tuple(item for item in source_context.get("candidates", ()) if isinstance(item, Mapping))
    by_id = {str(item.get("candidate_id")): item for item in candidates}
    reasons: list[str] = []
    ranked: tuple[str, ...] = ()
    response_actions: tuple[str, ...] = ()
    rationale: Mapping[str, tuple[str, ...]] = {}
    if model_response is not None:
        try:
            parsed = parse_orientation_advisory_response(model_response, source_context)
            ranked = parsed.ranked_candidate_ids
            response_actions = parsed.review_action_codes
            rationale = parsed.candidate_rationale_codes
        except OrientationAdvisoryValidationError as exc:
            reasons.extend(exc.reason_codes)
            reasons.append("advisory_response_invalid")
    else:
        reasons.append("advisory_model_unavailable")
    risks = list(_source_risks(source_context))
    comparison: list[str] = []
    if len(candidates) > 1:
        comparison.append("candidate_comparison_available")
    if ranked:
        comparison.extend(code for code in set().union(*(set(rationale.get(item, ())) for item in ranked)))
    limitations = list(source_context.get("reason_codes", ()))
    if not ranked:
        limitations.append("advisory_ranking_unavailable")
    actions: list[str] = list(response_actions)
    if candidates:
        actions.append("inspect_q_band")
    if any(not item.get("reference_axis_deg") for item in candidates):
        actions.append("verify_tensile_axis")
    if any("calibration" in risk for risk in risks):
        actions.append("acquire_background_standard")
    if risks:
        actions.append("compare_mask_sensitivity")
    if limitations:
        actions.append("request_scientific_review")
    status = "available" if ranked and source_context.get("status") == "available" and not reasons else "limited"
    observations = tuple(by_id[item] for item in ranked if item in by_id) or candidates
    return OrientationAdvisoryReport(
        schema_version="saxs-orientation-advisory-report-v1",
        ranked_candidate_ids=ranked,
        candidate_observations=observations,
        comparison_summary_codes=tuple(dict.fromkeys(comparison)),
        artifact_risk_codes=tuple(dict.fromkeys(risks)),
        recommended_review_action_codes=tuple(dict.fromkeys(actions)),
        limitation_codes=tuple(dict.fromkeys(limitations)),
        source_evidence_digest=str(source_context.get("source_evidence_digest", "")),
        status=status,
        reason_codes=tuple(dict.fromkeys(reasons)),
    )


__all__ = [
    "CONTEXT_SCHEMA",
    "RESPONSE_SCHEMA",
    "RATIONALE_CODES",
    "REVIEW_ACTION_CODES",
    "OrientationAdvisoryValidationError",
    "ParsedOrientationAdvisoryResponse",
    "OrientationAdvisoryReport",
    "build_orientation_advisory_context",
    "parse_orientation_advisory_response",
    "build_orientation_advisory_report",
]
