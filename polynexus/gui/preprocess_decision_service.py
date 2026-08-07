from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from polynexus.core.saxs_engine.saxs_ai_rescue import (
    validate_saxs_confirmation_report,
)
from polynexus.core.saxs_mode import canonical_saxs_mode


PROTECTED_METRICS = (
    "noise_reduction",
    "baseline_flatness",
    "peak_shift",
    "fwhm_change",
    "integrated_area_change",
    "weak_peak_retention",
    "physical_parameter_drift",
)

_MAX_SAFE_INTEGER = 9_007_199_254_740_991


@dataclass(frozen=True)
class PreprocessUIDecision:
    mode: str
    title: str
    summary: str
    metric_rows: dict[str, Any] = field(default_factory=dict)
    reason_codes: tuple[str, ...] = ()
    apply_enabled: bool = False
    undo_enabled: bool = False
    selected_config: dict[str, Any] = field(default_factory=dict)
    evidence_kind: str = "generic"


def _exact_string(value: object, default: str = "") -> str:
    if type(value) is not str:
        return default
    text = value.strip()
    return text or default


def _selected_evidence(report: dict[str, Any]) -> dict[str, Any]:
    rows = report.get("preprocess_evidence", [])
    if not isinstance(rows, list):
        return {}
    selected_id = _exact_string(report.get("selected_candidate_id"))
    if selected_id:
        for item in rows:
            if (
                isinstance(item, dict)
                and _exact_string(item.get("candidate_id")) == selected_id
            ):
                return item
    for item in reversed(rows):
        if isinstance(item, dict):
            return item
    return {}


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _string_list(value: object) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    projected: list[str] = []
    for item in value:
        if type(item) is not str:
            continue
        text = item.strip()
        if text:
            projected.append(text)
    return projected


def _finite_count(value: object) -> tuple[int, int]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return 0, 0
    finite = 0
    for item in value:
        try:
            finite += int(math.isfinite(float(item)))
        except (TypeError, ValueError, OverflowError):
            continue
    return finite, len(value)


def _nonnegative_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    try:
        numeric = float(value)
    except (TypeError, ValueError, OverflowError):
        return 0
    if (
        not math.isfinite(numeric)
        or numeric < 0
        or numeric > _MAX_SAFE_INTEGER
    ):
        return 0
    return int(numeric)


def _bounded_fraction(value: object) -> float:
    if isinstance(value, bool):
        return 0.0
    try:
        numeric = float(value)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    if not math.isfinite(numeric):
        return 0.0
    return min(max(numeric, 0.0), 1.0)


