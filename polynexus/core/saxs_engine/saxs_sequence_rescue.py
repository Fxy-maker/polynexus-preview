"""Evidence-only sequence rescue adapters for SAXS result objects.

This module does not alter source frames or fill missing axis positions.  It
turns an already selected, existing alternative metric path into an auditable
candidate and provides one explicit all-gates validation helper.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from .saxs_quality_contracts import RescueCandidate, RescueValidationReport


_SEQUENCE_RESCUE_SOURCE = "saxs_temperature.select_lc_sequence_path"


def _get_value(point: Any, name: str, default: Any = None) -> Any:
    if isinstance(point, Mapping):
        return point.get(name, default)
    return getattr(point, name, default)


def _finite_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def _reason_codes(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        values = value.split("|")
    elif isinstance(value, Sequence):
        values = value
    else:
        values = ()
    return tuple(dict.fromkeys(str(item).strip() for item in values if str(item).strip()))


def build_sequence_rescue_candidates(
    points: Sequence[Any] | None,
    *,
    axis_name: str = "temperature",
) -> tuple[RescueCandidate, ...]:
    """Expose existing sequence-selected alternatives as rescue candidates.

    Only a finite non-primary path selected by the existing deterministic
    sequence selector becomes a candidate.  ``None`` points and frames with a
    usable primary value remain untouched and do not produce fabricated data.
    """

    if points is None:
        return ()

    candidates: list[RescueCandidate] = []
    normalized_axis = str(axis_name or "temperature").strip() or "temperature"
    for frame_index, point in enumerate(points):
        if point is None:
            continue
        proposed_source = str(_get_value(point, "lc_effective_source", "") or "").strip()
        proposed_value = _finite_number(_get_value(point, "lc_effective_nm"))
        if not proposed_source or proposed_source == "primary" or proposed_value is None or proposed_value <= 0:
            continue

        original_value = _finite_number(_get_value(point, "lc_nm"))
        axis_value = _finite_number(
            _get_value(point, f"{normalized_axis}_C", _get_value(point, normalized_axis))
        )
        path_status = str(_get_value(point, "lc_path_status", "diagnostic_only") or "diagnostic_only")
        reasons = list(_reason_codes(_get_value(point, "lc_path_reason", "")))
        if original_value is None:
            reasons.append("original_metric_missing")
        reasons.append("sequence_existing_alternative")
        candidate_id = f"{normalized_axis}-frame-{frame_index}-lc-{proposed_source}"
        candidates.append(
            RescueCandidate(
                candidate_id=candidate_id,
                kind="deterministic",
                parameters={
                    "frame_index": frame_index,
                    "axis_name": normalized_axis,
                    "axis_value": axis_value,
                    "metric": "lc_nm",
                    "original_value_nm": original_value,
                    "proposed_value_nm": proposed_value,
                    "proposed_source": proposed_source,
                    "path_status": path_status,
                    "preserve_missing_frames": True,
                    "apply_mode": "candidate_only",
                },
                reason_codes=tuple(dict.fromkeys(reasons)),
                source="saxs_temperature.select_lc_sequence_path",
                requires_validation=True,
            )
        )
    return tuple(candidates)


def resolve_sequence_rescue_candidate(
    candidates: Sequence[RescueCandidate | Mapping[str, Any]] | None,
    candidate_id: str,
    *,
    mode: str = "temperature",
) -> RescueCandidate | None:
    """Resolve one advisory ID against the current full candidate records.

    The prompt projection is intentionally insufficient for this operation:
    resolution requires the source provenance retained on the current result.
    This function only restores candidate identity and never evaluates or
    applies the candidate.
    """

    if str(mode or "").strip().lower() != "temperature":
        return None
    target_id = str(candidate_id or "").strip()
    if not target_id or candidates is None or isinstance(candidates, (str, bytes)):
        return None

    matches: list[RescueCandidate] = []
    try:
        candidate_items = list(candidates)
    except TypeError:
        return None
    for item in candidate_items:
        if isinstance(item, RescueCandidate):
            candidate = item
        elif isinstance(item, Mapping):
            try:
                candidate = RescueCandidate.from_dict(item)
            except (KeyError, TypeError, ValueError):
                continue
        else:
            continue
        if candidate.candidate_id == target_id:
            matches.append(candidate)

    if len(matches) != 1:
        return None
    candidate = matches[0]
    parameters = candidate.parameters
    if (
        candidate.kind != "deterministic"
        or candidate.requires_validation is not True
        or candidate.source != _SEQUENCE_RESCUE_SOURCE
        or str(parameters.get("axis_name", "")).strip().lower() != "temperature"
        or parameters.get("metric") != "lc_nm"
        or parameters.get("apply_mode") != "candidate_only"
        or parameters.get("preserve_missing_frames") is not True
    ):
        return None

    return RescueCandidate.from_dict(candidate.to_dict())


def validate_sequence_rescue_candidate(
    candidate: RescueCandidate,
    *,
    hard_gate_passed: bool,
    physical_gate_passed: bool,
    data_preserved: bool,
    sequence_gate_passed: bool,
    soft_score: float | None = None,
    rejection_reasons: Sequence[str] = (),
) -> RescueValidationReport:
    """Create an accepted/rejected report only after every gate is explicit."""

    all_gates_passed = bool(
        hard_gate_passed
        and physical_gate_passed
        and data_preserved
        and sequence_gate_passed
    )
    decision = "accepted" if all_gates_passed else "rejected"
    return RescueValidationReport(
        candidate_id=str(candidate.candidate_id),
        hard_gate_passed=bool(hard_gate_passed),
        physical_gate_passed=bool(physical_gate_passed),
        data_preserved=bool(data_preserved),
        sequence_gate_passed=bool(sequence_gate_passed),
        soft_score=soft_score,
        rejection_reasons=tuple(str(reason) for reason in rejection_reasons if str(reason)),
        decision=decision,
    )


__all__ = [
    "build_sequence_rescue_candidates",
    "resolve_sequence_rescue_candidate",
    "validate_sequence_rescue_candidate",
]
