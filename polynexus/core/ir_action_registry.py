from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from polynexus.config_bridge import IR_PARAM_MAP


@dataclass(frozen=True)
class IRActionSpec:
    name: str
    label: str
    summary: str
    target_symptoms: tuple[str, ...]
    allowed_params: tuple[str, ...]
    expected_evidence_change: tuple[str, ...] = ()
    priority: int = 0
    technique: str = "IR"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label,
            "summary": self.summary,
            "target_symptoms": list(self.target_symptoms),
            "allowed_params": list(self.allowed_params),
            "expected_evidence_change": list(self.expected_evidence_change),
            "priority": self.priority,
            "technique": self.technique,
        }


IR_ACTION_SPECS: tuple[IRActionSpec, ...] = (
    IRActionSpec(
        name="repair_sequence_axis",
        label="Repair sequence axis",
        summary="Recover an explicit perturbation order before trusting 2D IR trend or Noda-order interpretation.",
        target_symptoms=(
            "sequence_axis_incomplete",
            "temperature_axis_missing",
            "stage_order_ambiguous",
            "hold_time_missing_or_estimated",
            "insufficient_perturbation_frames",
        ),
        allowed_params=("wavenumber_min", "wavenumber_max", "sequence_axis_mode", "sequence_axis_metadata_path"),
        expected_evidence_change=(
            "sequence axis should become more explicit and traceable",
            "temperature / stage ordering should stop driving artificial 2D-COS structure",
        ),
        priority=7,
    ),
    IRActionSpec(
        name="stabilize_matrix_baseline",
        label="Stabilize matrix baseline",
        summary="Repair matrix-level baseline and scaling before re-reading 2D-COS peaks.",
        target_symptoms=(
            "negative_matrix_fraction_high",
            "matrix_nan_fraction_high",
            "frame_intensity_scale_unstable",
            "wavenumber_grid_inconsistent",
        ),
        allowed_params=("baseline_method", "normalization_method", "smooth_window"),
        expected_evidence_change=(
            "negative / NaN-heavy matrix regions should weaken",
            "matrix quality score should rise before cross-peak interpretation is promoted",
        ),
        priority=8,
    ),
    IRActionSpec(
        name="recover_dynamic_signal",
        label="Recover dynamic signal",
        summary="Protect temperature-driven signal changes before asking the model to interpret 2D-COS structure.",
        target_symptoms=(
            "dynamic_signal_too_weak",
            "weak_cos_signal",
        ),
        allowed_params=("baseline_method", "normalization_method", "smooth_window"),
        expected_evidence_change=(
            "dynamic RMS should rise into a stable range",
            "sync / async cross peaks should stop depending on amplified noise",
        ),
        priority=7,
    ),
    IRActionSpec(
        name="denoise_2dcos",
        label="Denoise 2D-COS",
        summary="Suppress noisy near-diagonal or weakly supported cross peaks before discussing mechanistic order.",
        target_symptoms=(
            "cross_peak_near_diagonal",
            "weak_cos_signal",
        ),
        allowed_params=("smooth_window", "cross_peak_exclusion_cm1"),
        expected_evidence_change=(
            "top peaks should move away from the diagonal clutter",
            "cross-peak ranking should become more repeatable",
        ),
        priority=6,
    ),
    IRActionSpec(
        name="stabilize_band_tracking",
        label="Stabilize band tracking",
        summary="Stabilize band-index transitions before promoting the temperature trend as reproducible.",
        target_symptoms=(
            "band_index_jump_single_frame",
            "band_index_denominator_unstable",
            "transition_single_frame_only",
            "band_tracking_missing_key_band",
            "temperature_trend_not_reproducible",
        ),
        allowed_params=("peak_fit_window_cm1", "peak_distance", "smooth_window"),
        expected_evidence_change=(
            "band-index changes should be supported by multiple tracked bands",
            "transition support should persist across adjacent frames",
        ),
        priority=7,
    ),
    IRActionSpec(
        name="tighten_cross_peak_assignment",
        label="Tighten cross-peak assignment",
        summary="Require cross peaks to align with known reference bands before using them in 2D IR interpretation.",
        target_symptoms=(
            "cross_peak_without_band_assignment",
            "async_peak_without_sync_support",
            "noda_rule_not_applicable",
        ),
        allowed_params=("assignment_tolerance_cm1", "cross_peak_exclusion_cm1"),
        expected_evidence_change=(
            "assigned cross-peak count should rise",
            "async peaks should gain explicit sync support before Noda-rule interpretation is promoted",
        ),
        priority=8,
    ),
    IRActionSpec(
        name="rebalance_baseline",
        label="Rebalance baseline",
        summary="Stabilize baseline handling before trusting band assignments or crystallinity reads.",
        target_symptoms=(
            "baseline_drift_low_wn",
            "baseline_drift_high_wn",
            "baseline_drift",
            "normalization_bias",
            "baseline_sensitive_assignment",
        ),
        allowed_params=("baseline_method", "normalization_method", "smooth_window"),
        expected_evidence_change=(
            "baseline-related residuals should weaken",
            "assignment confidence should stop depending on preprocessing drift",
        ),
        priority=6,
    ),
    IRActionSpec(
        name="reduce_noise",
        label="Reduce noise",
        summary="Use a slightly broader smoothing move when the residual looks jagged rather than structural.",
        target_symptoms=(
            "noise_dominant",
            "noise",
        ),
        allowed_params=("smooth_window",),
        expected_evidence_change=(
            "sign flips should drop",
            "weak bands should stop oscillating",
        ),
        priority=5,
    ),
    IRActionSpec(
        name="tighten_key_band_fit",
        label="Tighten key-band fit",
        summary="Narrow the local fit window before re-judging the characteristic bands.",
        target_symptoms=(
            "key_band_mismatch",
            "peak_mismatch",
            "assignment_without_characteristic_bands",
            "key_band_support_insufficient",
            "polymer_score_without_assignment_support",
        ),
        allowed_params=("peak_fit_window_cm1", "peak_prominence_min", "peak_height_min"),
        expected_evidence_change=(
            "key-band hits should rise",
            "assignment confidence should align with band coverage",
        ),
        priority=6,
    ),
    IRActionSpec(
        name="separate_crowded_bands",
        label="Separate crowded bands",
        summary="Spread crowded bands before asking the model to classify them as distinct assignments.",
        target_symptoms=(
            "crowded_band_underfit",
            "overcrowded_band_separation_unstable",
            "key_band_mismatch",
            "peak_mismatch",
        ),
        allowed_params=("peak_distance", "lineshape"),
        expected_evidence_change=(
            "peak families should separate cleanly",
            "peak widths should stabilize",
        ),
        priority=5,
    ),
    IRActionSpec(
        name="lift_weak_band_support",
        label="Lift weak-band support",
        summary="Recover weak reference bands without promoting the conclusion too early.",
        target_symptoms=(
            "weak_peak_only_support",
            "over_smoothed_weak_bands",
            "crystallinity_index_without_band_support",
            "polymer_score_without_assignment_support",
        ),
        allowed_params=("peak_height_min", "peak_prominence_min", "normalization_method"),
        expected_evidence_change=(
            "reference-band hits should rise",
            "weak-band support should become visible before the conclusion is promoted",
        ),
        priority=4,
    ),
    IRActionSpec(
        name="expand_band_window",
        label="Expand band window",
        summary="Widen the analysis window when key bands are being clipped at the spectral edges.",
        target_symptoms=(
            "key_band_support_insufficient",
            "assignment_without_characteristic_bands",
            "key_band_mismatch",
        ),
        allowed_params=("wavenumber_min", "wavenumber_max"),
        expected_evidence_change=(
            "clipped key bands should re-enter the analysis window",
        ),
        priority=3,
    ),
)


