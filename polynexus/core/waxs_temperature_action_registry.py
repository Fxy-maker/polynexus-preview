from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from polynexus.config_bridge import WAXS_PARAM_MAP


@dataclass(frozen=True)
class WAXSTemperatureActionSpec:
    name: str
    label: str
    summary: str
    target_symptoms: tuple[str, ...]
    allowed_params: tuple[str, ...]
    expected_evidence_change: tuple[str, ...] = ()
    priority: int = 0
    technique: str = "WAXS.TEMPERATURE"

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


WAXS_TEMPERATURE_ACTION_SPECS: tuple[WAXSTemperatureActionSpec, ...] = (
    WAXSTemperatureActionSpec(
        name="adjust_peak_position",
        label="Adjust peak position",
        summary="Nudge the WAXS peak placement when the temperature series still shows a left/right bias.",
        target_symptoms=(
            "peak_position_bias",
            "offset_sensitive_solution",
        ),
        allowed_params=("two_theta_offset", "peak_function", "peak_distance"),
        expected_evidence_change=(
            "peak positions should converge",
            "residual_type should move toward random",
        ),
        priority=6,
    ),
    WAXSTemperatureActionSpec(
        name="increase_peak_capacity",
        label="Increase peak capacity",
        summary="Allow the fitter to represent an underfit peak family with a slightly larger search budget.",
        target_symptoms=(
            "peak_count_underfit",
            "peak_visibility",
            "peak_count_insufficient",
        ),
        allowed_params=("peak_distance", "max_peaks"),
        expected_evidence_change=(
            "peak count should rise",
            "supporting peak regions should narrow",
        ),
        priority=5,
    ),
    WAXSTemperatureActionSpec(
        name="reduce_peak_capacity",
        label="Reduce peak capacity",
        summary="Simplify an overfit peak family before the model starts chasing noise or halo detail.",
        target_symptoms=("peak_count_overfit",),
        allowed_params=("max_peaks", "peak_distance"),
        expected_evidence_change=(
            "peak count should fall",
            "peak family should simplify",
        ),
        priority=4,
    ),
    WAXSTemperatureActionSpec(
        name="rebalance_background_partition",
        label="Rebalance background partition",
        summary="Tighten the amorphous/background split when crystallinity still depends too much on halo shape.",
        target_symptoms=("amorphous_background_bias", "amorphous_partition_unstable"),
        allowed_params=("background_method", "amorphous_subtraction", "amorphous_n_peaks"),
        expected_evidence_change=(
            "background-related residuals should weaken",
            "crystallinity should stop depending on halo shape",
        ),
        priority=6,
    ),
    WAXSTemperatureActionSpec(
        name="stabilize_peak_shape",
        label="Stabilize peak shape",
        summary="Switch peak shape handling when shoulders and peak core disagree.",
        target_symptoms=(
            "peak_width_mismatch",
            "peak_family_unstable",
            "peak_width_nonphysical",
        ),
        allowed_params=("peak_function", "smooth_window"),
        expected_evidence_change=(
            "shoulders and peak core should agree better",
            "peak widths should stabilize",
        ),
        priority=5,
    ),
    WAXSTemperatureActionSpec(
        name="trim_low_angle_drift",
        label="Trim low-angle drift",
        summary="Fix the low-angle background first when the beamstop side still dominates the mismatch.",
        target_symptoms=(
            "low_angle_background_drift",
            "offset_sensitive_solution",
        ),
        allowed_params=("background_method", "amorphous_subtraction", "two_theta_offset"),
        expected_evidence_change=(
            "low-angle residuals should weaken",
            "max_residual_region should move away from beamstop",
        ),
        priority=6,
    ),
    WAXSTemperatureActionSpec(
        name="recover_temperature_axis",
        label="Recover temperature axis",
        summary="Recover an explicit temperature axis before reading the sequence as a physical temperature scan.",
        target_symptoms=(
            "temperature_axis_missing",
            "temperature_axis_low_confidence",
        ),
        allowed_params=(),
        expected_evidence_change=(
            "temperature axis confidence should rise",
            "sequence ordering should become explicit and traceable",
        ),
        priority=10,
    ),
    WAXSTemperatureActionSpec(
        name="split_temperature_series",
        label="Split temperature series",
        summary="Separate mixed heating and cooling paths before trusting one shared trend line.",
        target_symptoms=(
            "mixed_heating_cooling_sequence",
            "mixed_sample_temperature_series",
            "temperature_sequence_nonmonotonic",
        ),
        allowed_params=(),
        expected_evidence_change=(
            "heating and cooling paths should stop being conflated",
            "temperature monotonicity should become easier to interpret",
        ),
        priority=9,
    ),
    WAXSTemperatureActionSpec(
        name="stabilize_peak_family_tracking",
        label="Stabilize peak family tracking",
        summary="Keep peak-family identity stable before promoting a trend across temperature.",
        target_symptoms=(
            "peak_family_identity_swap",
            "peak_family_track_fragmented",
            "peak_family_missing_too_many_frames",
        ),
        allowed_params=("peak_distance", "peak_function", "smooth_window"),
        expected_evidence_change=(
            "peak-family continuity should improve",
            "identity swaps should weaken",
        ),
        priority=9,
    ),
    WAXSTemperatureActionSpec(
        name="rebalance_temperature_background",
        label="Rebalance temperature background",
        summary="Repair background and amorphous partitioning before using Xc as a trend line.",
        target_symptoms=(
            "crystallinity_background_driven",
            "crystallinity_trend_conflicts_with_peak_area",
            "crystallinity_trend_without_peak_support",
            "amorphous_partition_unstable",
        ),
        allowed_params=("background_method", "amorphous_subtraction", "amorphous_n_peaks"),
        expected_evidence_change=(
            "background sensitivity should drop",
            "Xc should rely more on peak support than on halo shape",
        ),
        priority=8,
    ),
    WAXSTemperatureActionSpec(
        name="stabilize_temperature_peak_shape",
        label="Stabilize temperature peak shape",
        summary="Reduce peak-width noise before trusting the Scherrer trend.",
        target_symptoms=(
            "scherrer_dominated_by_peak_width_noise",
            "scherrer_unphysical_temperature_trend",
            "peak_width_trend_unstable",
        ),
        allowed_params=("peak_function", "smooth_window", "peak_distance"),
        expected_evidence_change=(
            "D trend support should rise",
            "width drift should become smaller and more consistent",
        ),
        priority=8,
    ),
    WAXSTemperatureActionSpec(
        name="mark_temperature_frame_outlier",
        label="Mark temperature frame outlier",
        summary="Isolate a single unstable frame when one point poisons the whole trend.",
        target_symptoms=(
            "crystallinity_jump_single_frame",
            "scherrer_jump_single_frame",
            "temperature_axis_low_confidence",
        ),
        allowed_params=(),
        expected_evidence_change=(
            "single-frame jumps should stop dominating the trend",
            "sequence continuity should improve after isolating the bad frame",
        ),
        priority=7,
    ),
    WAXSTemperatureActionSpec(
        name="promote_transition_candidate",
        label="Promote transition candidate",
        summary="Keep a temperature transition tentative until peak-family and trend evidence agree.",
        target_symptoms=(
            "phase_transition_without_peak_family_support",
            "melting_trend_without_peak_disappearance",
            "cold_crystallization_without_new_peak_support",
        ),
        allowed_params=(),
        expected_evidence_change=(
            "transition support should be based on multiple frames and peak families",
            "candidate transition points should stay tentative until corroborated",
        ),
        priority=7,
    ),
)


