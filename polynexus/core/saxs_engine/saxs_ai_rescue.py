"""SAXS bridge into the shared preprocessing candidate/decision contracts.

The bridge treats model-provided intents as untrusted input.  It creates
candidate-only plans and delegates all evidence gates and automation-state
semantics to ``preprocess_optimization``; it never applies a candidate.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

import numpy as np

from ..preprocess_optimization import (
    DecisionOutcome,
    PreprocessCandidate,
    PreprocessEvidence,
    PreprocessIntent,
    PreprocessPolicy,
    generate_preprocess_candidates,
    get_preprocess_adapter,
    get_preprocess_policy,
    parse_preprocess_intent,
    stable_config_hash,
)
from ..preprocess_optimization.decision import decide_preprocess_candidate
from ..preprocess_optimization.intent_schema import ContractValidationError
from ..preprocess_optimization.policy import PolicyValidationError
from .saxs_2d_review_context import (
    build_saxs_2d_review_context,
    sanitize_saxs_2d_review_context,
)


_REQUIRED_PROTECTED_FEATURES = frozenset(
    {
        "weak_peaks",
        "integrated_area",
        "guinier_region",
        "beamstop_boundaries",
        "peak_position",
        "peak_width",
        "physical_parameters",
    }
)

_CONFIRMED_RERUN_MODES = frozenset({"static", "temperature", "strain"})
_QUALITY_LEVELS = frozenset({"Quantitative", "Trend"})
_EVIDENCE_FIELDS = (
    "data_quality_report",
    "guinier_evidence",
    "metric_evidence",
    "detector_quality_report",
    "orientation_evidence",
)
_ACCEPTANCE_AUDIT_FIELDS = (
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
_RAW_SUMMARY_KEYS = frozenset(
    {
        "q",
        "i",
        "raw_q",
        "raw_i",
        "q_values",
        "intensity_values",
        "detector_pixels",
        "pixel_values",
        "source_path",
        "source_paths",
        "source_file",
        "file_path",
        "filepath",
    }
)
_COMPACT_FIELDS = frozenset(
    {
        "level",
        "reason_codes",
        "source_id",
        "source_ref",
        "metric_name",
        "value",
        "unit",
        "uncertainty",
        "applicable",
        "fit_evidence",
        "physical_checks",
        "rg_nm",
        "rg_uncertainty_nm",
        "q_rg_max",
        "r_squared",
        "point_count",
        "frame_count",
        "valid_frame_count",
        "evidence_frame_count",
        "usable_frame_count",
        "diagnostic_frame_count",
        "unusable_frame_count",
        "missing_frame_count",
        "coverage_fraction",
        "frame_source_indices",
        "relative_change_stats",
        "source_kind",
        "shape",
        "reason_codes",
    }
)
_SEQUENCE_RESCUE_CANDIDATE_FIELDS = (
    "candidate_id",
    "kind",
    "parameters",
    "reason_codes",
    "requires_validation",
)
_SEQUENCE_RESCUE_PARAMETER_FIELDS = (
    "frame_index",
    "axis_name",
    "axis_value",
    "metric",
    "original_value_nm",
    "proposed_value_nm",
    "proposed_source",
    "path_status",
    "preserve_missing_frames",
    "apply_mode",
)


def _json_safe(value: Any) -> Any:
    """Return a detached value accepted by ``json.dumps(..., allow_nan=False)``."""

    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, (float, np.floating)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, np.ndarray)):
        return [_json_safe(item) for item in value]
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        try:
            return _json_safe(to_dict())
        except (TypeError, ValueError):
            return None
    return str(value)


def _object_value(source: Any, name: str, default: Any = None) -> Any:
    if isinstance(source, Mapping):
        return source.get(name, default)
    return getattr(source, name, default)


def _mode_result(result: Any, mode: str) -> Any:
    if mode == "temperature":
        series = _object_value(result, "_temperature_result", None)
        if series is not None:
            return series
    elif mode == "strain":
        series = _object_value(result, "_strain_result", None)
        if series is not None:
            return series
    wrapped = _object_value(result, "result", None)
    return wrapped if wrapped is not None else result


def _summary_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _summary_safe(item)
            for key, item in value.items()
            if str(key).strip().lower() not in _RAW_SUMMARY_KEYS
        }
    if isinstance(value, (list, tuple, set, np.ndarray)):
        return [_summary_safe(item) for item in value]
    return _json_safe(value)


def _acceptance_audit_projection(source: Any) -> dict[str, Any]:
    if not isinstance(source, Mapping):
        return {}
    projected = {
        str(key): _summary_safe(source[key])
        for key in _ACCEPTANCE_AUDIT_FIELDS
        if key in source
    }
    return _json_safe(projected)


def _existing_acceptance_audit(result: Any) -> dict[str, Any]:
    owner = _mode_result(result, "static")
    parameters = _object_value(owner, "parameters", None)
    if not isinstance(parameters, Mapping):
        return {}
    return _acceptance_audit_projection(parameters.get("scientific_acceptance_audit"))


def _existing_scientific_review(result: Any) -> Any:
    owner = _mode_result(result, "static")
    parameters = _object_value(owner, "parameters", None)
    if not isinstance(parameters, Mapping):
        return None
    for field_name in ("scientific_review_record", "scientific_review"):
        if field_name in parameters:
            return parameters[field_name]
    return None


def _compact(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        value = getattr(value, "to_dict", lambda: {})()
    if not isinstance(value, Mapping):
        return {}
    result: dict[str, Any] = {}
    for key, item in value.items():
        name = str(key)
        if name in _COMPACT_FIELDS:
            result[name] = _json_safe(item)
        elif isinstance(item, Mapping):
            nested = _compact(item)
            if nested:
                result[name] = nested
    return result


def _sequence_rescue_candidate_projection(value: Any) -> dict[str, Any]:
    """Project one existing sequence candidate without arbitrary payloads."""

    if not isinstance(value, Mapping):
        to_dict = getattr(value, "to_dict", None)
        value = to_dict() if callable(to_dict) else None
    if not isinstance(value, Mapping):
        return {}

    projected: dict[str, Any] = {}
    for field_name in _SEQUENCE_RESCUE_CANDIDATE_FIELDS:
        if field_name not in value:
            continue
        item = value[field_name]
        if field_name == "parameters":
            if not isinstance(item, Mapping):
                continue
            parameters = {
                str(key): _json_safe(item[key])
                for key in _SEQUENCE_RESCUE_PARAMETER_FIELDS
                if key in item
            }
            if parameters:
                projected[field_name] = parameters
        else:
            projected[field_name] = _json_safe(item)
    return projected


def _sequence_rescue_candidates_projection(value: Any) -> list[dict[str, Any]]:
    """Project only valid existing sequence candidates in stable order."""

    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    projected = [_sequence_rescue_candidate_projection(item) for item in value]
    return [item for item in projected if item]


def _normal_mode(mode: str) -> str:
    value = str(mode or "static").strip().lower()
    return value if value in _CONFIRMED_RERUN_MODES else ""


def _has_unacceptable_level(value: Any) -> bool:
    if isinstance(value, Mapping):
        if str(value.get("level", "") or "") in {"Diagnostic", "Unusable"}:
            return True
        return any(_has_unacceptable_level(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_has_unacceptable_level(item) for item in value)
    return False


def _has_failed_physical_check(value: Any) -> bool:
    if isinstance(value, Mapping):
        checks = value.get("physical_checks")
        if isinstance(checks, Mapping):
            for check in checks.values():
                if check is False or str(check).lower() in {"failed", "error", "rejected"}:
                    return True
        return any(_has_failed_physical_check(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_has_failed_physical_check(item) for item in value)
    return False


def _result_frames(result: Any, mode: str) -> list[Any]:
    if result is None:
        return []
    result = _mode_result(result, mode)
    if mode == "temperature":
        points = _object_value(result, "temp_points", ())
    elif mode == "strain":
        points = _object_value(result, "strain_points", ())
    else:
        points = _object_value(result, "frames", None)
        if points is None:
            points = [result]
    if isinstance(points, (str, bytes)):
        return []
    try:
        return [item for item in points if item is not None]
    except TypeError:
        return []


def _frame_projection(frame: Any, index: int) -> dict[str, Any]:
    payload: dict[str, Any] = {"frame_index": index}
    for field_name in ("source_index", "temperature_C", "strain", "strain_pct"):
        value = _object_value(frame, field_name, None)
        if value is not None:
            payload[field_name] = _json_safe(value)
    for field_name in _EVIDENCE_FIELDS:
        evidence = _compact(_object_value(frame, field_name, None))
        if evidence:
            payload[field_name] = evidence
    quality_flag = _object_value(frame, "quality_flag", None)
    if quality_flag not in (None, ""):
        payload["quality_flag"] = str(quality_flag)
    q_star_valid = _object_value(frame, "Q_star_valid", None)
    if q_star_valid is not None:
        payload["Q_star_valid"] = bool(q_star_valid)
    return payload


def build_saxs_confirmed_rerun_evidence(result: Any, *, mode: str) -> dict[str, Any]:
    """Project existing SAXS evidence for one confirmed rerun.

    This adapter is deliberately non-computational: it copies compact fields
    already produced by the SAXS engine and never evaluates raw curves.
    """

    normalized_mode = _normal_mode(mode)
    if not normalized_mode:
        return {
            "mode": str(mode or ""),
            "status": "unavailable",
            "physical_gate_status": "unavailable",
            "quality_gate_status": "unavailable",
            "reason_codes": ["unsupported_mode"],
            "frames": [],
            "series": {},
        }
    mode_result = _mode_result(result, normalized_mode)
    frames = [_frame_projection(frame, index) for index, frame in enumerate(_result_frames(result, normalized_mode))]
    series: dict[str, Any] = {}
    if normalized_mode == "temperature":
        series["guinier_sequence_evidence"] = _compact(
            _object_value(mode_result, "guinier_sequence_evidence", None)
        )
        rescue_candidates = _sequence_rescue_candidates_projection(
            _object_value(mode_result, "sequence_rescue_candidates", ())
        )
        if rescue_candidates:
            series["sequence_rescue_candidates"] = rescue_candidates
    for field_name in ("metric_evidence", "detector_quality_report", "orientation_evidence"):
        evidence = _compact(_object_value(mode_result, field_name, None))
        if evidence:
            series[field_name] = evidence
    payload = {
        "mode": normalized_mode,
        "status": "available" if frames else "unavailable",
        "frames": frames,
        "series": series,
    }
    return _json_safe(payload)


def assess_saxs_confirmed_rerun(result: Any, *, mode: str) -> dict[str, Any]:
    """Apply only the existing SAXS evidence statuses to a rerun result."""

    evidence = build_saxs_confirmed_rerun_evidence(result, mode=mode)
    reasons = list(evidence.get("reason_codes", []))
    frames = evidence.get("frames", [])
    physical_failed = False
    quality_failed = False
    for source in (result,):
        flag = str(_object_value(source, "quality_flag", "") or "")
        summary = str(_object_value(source, "validation_summary", "") or "").lower()
        if (
            "ERROR" in flag
            or "FAIL" in flag.upper()
            or any(token in summary for token in ("error", "failed", "rejected"))
            or _object_value(source, "validation_passed", True) is False
            or _object_value(source, "Q_star_valid", True) is False
        ):
            physical_failed = True
        quality_flags = _object_value(source, "quality_flags", {})
        if isinstance(quality_flags, Mapping) and any(
            "error" in str(value).lower() or "fail" in str(value).lower()
            for value in quality_flags.values()
        ):
            physical_failed = True
    for frame in frames:
        flag = str(frame.get("quality_flag", "") or "")
        if "ERROR" in flag or frame.get("Q_star_valid") is False:
            physical_failed = True
            reasons.append("existing_physical_gate_failed")
        if any(_has_unacceptable_level(frame.get(field_name, {})) for field_name in _EVIDENCE_FIELDS):
            quality_failed = True
        if _has_failed_physical_check(frame):
            physical_failed = True
    if not frames:
        physical_status = "unavailable"
        quality_status = "unavailable"
        reasons.append("quality_evidence_missing")
    else:
        if physical_failed:
            reasons.append("existing_physical_gate_failed")
        physical_status = "failed" if physical_failed else "passed"
        levels = [
            str(frame.get("data_quality_report", {}).get("level", "") or "")
            for frame in frames
        ]
        series = evidence.get("series", {})
        if _has_unacceptable_level(series):
            quality_failed = True
        if any(level not in _QUALITY_LEVELS for level in levels) or quality_failed:
            quality_status = "failed"
            reasons.append("quality_evidence_not_acceptable")
        else:
            quality_status = "passed"
    accepted = bool(
        evidence.get("status") == "available"
        and physical_status == "passed"
        and quality_status == "passed"
    )
    evidence.update(
        {
            "physical_gate_status": physical_status,
            "quality_gate_status": quality_status,
            "reason_codes": list(dict.fromkeys(str(item) for item in reasons)),
            "accepted": accepted,
        }
    )
    return _json_safe(evidence)


def sanitize_saxs_ai_summary_context(payload: Any) -> dict[str, Any]:
    """Keep only the summary fields allowed to cross the SAXS prompt boundary."""

    if not isinstance(payload, Mapping) or str(payload.get("technique", "")).upper() != "SAXS":
        return {}
    raw_frames = payload.get("frames", ())
    frames = (
        [_frame_projection(item, index) for index, item in enumerate(raw_frames) if isinstance(item, Mapping)]
        if isinstance(raw_frames, Sequence) and not isinstance(raw_frames, (str, bytes))
        else []
    )
    series: dict[str, Any] = {}
    raw_series = payload.get("series")
    if isinstance(raw_series, Mapping):
        rescue_candidates = _sequence_rescue_candidates_projection(
            raw_series.get("sequence_rescue_candidates", ())
        )
        if rescue_candidates:
            series["sequence_rescue_candidates"] = rescue_candidates
    for field_name in ("guinier_sequence_evidence", *_EVIDENCE_FIELDS):
        value = raw_series.get(field_name) if isinstance(raw_series, Mapping) else None
        compact = _compact(value)
        if compact:
            series[field_name] = compact
    acceptance_audit = _acceptance_audit_projection(payload.get("scientific_acceptance_audit"))
    context = {
        "schema_version": "saxs-ai-summary-v1",
        "technique": "SAXS",
        "mode": str(payload.get("mode", "") or ""),
        "status": str(payload.get("status", "unavailable") or "unavailable"),
        "physical_gate_status": str(payload.get("physical_gate_status", "unavailable") or "unavailable"),
        "quality_gate_status": str(payload.get("quality_gate_status", "unavailable") or "unavailable"),
        "reason_codes": [str(item) for item in payload.get("reason_codes", ()) if isinstance(item, str)],
        "frames": frames,
        "series": series,
        "candidate_only": True,
        "raw_profile_included": False,
        "raw_detector_data_included": False,
        "physical_validation_required": True,
    }
    two_d_context = sanitize_saxs_2d_review_context(payload.get("saxs_2d_review_context"))
    if two_d_context:
        context["saxs_2d_review_context"] = two_d_context
    if acceptance_audit:
        context["scientific_acceptance_audit"] = acceptance_audit
    return _json_safe(context)


def build_saxs_ai_summary_context(result: Any, *, mode: str) -> dict[str, Any]:
    """Build a summary-only, strict-JSON input envelope for a future AI call.

    The envelope deliberately reuses the existing evidence projection and
    status assessment.  It never inspects or serializes raw q/I, detector
    pixels, source paths, or any other unbounded input payload.
    """

    evidence = assess_saxs_confirmed_rerun(result, mode=mode)
    normalized_mode = _normal_mode(mode)
    context = {
        "schema_version": "saxs-ai-summary-v1",
        "technique": "SAXS",
        "mode": normalized_mode or str(mode or ""),
        "status": evidence.get("status", "unavailable"),
        "physical_gate_status": evidence.get("physical_gate_status", "unavailable"),
        "quality_gate_status": evidence.get("quality_gate_status", "unavailable"),
        "reason_codes": evidence.get("reason_codes", []),
        "frames": evidence.get("frames", []),
        "series": evidence.get("series", {}),
        "candidate_only": True,
        "raw_profile_included": False,
        "raw_detector_data_included": False,
        "physical_validation_required": True,
    }
    acceptance_audit = _existing_acceptance_audit(result)
    if acceptance_audit:
        context["scientific_acceptance_audit"] = acceptance_audit
    two_d_context = build_saxs_2d_review_context(
        _mode_result(result, normalized_mode),
        scientific_review=_existing_scientific_review(result),
    )
    if two_d_context.get("status") != "unavailable":
        context["saxs_2d_review_context"] = two_d_context
    return _json_safe(context)


def validate_saxs_confirmation_report(
    report: Mapping[str, Any],
    *,
    current_config: Mapping[str, Any],
    mode: str,
) -> dict[str, Any]:
    """Validate confirmation identity before any SAXS config mutation."""

    normalized_mode = _normal_mode(mode)
    if not normalized_mode:
        raise ValueError("unsupported SAXS confirmation mode")
    if not isinstance(report, Mapping):
        raise ValueError("SAXS confirmation report must be a mapping")
    decision = report.get("preprocess_decision", {})
    if not isinstance(decision, Mapping) or decision.get("decision") != "request_confirmation":
        raise ValueError("SAXS confirmation requires request_confirmation")
    candidate_id = str(report.get("selected_candidate_id", "") or "")
    if not candidate_id:
        raise ValueError("SAXS confirmation candidate is missing")
    guards = decision.get("hard_guard_results", {})
    if not isinstance(guards, Mapping) or not guards or not all(bool(value) for value in guards.values()):
        raise ValueError("SAXS confirmation hard guard failed")
    candidates = report.get("preprocess_candidates", [])
    selected = next(
        (item for item in candidates if isinstance(item, Mapping) and str(item.get("candidate_id", "")) == candidate_id),
        None,
    ) if isinstance(candidates, Sequence) and not isinstance(candidates, (str, bytes)) else None
    if selected is None:
        raise ValueError("SAXS confirmation candidate record is missing")
    expected_hash = str(selected.get("base_config_hash", "") or "")
    current_hash = stable_config_hash(dict(current_config))
    if not expected_hash or expected_hash != current_hash:
        raise ValueError("SAXS confirmation base config hash mismatch")
    selected_config = report.get("selected_preprocess_config", {})
    config_delta = selected.get("config_delta", {})
    if not isinstance(selected_config, Mapping) or not isinstance(config_delta, Mapping):
        raise ValueError("SAXS confirmation config identity is incomplete")
    for key, value in config_delta.items():
        if key not in selected_config or selected_config.get(key) != value:
            raise ValueError("SAXS confirmation candidate config mismatch")
    return _json_safe(
        {
            "technique": "SAXS",
            "mode": normalized_mode,
            "candidate_id": candidate_id,
            "candidate_base_config_hash": expected_hash,
            "hard_guard_results": dict(guards),
        }
    )


@dataclass(frozen=True)
class SAXSConfirmedRerunAudit:
    """Detached strict-JSON audit for one confirmed SAXS transaction."""

    technique: str = "SAXS"
    mode: str = "static"
    candidate_id: str = ""
    candidate_base_config_hash: str = ""
    before_config_hash: str = ""
    after_config_hash: str = ""
    phase: str = "apply_pending"
    apply_performed: bool = False
    physical_gate_status: str = "unavailable"
    quality_gate_status: str = "unavailable"
    before_quality_evidence: dict[str, Any] | None = None
    after_quality_evidence: dict[str, Any] | None = None
    rollback_reason: str = ""
    accepted_by: str = ""
    audit_timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        from dataclasses import asdict

        payload = _json_safe(asdict(self))
        return payload if isinstance(payload, dict) else {}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, allow_nan=False)

    @classmethod
    def now(cls, **kwargs: Any) -> "SAXSConfirmedRerunAudit":
        return cls(
            audit_timestamp=datetime.now(timezone.utc).isoformat(),
            **kwargs,
        )


@dataclass(frozen=True)
class SAXSAIRescuePlan:
    """Candidate-only plan produced from a validated SAXS AI intent."""

    intent: PreprocessIntent
    candidates: tuple[PreprocessCandidate, ...]
    policy_version: str
    automation_state: str = "shadow"
    candidate_only: bool = True
    original_preserved: bool = True
    physical_validation_required: bool = True
    reason_codes: tuple[str, ...] = (
        "candidate_only",
        "original_preserved",
        "physical_validation_required",
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent.to_dict(),
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "policy_version": self.policy_version,
            "automation_state": self.automation_state,
            "candidate_only": self.candidate_only,
            "original_preserved": self.original_preserved,
            "physical_validation_required": self.physical_validation_required,
            "reason_codes": list(self.reason_codes),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, allow_nan=False)


@dataclass(frozen=True)
class SAXSAIRescueDecision:
    """Auditable wrapper around the shared preprocessing decision outcome."""

    outcome: DecisionOutcome
    original_preserved: bool = True
    physical_validation_required: bool = True
    apply_allowed: bool = False

    @property
    def decision(self) -> str:
        return self.outcome.decision

    @property
    def simulated_decision(self) -> str:
        return self.outcome.simulated_decision

    @property
    def reason_codes(self) -> tuple[str, ...]:
        return self.outcome.reason_codes

    def to_dict(self) -> dict[str, Any]:
        payload = self.outcome.to_dict()
        payload.update(
            {
                "original_preserved": self.original_preserved,
                "physical_validation_required": self.physical_validation_required,
                "apply_allowed": self.apply_allowed,
            }
        )
        return payload

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, allow_nan=False)


def _validated_intent(payload: Mapping[str, Any], policy: PreprocessPolicy) -> PreprocessIntent:
    try:
        intent = parse_preprocess_intent(dict(payload))
    except (ContractValidationError, TypeError, ValueError):
        raise
    if intent.technique.upper() != "SAXS":
        raise ContractValidationError("SAXS AI intent must use technique SAXS")
    missing = _REQUIRED_PROTECTED_FEATURES - set(intent.protected_features)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ContractValidationError(f"SAXS AI intent missing protected features: {missing_text}")
    try:
        policy.validate_intent(intent)
    except PolicyValidationError as exc:
        raise ContractValidationError(str(exc)) from exc
    return intent


def validate_saxs_ai_intent(
    intent_payload: Mapping[str, Any],
    *,
    policy: PreprocessPolicy | None = None,
) -> PreprocessIntent:
    """Validate a SAXS intent without generating or executing candidates."""

    selected_policy = policy or get_preprocess_policy("SAXS")
    if selected_policy.technique.upper() != "SAXS":
        raise PolicyValidationError("SAXS rescue requires the SAXS preprocessing policy")
    return _validated_intent(intent_payload, selected_policy)


def build_saxs_ai_rescue_plan(
    intent_payload: Mapping[str, Any],
    base_config: Mapping[str, Any],
    *,
    policy: PreprocessPolicy | None = None,
    experience_deltas: Sequence[Mapping[str, Any]] = (),
) -> SAXSAIRescuePlan:
    """Validate an AI intent and generate bounded SAXS candidates only."""

    selected_policy = policy or get_preprocess_policy("SAXS")
    intent = validate_saxs_ai_intent(intent_payload, policy=selected_policy)
    candidates = generate_preprocess_candidates(
        intent,
        dict(base_config),
        selected_policy,
        get_preprocess_adapter("SAXS"),
        experience_deltas=[dict(delta) for delta in experience_deltas],
    )
    return SAXSAIRescuePlan(
        intent=intent,
        candidates=tuple(candidates),
        policy_version=selected_policy.policy_version,
        automation_state=selected_policy.automation_state,
    )


def assess_saxs_ai_candidate(
    evidence: PreprocessEvidence,
    *,
    candidate_margin: float,
    metadata_complete: bool,
    automation_state: str | None = None,
    policy: PreprocessPolicy | None = None,
) -> SAXSAIRescueDecision:
    """Evaluate candidate evidence through the shared SAXS decision policy."""

    selected_policy = policy or get_preprocess_policy("SAXS")
    if selected_policy.technique.upper() != "SAXS":
        raise PolicyValidationError("SAXS AI decision requires the SAXS preprocessing policy")
    if automation_state is not None and automation_state != selected_policy.automation_state:
        selected_policy = selected_policy.with_automation_state(automation_state)
    outcome = decide_preprocess_candidate(
        evidence,
        selected_policy,
        candidate_margin=candidate_margin,
        metadata_complete=metadata_complete,
    )
    apply_allowed = bool(
        outcome.decision == "auto_accept"
        and all(outcome.hard_guard_results.values())
    )
    return SAXSAIRescueDecision(
        outcome=outcome,
        original_preserved=True,
        physical_validation_required=True,
        apply_allowed=apply_allowed,
    )


__all__ = [
    "SAXSConfirmedRerunAudit",
    "SAXSAIRescueDecision",
    "SAXSAIRescuePlan",
    "assess_saxs_ai_candidate",
    "assess_saxs_confirmed_rerun",
    "build_saxs_ai_summary_context",
    "build_saxs_confirmed_rerun_evidence",
    "build_saxs_ai_rescue_plan",
    "sanitize_saxs_ai_summary_context",
    "validate_saxs_confirmation_report",
    "validate_saxs_ai_intent",
]