def _nonnegative_index(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if (
        not math.isfinite(numeric)
        or numeric < 0
        or numeric > _MAX_SAFE_INTEGER
        or not numeric.is_integer()
    ):
        return None
    return int(numeric)


def _plateau_indices(plateau: Mapping[str, Any]) -> tuple[bool, set[Any]]:
    if "trial_indices" not in plateau:
        return True, set()
    raw_indices = plateau.get("trial_indices")
    if not isinstance(raw_indices, Sequence) or isinstance(raw_indices, (str, bytes)):
        return True, set()
    selected: set[Any] = set()
    for item in raw_indices:
        index = _nonnegative_index(item)
        if index is not None:
            selected.add(index)
    return True, selected


def _finite_number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return numeric if math.isfinite(numeric) else None


def _sanitised_intervals(value: object) -> dict[str, dict[str, float | int]]:
    intervals = _mapping(value)
    projected: dict[str, dict[str, float | int]] = {}
    for name, raw_item in intervals.items():
        if not isinstance(name, str) or len(name) > 128:
            continue
        item = _mapping(raw_item)
        if not item and not isinstance(raw_item, Mapping):
            continue
        row: dict[str, float | int] = {}
        for key in ("lower", "median", "upper"):
            numeric = _finite_number(item.get(key))
            if numeric is not None:
                row[key] = numeric
        if "replicates" in item:
            row["replicates"] = _nonnegative_int(item.get("replicates"))
        projected[name] = row
    return projected


def _orientation_rows(
    stability: Mapping[str, Any],
    *,
    continuity: Mapping[str, Any],
    active_dimensions: list[str],
) -> dict[str, Any]:
    orientation_metrics = (
        "f_herman",
        "f_herman_raw",
        "orientation_axis_deg",
        "orientation_strength",
    )
    frame_count = _nonnegative_int(continuity.get("frame_count", 0))
    has_continuity_frame_count = frame_count > 0
    observed_counts: dict[str, int] = {}
    finite_counts = _mapping(continuity.get("metric_finite_frame_count"))
    for name in orientation_metrics:
        if name not in finite_counts:
            continue
        try:
            observed_counts[name] = _nonnegative_int(finite_counts[name])
        except (TypeError, ValueError):
            observed_counts[name] = 0
    aggregate_metrics = set(observed_counts)

    plateau = _mapping(stability.get("plateau"))
    has_plateau_indices, plateau_indices = _plateau_indices(plateau)
    trials = stability.get("trials", ())
    selected_trials: list[Mapping[str, Any]] = []
    trial_frame_values: list[Mapping[str, Any]] = []
    if isinstance(trials, Sequence) and not isinstance(trials, (str, bytes)):
        for raw_trial in trials:
            trial = _mapping(raw_trial)
            if not trial:
                continue
            if has_plateau_indices:
                trial_index = _nonnegative_index(trial.get("index"))
                if trial_index is None or trial_index not in plateau_indices:
                    continue
            selected_trials.append(trial)
            frame_values = _mapping(trial.get("frame_values"))
            trial_frame_values.append(frame_values)
            for name in orientation_metrics:
                if name not in frame_values:
                    continue
                finite, total = _finite_count(frame_values[name])
                if not has_continuity_frame_count:
                    frame_count = max(frame_count, total)
    for name in orientation_metrics:
        if name in aggregate_metrics or not any(
            name in frame_values for frame_values in trial_frame_values
        ):
            continue
        observed_counts[name] = min(
            _finite_count(frame_values.get(name, ()))[0]
            for frame_values in trial_frame_values
        )

    reason_codes = _string_list(stability.get("reason_codes"))
    for trial in selected_trials:
        reason_codes.extend(_string_list(trial.get("reason_codes")))
    orientation_reasons = [
        reason
        for reason in reason_codes
        if "orientation" in reason.lower() or "tensile_axis" in reason.lower()
    ]
    orientation_active = any(
        "orientation" in name.lower()
        or "chi" in name.lower()
        or "mask_dilation" in name.lower()
        for name in active_dimensions
    )
    if not observed_counts and not orientation_reasons and not orientation_active:
        return {}

    coverage: dict[str, dict[str, int | float]] = {}
    for name, finite in observed_counts.items():
        finite = _nonnegative_int(finite)
        if frame_count:
            finite = min(finite, frame_count)
        denominator = frame_count or finite
        coverage[name] = {
            "finite_frames": finite,
            "frame_count": denominator,
            "fraction": round(finite / denominator, 6) if denominator else 0.0,
        }
    missing_or_invalid = any(
        token in reason.lower()
        for reason in orientation_reasons
        for token in ("missing", "unknown", "unavailable", "invalid", "failed")
    )
    has_finite_evidence = any(
        int(item["finite_frames"]) > 0 for item in coverage.values()
    )
    incomplete_coverage = any(
        float(item["fraction"]) < 1.0 for item in coverage.values()
    )
    if has_finite_evidence and (missing_or_invalid or incomplete_coverage):
        status = "partial"
    elif has_finite_evidence:
        status = "available"
    else:
        status = "unavailable"
    return {
        "orientation_status": status,
        "orientation_coverage": coverage,
    }


def _saxs_stability_rows(stability: Mapping[str, Any]) -> dict[str, Any]:
    plateau = _mapping(stability.get("plateau"))
    has_trial_indices, trial_indices = _plateau_indices(plateau)
    platform_points = plateau.get("point_count")
    if platform_points is None:
        platform_points = len(trial_indices) if has_trial_indices else 0
    active_dimensions = _string_list(stability.get("active_dimensions"))
    if not active_dimensions:
        active_dimensions = _string_list(plateau.get("active_dimensions"))
    excluded_dimensions = _mapping(stability.get("excluded_dimensions"))
    continuity = _mapping(stability.get("continuity"))
    continuity_passed = continuity.get("passed") is True
    continuity_status = _exact_string(
        continuity.get("status"),
        "passed" if continuity_passed else "failed",
    )
    if "perturbation_intervals" in stability:
        raw_intervals = stability.get("perturbation_intervals")
    else:
        raw_intervals = stability.get("bootstrap")
    intervals = _sanitised_intervals(raw_intervals)
    rows: dict[str, Any] = {
        "platform_points": _nonnegative_int(platform_points),
        "platform_coverage": _bounded_fraction(
            plateau.get("coverage_fraction", 0.0)
        ),
        "platform_bounds": deepcopy(dict(_mapping(plateau.get("parameter_bounds")))),
        "active_dimensions": active_dimensions,
        "excluded_dimensions": deepcopy(dict(excluded_dimensions)),
        "continuity_status": continuity_status,
        "continuity_passed": continuity_passed,
        "continuity_frame_count": _nonnegative_int(
            continuity.get("frame_count", 0)
        ),
        "physics_gate_passed": stability.get("physics_gate_passed") is True,
        "quality_gate_passed": stability.get("quality_gate_passed") is True,
        "stability_decision": _exact_string(
            stability.get("decision"),
            "keep_original",
        ),
        "decision_reasons": _string_list(stability.get("reason_codes")),
        "perturbation_intervals": deepcopy(intervals),
    }
    rows.update(
        _orientation_rows(
            stability,
            continuity=continuity,
            active_dimensions=active_dimensions,
        )
    )
    return rows


def _saxs_confirmation_contract_complete(
    payload: Mapping[str, Any],
    stability: Mapping[str, Any],
) -> bool:
    selected = _mapping(payload.get("selected_preprocess_config"))
    original = _mapping(payload.get("original_preprocess_config"))
    decision = _mapping(payload.get("preprocess_decision"))
    guards = _mapping(decision.get("hard_guard_results"))
    required_guards = {
        "stability_plateau",
        "physical_gate",
        "quality_gate",
        "cross_frame_continuity",
    }
    payload_mode = canonical_saxs_mode(_exact_string(payload.get("mode")))
    stability_mode = canonical_saxs_mode(_exact_string(stability.get("mode")))
    if payload_mode is None or stability_mode is None or payload_mode != stability_mode:
        return False
    mode = payload_mode
    continuity = _mapping(stability.get("continuity"))
    continuity_passed = continuity.get("passed") is True or (
        mode == "static"
        and _exact_string(continuity.get("status")) == "not_applicable"
    )
    try:
        validate_saxs_confirmation_report(
            payload,
            current_config=dict(original),
            mode=mode,
        )
    except (TypeError, ValueError):
        return False
    return bool(
        stability.get("complete") is True
        and _exact_string(stability.get("decision"))
        in {"request_confirmation", "auto_accept"}
        and _mapping(stability.get("plateau")).get("connected") is True
        and stability.get("physics_gate_passed") is True
        and stability.get("quality_gate_passed") is True
        and continuity_passed
        and required_guards.issubset(guards)
        and all(guards[name] is True for name in required_guards)
        and selected
        and original
    )


def _saxs_stability_summary(
    *,
    decision_name: str,
    confidence: str,
    metric_rows: Mapping[str, Any],
    reason_codes: tuple[str, ...],
    apply_enabled: bool,
) -> str:
    def gate(value: object) -> str:
        return "passed" if value else "failed"

    parts = [
        f"SAXS stability decision: {decision_name}; confidence: {confidence}",
        (
            f"platform: {metric_rows['platform_points']} points, "
            f"coverage {metric_rows['platform_coverage']}"
        ),
        (
            f"continuity: {metric_rows['continuity_status']} "
            f"({metric_rows['continuity_frame_count']} frames)"
        ),
        f"physical gate: {gate(metric_rows['physics_gate_passed'])}",
        f"quality gate: {gate(metric_rows['quality_gate_passed'])}",
    ]
    if decision_name == "request_confirmation" and apply_enabled:
        parts.append("Apply requires explicit user confirmation")
    elif decision_name == "request_confirmation":
        parts.append("Apply unavailable: confirmation contract incomplete")
    elif decision_name == "keep_original":
        reason_text = ", ".join(reason_codes) or "stability requirements not met"
        parts.append(f"Apply unavailable: {reason_text}")
    return "; ".join(parts) + "."


def build_preprocess_ui_decision(report: object) -> PreprocessUIDecision:
    payload = dict(report) if isinstance(report, Mapping) else {}
    raw_stability = payload.get("stability_report")
    has_stability = isinstance(raw_stability, Mapping)
    stability = _mapping(raw_stability)
    raw_decision = payload.get("preprocess_decision", {})
    decision = _mapping(raw_decision)
    decision_name = _exact_string(decision.get("decision"), "keep_original")
    if has_stability and decision_name == "auto_accept":
        decision_name = "request_confirmation"
    simulated = _exact_string(decision.get("simulated_decision"), decision_name)
    confidence = _exact_string(decision.get("confidence_band"), "low")

    evidence_kind = "saxs_stability" if has_stability else "generic"

    if decision_name == "auto_accept":
        mode = "auto_apply"
        title = "Preprocessing automatically selected"
        apply_enabled = False
        undo_enabled = True
    elif decision_name == "request_confirmation":
        mode = "confirm"
        title = "Confirm preprocessing change"
        apply_enabled = (
            _saxs_confirmation_contract_complete(payload, stability)
            if has_stability
            else True
        )
        undo_enabled = False
    elif simulated != "keep_original":
        mode = "shadow"
        title = "Preprocessing shadow result"
        apply_enabled = False
        undo_enabled = False
    else:
        mode = "keep_original"
        title = "Original preprocessing retained"
        apply_enabled = False
        undo_enabled = False

    reason_codes = tuple(
        dict.fromkeys(
            _string_list(decision.get("reason_codes"))
            + _string_list(stability.get("reason_codes"))
        )
    )
    if has_stability:
        metric_rows = _saxs_stability_rows(stability)
        summary = _saxs_stability_summary(
            decision_name=decision_name,
            confidence=confidence,
            metric_rows=metric_rows,
            reason_codes=reason_codes,
            apply_enabled=apply_enabled,
        )
    else:
        evidence = _selected_evidence(payload)
        metric_rows = {
            name: evidence[name]
            for name in PROTECTED_METRICS
            if name in evidence and evidence[name] is not None
        }
        summary = (
            f"Decision: {decision_name}; confidence: {confidence}; "
            f"protected metrics available: {len(metric_rows)}."
        )
    selected_config = payload.get("selected_preprocess_config", {})
    if isinstance(selected_config, Mapping):
        selected_config = dict(selected_config)
    else:
        selected_config = {}
    return PreprocessUIDecision(
        mode=mode,
        title=title,
        summary=summary,
        metric_rows=deepcopy(metric_rows),
        reason_codes=reason_codes,
        apply_enabled=apply_enabled,
        undo_enabled=undo_enabled,
        selected_config=deepcopy(selected_config),
        evidence_kind=evidence_kind,
    )