def _normalize_technique(technique: str | None) -> str | None:
    text = str(technique or "").strip().upper()
    return text or None


def _specs_for_technique(technique: str | None) -> tuple[WAXSTemperatureActionSpec, ...]:
    technique_key = _normalize_technique(technique)
    if technique_key in {None, "WAXS.TEMPERATURE", "WAXS.IN_SITU_TEMP"}:
        return WAXS_TEMPERATURE_ACTION_SPECS
    return ()


def _param_map_for_technique(technique: str | None) -> dict[str, Any]:
    technique_key = _normalize_technique(technique)
    if technique_key in {None, "WAXS.TEMPERATURE", "WAXS.IN_SITU_TEMP"}:
        return WAXS_PARAM_MAP
    return WAXS_PARAM_MAP


def get_action_spec(name: str, technique: str | None = None) -> dict[str, Any] | None:
    spec = _SPEC_BY_NAME.get(str(name or "").strip())
    if spec is None:
        return None
    technique_key = _normalize_technique(technique)
    if technique_key and spec.technique.upper() != technique_key:
        return None
    return spec.to_dict()


def list_actions() -> list[dict[str, Any]]:
    return [item.to_dict() for item in WAXS_TEMPERATURE_ACTION_SPECS]


def actions_for_symptoms(
    symptoms: list[dict[str, Any]] | None,
    technique: str | None = None,
) -> list[dict[str, Any]]:
    symptom_names = {
        str(item.get("name", "")).strip()
        for item in (symptoms or [])
        if isinstance(item, dict) and str(item.get("name", "")).strip()
    }
    if not symptom_names:
        return []

    out: list[dict[str, Any]] = []
    for spec in _specs_for_technique(technique):
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
            if rule.constraint is None:
                allowed[name] = []
            else:
                allowed[name] = list(rule.constraint)
    return allowed


_SPEC_BY_NAME = {item.name: item for item in WAXS_TEMPERATURE_ACTION_SPECS}