def _normalize_technique(technique: str | None) -> str | None:
    text = str(technique or "").strip().upper()
    return text or None


def _specs_for_technique(technique: str | None) -> tuple[IRActionSpec, ...]:
    technique_key = _normalize_technique(technique)
    if technique_key in {None, "IR"}:
        return IR_ACTION_SPECS
    return ()


def _param_map_for_technique(technique: str | None) -> dict[str, Any]:
    technique_key = _normalize_technique(technique)
    if technique_key == "IR" or technique_key is None:
        return IR_PARAM_MAP
    return IR_PARAM_MAP


def get_action_spec(name: str, technique: str | None = None) -> dict[str, Any] | None:
    spec = _SPEC_BY_NAME.get(str(name or "").strip())
    if spec is None:
        return None
    technique_key = _normalize_technique(technique)
    if technique_key and spec.technique.upper() != technique_key:
        return None
    return spec.to_dict()


def list_ir_actions() -> list[dict[str, Any]]:
    return [item.to_dict() for item in IR_ACTION_SPECS]


def actions_for_symptoms(
    symptoms: list[dict[str, Any]] | None,
    technique: str | None = None,
) -> list[dict[str, Any]]:
    technique_key = _normalize_technique(technique)
    if technique_key not in {None, "IR"}:
        return []

    symptom_names = {
        str(item.get("name", "")).strip()
        for item in (symptoms or [])
        if isinstance(item, dict) and str(item.get("name", "")).strip()
    }
    if not symptom_names:
        return []

    out: list[dict[str, Any]] = []
    for spec in _specs_for_technique(technique_key):
        matched = [name for name in spec.target_symptoms if name in symptom_names]
        if not matched:
            continue
        payload = spec.to_dict()
        payload["matched_symptoms"] = matched
        out.append(payload)

    out.sort(
        key=lambda item: (
            -int(item.get("priority", 0) or 0),
            -len(item.get("matched_symptoms", [])),
            str(item.get("name", "")),
        )
    )
    return out


def allowed_changes_for_actions(
    actions: list[dict[str, Any]] | None,
    technique: str | None = None,
) -> dict[str, list[Any]]:
    allowed: dict[str, list[Any]] = {}
    for action in actions or []:
        if not isinstance(action, dict):
            continue
        action_technique = _normalize_technique(action.get("technique")) or _normalize_technique(technique)
        param_map = _param_map_for_technique(action_technique)
        for param_name in action.get("allowed_params", []):
            name = str(param_name or "").strip()
            rule = param_map.get(name)
            if not name or rule is None or name in allowed:
                continue
            allowed[name] = list(rule.constraint)
    return allowed


_SPEC_BY_NAME = {item.name: item for item in IR_ACTION_SPECS}
