"""Core-only tracking of neutral q-band orientation features across strain."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np


def _value(item: Any, name: str, default: Any = None) -> Any:
    if isinstance(item, Mapping):
        return item.get(name, default)
    return getattr(item, name, default)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return [_json_safe(item) for item in value.tolist()]
    if isinstance(value, (np.integer, np.bool_)):
        return value.item()
    if isinstance(value, np.floating):
        value = float(value)
    if isinstance(value, float):
        return value if np.isfinite(value) else None
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    return str(value)


def _mapping_proxy(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    from types import MappingProxyType

    return MappingProxyType({str(key): _json_safe(item) for key, item in (value or {}).items()})


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def _axis_distance(first: Any, second: Any) -> float | None:
    first_value = _finite(first)
    second_value = _finite(second)
    if first_value is None or second_value is None:
        return None
    return float(abs((first_value - second_value + 90.0) % 180.0 - 90.0))


@dataclass(frozen=True)
class OrientationFeatureObservation:
    frame_source_index: int
    condition_value: float | None
    candidate_id: str
    q_range_nm1: tuple[float, float]
    common_q_bin_ids: tuple[str, ...]
    q_center_nm1: float | None
    f_principal_raw: float | None
    f_reference: float | None
    delta_f_from_zero: float | None
    delta_stability_interval: Mapping[str, Any] = field(default_factory=dict)
    reliability_status: str = "unavailable"
    reason_codes: tuple[str, ...] = ()
    _frame_evidence: Any = field(default=None, repr=False, compare=False)
    _candidate: Any = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "q_range_nm1", tuple(float(item) for item in self.q_range_nm1))
        object.__setattr__(self, "common_q_bin_ids", tuple(str(item) for item in self.common_q_bin_ids))
        object.__setattr__(self, "delta_stability_interval", _mapping_proxy(self.delta_stability_interval))
        object.__setattr__(self, "reason_codes", tuple(str(item) for item in self.reason_codes))

    def to_dict(self) -> dict[str, Any]:
        return _json_safe({
            "frame_source_index": self.frame_source_index,
            "condition_value": self.condition_value,
            "candidate_id": self.candidate_id,
            "q_range_nm1": self.q_range_nm1,
            "common_q_bin_ids": self.common_q_bin_ids,
            "q_center_nm1": self.q_center_nm1,
            "f_principal_raw": self.f_principal_raw,
            "f_reference": self.f_reference,
            "delta_f_from_zero": self.delta_f_from_zero,
            "delta_stability_interval": self.delta_stability_interval,
            "reliability_status": self.reliability_status,
            "reason_codes": self.reason_codes,
        })


@dataclass(frozen=True)
class OrientationFeatureTrack:
    track_id: str
    feature_kind: str
    convention: str
    reference_axis_kind: str
    reference_axis_deg: float | None
    reliability_policy_digest: str
    observations: tuple[OrientationFeatureObservation, ...]
    reliability_status: str = "diagnostic"
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "observations", tuple(self.observations))
        object.__setattr__(self, "reason_codes", tuple(str(item) for item in self.reason_codes))

    def to_dict(self) -> dict[str, Any]:
        return _json_safe({
            "track_id": self.track_id,
            "feature_kind": self.feature_kind,
            "convention": self.convention,
            "reference_axis_kind": self.reference_axis_kind,
            "reference_axis_deg": self.reference_axis_deg,
            "reliability_policy_digest": self.reliability_policy_digest,
            "observations": tuple(item.to_dict() for item in self.observations),
            "reliability_status": self.reliability_status,
            "reason_codes": self.reason_codes,
        })


@dataclass(frozen=True)
class OrientationSequenceEvidence:
    tracks: tuple[OrientationFeatureTrack, ...] = ()
    zero_reference_source_index: int | None = None
    ambiguous_match_count: int = 0
    split_count: int = 0
    missing_frame_indices: tuple[int, ...] = ()
    suspected_systematic_harmonic: bool = False
    systematic_harmonic_metrics: Mapping[str, Any] = field(default_factory=dict)
    level: str = "Unusable"
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "tracks", tuple(self.tracks))
        object.__setattr__(self, "missing_frame_indices", tuple(int(item) for item in self.missing_frame_indices))
        object.__setattr__(self, "systematic_harmonic_metrics", _mapping_proxy(self.systematic_harmonic_metrics))
        object.__setattr__(self, "reason_codes", tuple(str(item) for item in self.reason_codes))

    def to_dict(self) -> dict[str, Any]:
        return _json_safe({
            "tracks": tuple(item.to_dict() for item in self.tracks),
            "zero_reference_source_index": self.zero_reference_source_index,
            "ambiguous_match_count": self.ambiguous_match_count,
            "split_count": self.split_count,
            "missing_frame_indices": self.missing_frame_indices,
            "suspected_systematic_harmonic": self.suspected_systematic_harmonic,
            "systematic_harmonic_metrics": self.systematic_harmonic_metrics,
            "level": self.level,
            "reason_codes": self.reason_codes,
        })


@dataclass(frozen=True)
class _Frame:
    source_index: int
    condition_value: float | None
    evidence: Any


def _evidence_payload(frame: Any) -> Any:
    evidence = _value(frame, "q_resolved_orientation_evidence")
    if evidence is None:
        evidence = _value(frame, "orientation_tracking_source")
    if evidence is None:
        evidence = _value(frame, "evidence")
    if evidence is None and _value(frame, "q_band_candidates") is not None:
        evidence = frame
    if hasattr(evidence, "to_dict"):
        return evidence.to_dict()
    return evidence


def _normalize_frames(
    frames: Sequence[Any],
    frame_source_indices: Sequence[Any] | None,
) -> tuple[tuple[_Frame, ...], tuple[str, ...]]:
    if frame_source_indices is not None and len(frame_source_indices) != len(frames):
        return (), ("source_index_mapping_invalid", "source_index_length_mismatch")
    normalized: list[_Frame] = []
    reasons: list[str] = []
    seen: set[int] = set()
    for position, frame in enumerate(frames):
        raw_index = (
            frame_source_indices[position]
            if frame_source_indices is not None
            else _value(frame, "frame_source_index", _value(frame, "source_index"))
        )
        if isinstance(raw_index, (bool, np.bool_)):
            raw_index = None
        try:
            index = int(raw_index)
            if float(raw_index) != float(index) or index < 0:
                raise ValueError
        except (TypeError, ValueError, OverflowError):
            reasons.append("source_index_mapping_invalid")
            continue
        if index in seen:
            reasons.append("source_index_mapping_duplicate")
            continue
        seen.add(index)
        condition = _finite(_value(frame, "condition_value", _value(frame, "strain_pct")))
        normalized.append(_Frame(index, condition, _evidence_payload(frame)))
    if reasons:
        return (), tuple(dict.fromkeys(reasons))
    if not normalized:
        return (), ("orientation_tracking_input_unavailable",)
    normalized.sort(key=lambda item: item.source_index)
    return tuple(normalized), ()


def _candidates(evidence: Any) -> tuple[Any, ...]:
    values = _value(evidence, "q_band_candidates", ())
    return tuple(values or ())


def _candidate_ids(candidate: Any) -> tuple[str, ...]:
    return tuple(str(item) for item in (_value(candidate, "supported_q_bin_ids", ()) or ()))


def _common_ids(left: Any, right: Any) -> tuple[str, ...]:
    right_ids = set(_candidate_ids(right))
    return tuple(item for item in _candidate_ids(left) if item in right_ids)


def _compatible(
    left_evidence: Any,
    left: Any,
    right_evidence: Any,
    right: Any,
    *,
    max_axis_drift_deg: float,
) -> bool:
    if str(_value(left, "feature_kind", "q_band")) != "q_band" or str(_value(right, "feature_kind", "q_band")) != "q_band":
        return False
    if _value(left_evidence, "convention") != _value(right_evidence, "convention"):
        return False
    if _value(left_evidence, "reference_axis_kind", "unknown") != _value(right_evidence, "reference_axis_kind", "unknown"):
        return False
    left_axis = _finite(_value(left_evidence, "reference_axis_deg"))
    right_axis = _finite(_value(right_evidence, "reference_axis_deg"))
    if (left_axis is None) != (right_axis is None) or (left_axis is not None and not np.isclose(left_axis, right_axis)):
        return False
    if _value(left_evidence, "reliability_policy_digest", "") != _value(right_evidence, "reliability_policy_digest", ""):
        return False
    if str(_value(left_evidence, "reliability_status", "unavailable")).lower() == "unavailable" or str(_value(right_evidence, "reliability_status", "unavailable")).lower() == "unavailable":
        return False
    common = _common_ids(left, right)
    if len(common) < 3:
        return False
    left_low = _finite(_value(left, "q_min_nm1"))
    left_high = _finite(_value(left, "q_max_nm1"))
    right_low = _finite(_value(right, "q_min_nm1"))
    right_high = _finite(_value(right, "q_max_nm1"))
    left_center = _finite(_value(left, "q_center_nm1"))
    right_center = _finite(_value(right, "q_center_nm1"))
    if None in (left_low, left_high, right_low, right_high, left_center, right_center):
        return False
    if not (right_low <= left_center <= right_high and left_low <= right_center <= left_high):
        return False
    left_level = str(_value(left, "level", "unavailable")).lower()
    right_level = str(_value(right, "level", "unavailable")).lower()
    if left_level == "unusable" or right_level == "unusable":
        return False
    left_orientation = _finite(_value(left, "principal_axis_deg"))
    right_orientation = _finite(_value(right, "principal_axis_deg"))
    if left_orientation is not None and right_orientation is not None:
        distance = _axis_distance(left_orientation, right_orientation)
        if distance is not None and distance > max_axis_drift_deg:
            return False
    return True


def compatible(
    left_frame: Any,
    left: Any,
    right_frame: Any,
    right: Any,
    *,
    max_axis_drift_deg: float = 20.0,
) -> bool:
    """Public compatibility predicate used by focused consumers and tests."""

    return _compatible(
        _evidence_payload(left_frame), left, _evidence_payload(right_frame), right,
        max_axis_drift_deg=max_axis_drift_deg,
    )


def ordered_common_q_bins(left: Any, right: Any) -> tuple[str, ...]:
    return _common_ids(left, right)


def _q_bins(evidence: Any) -> dict[str, Any]:
    return {
        str(_value(item, "q_bin_id")): item
        for item in (_value(evidence, "q_bins", ()) or ())
        if _value(item, "q_bin_id") is not None
    }


def aggregate_common_m2(
    left_evidence: Any,
    right_evidence: Any,
    q_bin_ids: Sequence[str],
) -> tuple[complex, complex] | None:
    """Reaggregate Task 1 additive harmonic terms over exact common support."""

    outputs: list[complex] = []
    for evidence in (left_evidence, right_evidence):
        by_id = _q_bins(evidence)
        selected = [by_id.get(str(q_bin_id)) for q_bin_id in q_bin_ids]
        if any(item is None for item in selected):
            return None
        if any(
            _finite(_value(item, "harmonic_numerator_real")) is None
            or _finite(_value(item, "harmonic_numerator_imag")) is None
            or _finite(_value(item, "intensity_denominator")) is None
            for item in selected
        ):
            return None
        denominator = sum(float(_value(item, "intensity_denominator")) for item in selected)
        if denominator <= 0:
            return None
        numerator = sum(
            complex(
                float(_value(item, "harmonic_numerator_real")),
                float(_value(item, "harmonic_numerator_imag")),
            )
            for item in selected
        )
        outputs.append(numerator / denominator)
    return outputs[0], outputs[1]


def _delta_interval(
    frame_interval: Mapping[str, Any] | None,
    zero_interval: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(frame_interval, Mapping) or not isinstance(zero_interval, Mapping):
        return None
    frame_lower = frame_interval.get("lower", frame_interval.get("f_reference_low"))
    frame_upper = frame_interval.get("upper", frame_interval.get("f_reference_high"))
    zero_lower = zero_interval.get("lower", zero_interval.get("f_reference_low"))
    zero_upper = zero_interval.get("upper", zero_interval.get("f_reference_high"))
    if any(_finite(value) is None for value in (frame_lower, frame_upper, zero_lower, zero_upper)):
        return None
    return {
        "lower": float(frame_lower) - float(zero_upper),
        "upper": float(frame_upper) - float(zero_lower),
        "kind": "conservative_stability_bound",
    }


def delta_interval(
    frame_interval: Mapping[str, Any],
    zero_interval: Mapping[str, Any],
) -> dict[str, Any] | None:
    return _delta_interval(frame_interval, zero_interval)


def _candidate_interval(evidence: Any, candidate: Any, common_ids: Sequence[str]) -> Mapping[str, Any] | None:
    direct = _value(candidate, "stability_interval")
    if isinstance(direct, Mapping):
        return direct
    bins = _q_bins(evidence)
    intervals = [
        _value(bins[item], "stability_interval")
        for item in common_ids
        if item in bins and isinstance(_value(bins[item], "stability_interval"), Mapping)
    ]
    if not intervals:
        return None
    lows = [
        _finite(interval.get("lower", interval.get("f_reference_low")))
        for interval in intervals
    ]
    highs = [
        _finite(interval.get("upper", interval.get("f_reference_high")))
        for interval in intervals
    ]
    if any(value is None for value in (*lows, *highs)):
        return None
    return {"lower": min(lows), "upper": max(highs)}


def _reference_f(evidence: Any, m2: complex) -> float | None:
    axis = _finite(_value(evidence, "reference_axis_deg"))
    if axis is None:
        return None
    return float(0.25 + 0.75 * np.real(m2 * np.exp(-2j * np.deg2rad(axis))))


def _build_observation(
    frame: _Frame,
    candidate: Any,
    *,
    zero_frame: _Frame | None,
    zero_candidate: Any | None,
) -> OrientationFeatureObservation:
    candidate_ids = _candidate_ids(candidate)
    common_ids = candidate_ids
    delta = None
    interval: Mapping[str, Any] | None = None
    reasons: list[str] = []
    if zero_frame is None or zero_candidate is None:
        reasons.append("zero_reference_unavailable")
    elif frame.source_index == zero_frame.source_index:
        reasons.append("zero_reference_observation")
    else:
        common_ids = _common_ids(zero_candidate, candidate)
        if len(common_ids) < 3:
            reasons.append("delta_common_support_unavailable")
        else:
            pair = aggregate_common_m2(zero_frame.evidence, frame.evidence, common_ids)
            if pair is None:
                reasons.append("delta_common_support_unavailable")
            else:
                zero_f = _reference_f(zero_frame.evidence, pair[0])
                frame_f = _reference_f(frame.evidence, pair[1])
                if zero_f is None or frame_f is None:
                    reasons.append("delta_reference_axis_unavailable")
                elif str(_value(frame.evidence, "reliability_status", "unavailable")).lower() in {"unavailable", "diagnostic", "artifact_sensitive"}:
                    reasons.append("delta_local_reliability_not_eligible")
                elif str(_value(zero_frame.evidence, "reliability_status", "unavailable")).lower() in {"unavailable", "diagnostic", "artifact_sensitive"}:
                    reasons.append("delta_local_reliability_not_eligible")
                else:
                    delta = frame_f - zero_f
                    interval = _delta_interval(
                        _candidate_interval(frame.evidence, candidate, common_ids),
                        _candidate_interval(zero_frame.evidence, zero_candidate, common_ids),
                    )
                    if interval is None:
                        reasons.append("delta_stability_common_support_unavailable")
    q_min = _finite(_value(candidate, "q_min_nm1"))
    q_max = _finite(_value(candidate, "q_max_nm1"))
    if q_min is None or q_max is None:
        q_range = (float("nan"), float("nan"))
    else:
        q_range = (q_min, q_max)
    return OrientationFeatureObservation(
        frame_source_index=frame.source_index,
        condition_value=frame.condition_value,
        candidate_id=str(_value(candidate, "candidate_id", "")),
        q_range_nm1=q_range,
        common_q_bin_ids=common_ids,
        q_center_nm1=_finite(_value(candidate, "q_center_nm1")),
        f_principal_raw=_finite(_value(candidate, "f_principal_raw")),
        f_reference=_finite(_value(candidate, "f_reference")),
        delta_f_from_zero=delta,
        delta_stability_interval=interval or {},
        reliability_status=str(_value(frame.evidence, "reliability_status", "diagnostic")),
        reason_codes=tuple(dict.fromkeys(reasons)),
        _frame_evidence=frame.evidence,
        _candidate=candidate,
    )


def _track_id(nodes: Sequence[tuple[int, int]], frames: Sequence[_Frame], candidates_by_frame: Sequence[Sequence[Any]]) -> str:
    material = "|".join(
        f"{frames[frame_index].source_index}:{_value(candidates_by_frame[frame_index][candidate_index], 'candidate_id', '')}"
        for frame_index, candidate_index in nodes
    )
    suffix = hashlib.sha256(material.encode("utf-8")).hexdigest()[:12]
    return f"orientation-track-{suffix}"


def _systematic_metrics(tracks: Sequence[OrientationFeatureTrack], frame_count: int, max_axis_drift_deg: float) -> tuple[bool, dict[str, Any]]:
    if not tracks or frame_count == 0:
        return False, {"persistence_fraction": 0.0, "q_coverage_fraction": 0.0}
    best = max(tracks, key=lambda item: len(item.observations))
    persistence = len(best.observations) / frame_count
    q_sets = [set(item.common_q_bin_ids) for item in best.observations if item.common_q_bin_ids]
    common = set.intersection(*q_sets) if q_sets else set()
    union = set.union(*q_sets) if q_sets else set()
    axes = [item._candidate for item in best.observations]
    axis_values = [_finite(_value(item, "principal_axis_deg")) for item in axes]
    axis_values = [item for item in axis_values if item is not None]
    axis_spread = 0.0
    if len(axis_values) > 1:
        axis_spread = max(_axis_distance(left, right) or 0.0 for left in axis_values for right in axis_values)
    strengths = [_finite(_value(item, "anisotropy_strength")) for item in axes]
    strengths = [item for item in strengths if item is not None]
    strength_cv = None
    if strengths and np.mean(strengths) != 0:
        strength_cv = float(np.std(strengths) / abs(np.mean(strengths)))
    metrics = {
        "persistence_fraction": float(persistence),
        "q_coverage_fraction": float(len(common) / len(union)) if union else 0.0,
        "axis_spread_deg": float(axis_spread),
        "strength_cv": strength_cv,
    }
    suspected = persistence == 1.0 and metrics["q_coverage_fraction"] >= 0.5 and axis_spread <= max_axis_drift_deg
    return suspected, metrics


def track_orientation_features(
    frames: Sequence[Any],
    *,
    frame_source_indices: Sequence[Any] | None = None,
    max_axis_drift_deg: float = 20.0,
) -> OrientationSequenceEvidence:
    """Track only mutually unique compatible q bands across source-index order."""

    normalized, input_reasons = _normalize_frames(frames, frame_source_indices)
    if input_reasons:
        return OrientationSequenceEvidence(level="Unusable", reason_codes=input_reasons)
    missing: list[int] = []
    reasons: list[str] = []
    for left, right in zip(normalized, normalized[1:]):
        if right.source_index - left.source_index > 1:
            missing.extend(range(left.source_index + 1, right.source_index))
    if missing:
        reasons.append("missing_frame_gap")

    candidates_by_frame = [_candidates(frame.evidence) for frame in normalized]
    adjacency: dict[tuple[int, int], set[tuple[int, int]]] = {}
    ambiguous_count = 0
    for frame_index, (left_frame, right_frame) in enumerate(zip(normalized, normalized[1:])):
        source_gap = right_frame.source_index - left_frame.source_index
        if source_gap > 2:
            reasons.append("feature_track_gap_too_large")
            continue
        potential: dict[tuple[int, int], list[tuple[int, int]]] = {}
        reverse: dict[tuple[int, int], list[tuple[int, int]]] = {}
        for left_index, left_candidate in enumerate(candidates_by_frame[frame_index]):
            for right_index, right_candidate in enumerate(candidates_by_frame[frame_index + 1]):
                if _compatible(left_frame.evidence, left_candidate, right_frame.evidence, right_candidate, max_axis_drift_deg=max_axis_drift_deg):
                    left_node = (frame_index, left_index)
                    right_node = (frame_index + 1, right_index)
                    potential.setdefault(left_node, []).append(right_node)
                    reverse.setdefault(right_node, []).append(left_node)
        ambiguous_nodes = {
            node for node, values in potential.items() if len(values) != 1
        } | {
            node for node, values in reverse.items() if len(values) != 1
        }
        if ambiguous_nodes:
            ambiguous_count += 1
            reasons.append("feature_match_ambiguous")
        for left_node, values in potential.items():
            if left_node in ambiguous_nodes or len(values) != 1:
                continue
            right_node = values[0]
            if right_node in ambiguous_nodes or len(reverse.get(right_node, ())) != 1:
                continue
            adjacency.setdefault(left_node, set()).add(right_node)
            adjacency.setdefault(right_node, set()).add(left_node)

    all_nodes = [
        (frame_index, candidate_index)
        for frame_index, candidates in enumerate(candidates_by_frame)
        for candidate_index, candidate in enumerate(candidates)
        if str(_value(candidate, "level", "unavailable")).lower() != "unusable"
    ]
    visited: set[tuple[int, int]] = set()
    tracks: list[OrientationFeatureTrack] = []
    zero_reference_source_index: int | None = None
    if len([frame for frame in normalized if frame.condition_value is not None and np.isclose(frame.condition_value, 0.0)]) == 1:
        zero_reference_source_index = next(frame.source_index for frame in normalized if frame.condition_value is not None and np.isclose(frame.condition_value, 0.0))
    elif len([frame for frame in normalized if frame.condition_value is not None and np.isclose(frame.condition_value, 0.0)]) == 0:
        reasons.append("zero_reference_missing")
    else:
        reasons.append("zero_reference_ambiguous")

    for node in all_nodes:
        if node in visited:
            continue
        stack = [node]
        component: list[tuple[int, int]] = []
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            component.append(current)
            stack.extend(adjacency.get(current, ()))
        component.sort(key=lambda item: (normalized[item[0]].source_index, item[1]))
        zero_node = next(
            (item for item in component if normalized[item[0]].source_index == zero_reference_source_index),
            None,
        )
        zero_frame = normalized[zero_node[0]] if zero_node is not None else None
        zero_candidate = candidates_by_frame[zero_node[0]][zero_node[1]] if zero_node is not None else None
        observations = tuple(
            _build_observation(
                normalized[frame_index],
                candidates_by_frame[frame_index][candidate_index],
                zero_frame=zero_frame,
                zero_candidate=zero_candidate,
            )
            for frame_index, candidate_index in component
        )
        local_statuses = {str(item.reliability_status).lower() for item in observations}
        track_reasons: list[str] = []
        if "unavailable" in local_statuses:
            track_reasons.append("orientation_local_unavailable")
        if any(item.delta_f_from_zero is None and item.frame_source_index != zero_reference_source_index for item in observations):
            track_reasons.append("delta_not_available")
        evidence = normalized[component[0][0]].evidence
        track_level = "usable" if local_statuses == {"usable"} and not track_reasons else "diagnostic"
        tracks.append(OrientationFeatureTrack(
            track_id=_track_id(component, normalized, candidates_by_frame),
            feature_kind="q_band",
            convention=str(_value(evidence, "convention", "")),
            reference_axis_kind=str(_value(evidence, "reference_axis_kind", "unknown")),
            reference_axis_deg=_finite(_value(evidence, "reference_axis_deg")),
            reliability_policy_digest=str(_value(evidence, "reliability_policy_digest", "")),
            observations=observations,
            reliability_status=track_level,
            reason_codes=tuple(dict.fromkeys(track_reasons)),
        ))

    suspected, systematic_metrics = _systematic_metrics(tracks, len(normalized), max_axis_drift_deg)
    if suspected:
        reasons.append("systematic_harmonic_suspected")
    if not tracks:
        level = "Unusable"
    elif any(track.reliability_status != "usable" for track in tracks) or reasons:
        level = "Diagnostic"
    else:
        level = "Trend"
    split_count = max(0, len(tracks) - len(candidates_by_frame[0]) if candidates_by_frame else 0)
    return OrientationSequenceEvidence(
        tracks=tuple(tracks),
        zero_reference_source_index=zero_reference_source_index,
        ambiguous_match_count=ambiguous_count,
        split_count=split_count,
        missing_frame_indices=tuple(sorted(set(missing))),
        suspected_systematic_harmonic=suspected,
        systematic_harmonic_metrics=systematic_metrics,
        level=level,
        reason_codes=tuple(dict.fromkeys(reasons)),
    )


build_orientation_feature_tracks = track_orientation_features


__all__ = [
    "OrientationFeatureObservation",
    "OrientationFeatureTrack",
    "OrientationSequenceEvidence",
    "aggregate_common_m2",
    "build_orientation_feature_tracks",
    "compatible",
    "delta_interval",
    "ordered_common_q_bins",
    "track_orientation_features",
]
