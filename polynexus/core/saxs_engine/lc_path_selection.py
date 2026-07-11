"""Sequence-level lc candidate selection for temperature SAXS."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

import numpy as np


_SOURCE_PRIORITY = {
    "primary": 0,
    "tangent": 1,
    "idf": 2,
    "gamma_min": 3,
}


def _num(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return np.nan
    return number if np.isfinite(number) else np.nan


def _clean_reason_bits(bits: Sequence[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for bit in bits:
        text = str(bit or "").strip()
        if text and text not in seen:
            seen.add(text)
            ordered.append(text)
    return ordered


@dataclass
class LcCandidate:
    source: str
    value_nm: float
    score_local: float = np.nan
    hard_valid: bool = True
    reject_reasons: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LcPathDecision:
    temperature_C: float = np.nan
    selected_value_nm: float = np.nan
    selected_source: str = ""
    selected_score: float = np.nan
    selection_margin: float = np.nan
    status: str = "diagnostic_only"
    reason: str = ""
    candidate_count: int = 0
    candidates: List[LcCandidate] = field(default_factory=list)


@dataclass
class _PathState:
    label: str
    value_nm: float
    score_local: float
    is_none: bool = False
    candidate: Optional[LcCandidate] = None


def build_lc_candidates(point: Any) -> List[LcCandidate]:
    """Collect lc candidates from a frame-like object."""
    grouped: Dict[float, Dict[str, Any]] = {}
    for source, attr_name in (
        ("primary", "lc_nm"),
        ("tangent", "lc_tangent_nm"),
        ("idf", "lc_idf_nm"),
        ("gamma_min", "lc_gamma_min_nm"),
    ):
        value = _num(getattr(point, attr_name, np.nan))
        if not np.isfinite(value) or value <= 0:
            continue
        key = round(float(value), 4)
        bucket = grouped.setdefault(key, {"value_nm": float(value), "sources": []})
        bucket["sources"].append(source)

    candidates: List[LcCandidate] = []
    for bucket in grouped.values():
        sources = [str(src) for src in bucket["sources"] if str(src)]
        sources = sorted(dict.fromkeys(sources), key=lambda src: _SOURCE_PRIORITY.get(src, 99))
        source_label = "+".join(sources) if sources else "unknown"
        candidates.append(
            LcCandidate(
                source=source_label,
                value_nm=float(bucket["value_nm"]),
                evidence={
                    "sources": sources,
                    "source_count": len(sources),
                },
            )
        )

    candidates.sort(
        key=lambda cand: (
            0 if "primary" in cand.evidence.get("sources", []) else 1,
            -int(cand.evidence.get("source_count", 0) or 0),
            cand.value_nm,
        )
    )
    return candidates


def _candidate_median(candidates: Sequence[LcCandidate]) -> float:
    values = np.asarray([cand.value_nm for cand in candidates if np.isfinite(cand.value_nm) and cand.value_nm > 0], dtype=float)
    if values.size == 0:
        return np.nan
    return float(np.median(values))


def _candidate_spread(candidates: Sequence[LcCandidate]) -> float:
    values = np.asarray([cand.value_nm for cand in candidates if np.isfinite(cand.value_nm) and cand.value_nm > 0], dtype=float)
    if values.size < 2:
        return np.nan
    mean_value = float(np.mean(values))
    if not np.isfinite(mean_value) or mean_value <= 0:
        return np.nan
    return float((float(np.max(values)) - float(np.min(values))) / mean_value)


def _point_text(point: Any, *names: str) -> str:
    for name in names:
        value = str(getattr(point, name, "") or "").strip()
        if value:
            return value
    return ""


def _score_none_state(point: Any, candidate_count: int, spread: float) -> float:
    lc_status = _point_text(point, "lc_reliability_status").lower()
    melt_status = _point_text(point, "melting_window_status").lower()

    score = 0.0
    if lc_status == "usable":
        score -= 0.35
    elif lc_status == "low_confidence":
        score += 0.08
    elif lc_status == "diagnostic_only":
        score += 0.55

    if melt_status == "outside_window":
        score -= 0.10
    elif melt_status == "near_onset":
        score += 0.18
    elif melt_status == "within_window":
        score += 0.45
    elif melt_status == "post_end":
        score += 0.75

    if candidate_count == 0:
        score += 0.60
    elif np.isfinite(spread) and spread > 0.35:
        score += 0.05

    return float(score)


def _score_candidate(point: Any, candidate: LcCandidate, *, median_value: float, spread: float) -> tuple[float, List[str]]:
    reasons: List[str] = []
    L_nm = _num(getattr(point, "L_nm", np.nan))
    lc_nm = _num(candidate.value_nm)
    if not np.isfinite(L_nm) or L_nm <= 0 or not np.isfinite(lc_nm) or lc_nm <= 0:
        candidate.hard_valid = False
        reasons.append("structure_unresolved")
        return float("-inf"), reasons
    if lc_nm >= L_nm:
        candidate.hard_valid = False
        reasons.append("lc_ge_L")
        return float("-inf"), reasons

    score = 0.0
    ratio = lc_nm / L_nm
    candidate.evidence["ratio"] = float(ratio)
    if ratio < 0.05:
        score -= 1.50
        reasons.append("too_small_fraction")
    elif ratio < 0.12:
        score -= 0.95
        reasons.append("minority_fraction_too_low")
    elif ratio < 0.20:
        score -= 0.35
        reasons.append("minority_fraction_low")
    elif ratio > 0.85:
        score -= 0.25
        reasons.append("majority_fraction_high")

    if lc_nm < 1.0:
        score -= 0.25
        reasons.append("subnm_lc")
    elif lc_nm < 1.5:
        score -= 0.10
        reasons.append("very_small_lc")

    if np.isfinite(median_value):
        rel_diff = abs(lc_nm - median_value) / max(abs(median_value), 1e-9)
        candidate.evidence["median_rel_diff"] = float(rel_diff)
        if rel_diff <= 0.10:
            score += 0.35
            reasons.append("method_agreement")
        elif rel_diff <= 0.20:
            score += 0.18
            reasons.append("method_agreement")
        elif rel_diff >= 0.45:
            score -= 0.22
            reasons.append("method_conflict")

    sources = [str(src) for src in candidate.evidence.get("sources", [])]
    if "primary" in sources:
        score += 0.12
    if "tangent" in sources:
        score += 0.08
    if "idf" in sources:
        score += 0.05
    if "gamma_min" in sources:
        score += 0.02
    if len(sources) >= 2:
        score += 0.05

    lc_status = _point_text(point, "lc_reliability_status").lower()
    if lc_status == "usable":
        score += 0.10
    elif lc_status == "low_confidence":
        score -= 0.10
        reasons.append("low_lc_confidence")
    elif lc_status == "diagnostic_only":
        score -= 0.60
        reasons.append("diagnostic_only")

    melt_status = _point_text(point, "melting_window_status").lower()
    if melt_status == "outside_window":
        score += 0.10
    elif melt_status == "near_onset":
        score -= 0.15
        reasons.append("near_melting_onset")
    elif melt_status == "within_window":
        score -= 0.50
        reasons.append("within_melting_window")
    elif melt_status == "post_end":
        score -= 0.90
        reasons.append("post_melting_window")

    if getattr(point, "warnings", None):
        score -= 0.15
        reasons.append("frame_analysis_warning")

    q_star = _num(getattr(point, "Q_star", np.nan))
    if np.isfinite(q_star) and (q_star > 50.0 or (0 < q_star < 0.5)):
        score -= 0.15
        reasons.append("q_invariant_anomaly")

    if np.isfinite(spread) and spread > 0.35:
        score -= 0.10
        reasons.append("method_conflict")

    candidate.score_local = float(score)
    candidate.reject_reasons = _clean_reason_bits(reasons)
    candidate.evidence["score_local"] = float(score)
    candidate.evidence["score_reasons"] = list(candidate.reject_reasons)
    return float(score), candidate.reject_reasons


def _transition_score(prev_state: _PathState, curr_state: _PathState) -> float:
    if prev_state.is_none and curr_state.is_none:
        return 0.0
    if prev_state.is_none or curr_state.is_none:
        return -0.15

    prev = _num(prev_state.value_nm)
    curr = _num(curr_state.value_nm)
    if not np.isfinite(prev) or not np.isfinite(curr) or prev <= 0 or curr <= 0:
        return -0.50

    rel_jump = abs(float(np.log(curr / prev)))
    score = -0.65 * rel_jump
    if rel_jump < 0.10:
        score += 0.20
    elif rel_jump < 0.20:
        score += 0.08
    elif rel_jump > 0.45:
        score -= 0.15
    return float(score)


def _path_status_for_decision(point: Any, decision: LcPathDecision) -> str:
    if decision.candidate_count == 0:
        return "no_path"
    if not np.isfinite(decision.selected_value_nm):
        return "diagnostic_only"

    lc_status = _point_text(point, "lc_reliability_status").lower()
    melt_status = _point_text(point, "melting_window_status").lower()
    margin = decision.selection_margin if np.isfinite(decision.selection_margin) else float("-inf")

    if margin >= 0.55 and lc_status == "usable" and melt_status in {"outside_window", "undetermined"}:
        return "usable"
    if margin >= 0.15:
        return "low_confidence"
    if lc_status == "usable" and melt_status in {"outside_window", "undetermined"}:
        return "low_confidence"
    return "diagnostic_only"


def _path_reason_for_decision(point: Any, decision: LcPathDecision) -> str:
    if decision.candidate_count == 0:
        return "no_lc_candidates"
    if not np.isfinite(decision.selected_value_nm):
        return "path_prefers_none"

    reasons: List[str] = []
    if decision.selected_source:
        reasons.append(f"selected={decision.selected_source}")
    if np.isfinite(decision.selected_score):
        reasons.append(f"candidate_score={decision.selected_score:.3f}")
    if np.isfinite(decision.selection_margin):
        reasons.append(f"selection_margin={decision.selection_margin:.3f}")
    lc_status = _point_text(point, "lc_reliability_status").lower()
    if lc_status:
        reasons.append(f"frame_lc_status={lc_status}")
    melt_status = _point_text(point, "melting_window_status").lower()
    if melt_status:
        reasons.append(f"melting_window={melt_status}")
    if decision.candidates:
        candidate = next((cand for cand in decision.candidates if cand.source == decision.selected_source), None)
        if candidate is not None:
            reasons.extend(candidate.reject_reasons)
    return "|".join(_clean_reason_bits(reasons))


def select_lc_sequence_path(points: Sequence[Any]) -> List[LcPathDecision]:
    """Select a sequence-consistent lc path across a temperature series."""
    if not points:
        return []

    frame_candidates: List[List[LcCandidate]] = []
    frame_states: List[List[_PathState]] = []
    for point in points:
        candidates = build_lc_candidates(point)
        frame_candidates.append(candidates)
        median_value = _candidate_median(candidates)
        spread = _candidate_spread(candidates)

        states: List[_PathState] = []
        for candidate in candidates:
            score, _ = _score_candidate(
                point,
                candidate,
                median_value=median_value,
                spread=spread,
            )
            states.append(
                _PathState(
                    label=candidate.source,
                    value_nm=float(candidate.value_nm),
                    score_local=float(score),
                    is_none=False,
                    candidate=candidate,
                )
            )

        states.append(
            _PathState(
                label="none",
                value_nm=np.nan,
                score_local=_score_none_state(point, len(candidates), spread),
                is_none=True,
                candidate=None,
            )
        )
        frame_states.append(states)

    n_frames = len(points)
    backpointers: List[List[int]] = [[-1] * len(frame_states[0])]
    dp_scores = [state.score_local for state in frame_states[0]]

    for frame_idx in range(1, n_frames):
        prev_states = frame_states[frame_idx - 1]
        curr_states = frame_states[frame_idx]
        new_scores = [float("-inf")] * len(curr_states)
        new_back = [-1] * len(curr_states)

        for curr_idx, curr_state in enumerate(curr_states):
            best_prev_score = float("-inf")
            best_prev_idx = -1
            for prev_idx, prev_state in enumerate(prev_states):
                transition = _transition_score(prev_state, curr_state)
                total = dp_scores[prev_idx] + curr_state.score_local + transition
                if total > best_prev_score:
                    best_prev_score = total
                    best_prev_idx = prev_idx
            new_scores[curr_idx] = best_prev_score
            new_back[curr_idx] = best_prev_idx

        dp_scores = new_scores
        backpointers.append(new_back)

    best_final_idx = int(np.argmax(np.asarray(dp_scores, dtype=float)))
    selected_indices = [best_final_idx]
    for frame_idx in range(n_frames - 1, 0, -1):
        best_final_idx = backpointers[frame_idx][best_final_idx]
        if best_final_idx < 0:
            best_final_idx = len(frame_states[frame_idx - 1]) - 1
        selected_indices.append(best_final_idx)
    selected_indices.reverse()

    selected_values: List[float] = []
    for frame_idx, state_idx in enumerate(selected_indices):
        state = frame_states[frame_idx][state_idx]
        selected_values.append(float(state.value_nm) if not state.is_none else np.nan)

    decisions: List[LcPathDecision] = []
    for idx, point in enumerate(points):
        state_idx = selected_indices[idx]
        state = frame_states[idx][state_idx]
        candidates = frame_candidates[idx]
        none_score = next((s.score_local for s in frame_states[idx] if s.is_none), float("nan"))
        local_margin = float(state.score_local - none_score) if np.isfinite(state.score_local) and np.isfinite(none_score) else np.nan

        neighbor_bonus = 0.0
        prev_value = None
        next_value = None
        for prev_idx in range(idx - 1, -1, -1):
            prev_value = selected_values[prev_idx]
            if np.isfinite(prev_value):
                break
            prev_value = None
        for next_idx in range(idx + 1, len(selected_values)):
            next_value = selected_values[next_idx]
            if np.isfinite(next_value):
                break
            next_value = None
        if np.isfinite(state.value_nm):
            if prev_value is not None and prev_value > 0:
                rel_jump = abs(float(np.log(state.value_nm / prev_value)))
                if rel_jump < 0.08:
                    neighbor_bonus += 0.25
                elif rel_jump < 0.18:
                    neighbor_bonus += 0.12
                elif rel_jump > 0.40:
                    neighbor_bonus -= 0.18
            if next_value is not None and next_value > 0:
                rel_jump = abs(float(np.log(next_value / state.value_nm)))
                if rel_jump < 0.08:
                    neighbor_bonus += 0.25
                elif rel_jump < 0.18:
                    neighbor_bonus += 0.12
                elif rel_jump > 0.40:
                    neighbor_bonus -= 0.18

        selection_margin = local_margin + neighbor_bonus if np.isfinite(local_margin) else np.nan
        selected_value = float(state.value_nm) if not state.is_none else np.nan
        selected_source = state.label if not state.is_none else ""
        selected_score = float(state.score_local) if np.isfinite(state.score_local) else np.nan
        decision = LcPathDecision(
            temperature_C=_num(getattr(point, "temperature_C", np.nan)),
            selected_value_nm=selected_value,
            selected_source=selected_source,
            selected_score=selected_score,
            selection_margin=selection_margin,
            candidate_count=len(candidates),
            candidates=candidates,
        )
        decision.status = _path_status_for_decision(point, decision)
        decision.reason = _path_reason_for_decision(point, decision)
        decisions.append(decision)

    return decisions


def apply_lc_path_decisions(points: Sequence[Any], decisions: Sequence[LcPathDecision]) -> None:
    """Write selected path decisions back onto frame-like objects."""
    for point, decision in zip(points, decisions):
        setattr(point, "lc_candidates", list(decision.candidates))
        setattr(point, "lc_candidate_selected_nm", decision.selected_value_nm)
        setattr(point, "lc_candidate_selected_source", decision.selected_source)
        setattr(point, "lc_candidate_selected_score", decision.selected_score)
        setattr(point, "lc_effective_nm", decision.selected_value_nm)
        setattr(point, "lc_effective_source", decision.selected_source)
        setattr(point, "lc_effective_score", decision.selected_score)
        setattr(point, "lc_path_status", decision.status)
        setattr(point, "lc_path_reason", decision.reason)
        setattr(point, "lc_candidate_count", decision.candidate_count)
