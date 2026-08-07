from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from polynexus.config_bridge import SAXS_PARAM_MAP, WAXS_PARAM_MAP


@dataclass(frozen=True)
class SAXSActionSpec:
    name: str
    label: str
    summary: str
    target_symptoms: tuple[str, ...]
    allowed_params: tuple[str, ...]
    expected_evidence_change: tuple[str, ...] = ()
    priority: int = 0
    technique: str = "SAXS"

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


SAXS_ACTION_SPECS: tuple[SAXSActionSpec, ...] = (
    SAXSActionSpec(
        name="rebalance_background_scale",
        label="Rebalance background scale",
        summary="Adjust only the scale of a real manually configured background profile.",
        target_symptoms=("background_drift", "negative_intensity_excess"),
        allowed_params=("bg_scale_value",),
        expected_evidence_change=(
            "background residuals should weaken",
            "negative intensity should remain bounded",
        ),
        priority=6,
    ),
    SAXSActionSpec(
        name="reduce_profile_noise",
        label="Reduce profile noise",
        summary="Adjust segment-safe smoothing without changing measured metadata.",
        target_symptoms=("noise_dominant", "high_frequency_residual"),
        allowed_params=("smooth_method", "smooth_span", "savgol_window", "savgol_order"),
        expected_evidence_change=(
            "residual noise should weaken",
            "q-peak and Guinier support should remain stable",
        ),
        priority=5,
    ),
    SAXSActionSpec(
        name="adjust_q_crop",
        label="Adjust q crop",
        summary="Tighten or widen low-q/high-q coverage when contamination or truncation dominates the fit.",
        target_symptoms=(
            "beamstop_or_low_q_contamination",
            "low_q_void_dominant",
            "strain_void_lamellar_conflict",
            "lamellar_anchor_lost_under_strain",
            "qstar_rel_without_lamellar_support",
            "batch_summary_conflicts_with_frame_evidence",
            "thickness_chain_unreliable",
        ),
        allowed_params=("q_bragg_min", "q_bragg_max", "q_corr_min", "q_corr_max"),
        expected_evidence_change=(
            "beam_stop_contaminated should clear or be isolated",
            "Q_star_valid should stabilize",
        ),
        priority=4,
    ),
    SAXSActionSpec(
        name="adjust_peak_window",
        label="Adjust peak window",
        summary="Re-center the Bragg search window before trusting long-period peak placement.",
        target_symptoms=(
            "peak_window_mismatch",
            "multi_method_disagreement",
        ),
        allowed_params=("q_bragg_min", "q_bragg_max", "savgol_window"),
        expected_evidence_change=(
            "peak-region residuals should weaken",
            "q_peak_diff_pct should shrink",
        ),
        priority=5,
    ),
    SAXSActionSpec(
        name="adjust_corr_window",
        label="Adjust correlation window",
        summary="Stabilize the correlation or IDF fit region before reading Lc or long-period transforms.",
        target_symptoms=(
            "idf_artifact_regular_spacing",
            "gamma_tangent_unstable",
            "multi_method_disagreement",
            "batch_summary_conflicts_with_frame_evidence",
            "thickness_chain_unreliable",
            "strain_void_lamellar_conflict",
            "lamellar_anchor_lost_under_strain",
            "qstar_rel_without_lamellar_support",
            "orientation_shift_breaks_lamellar_comparison",
        ),
        allowed_params=("q_corr_min", "q_corr_max", "savgol_window"),
        expected_evidence_change=(
            "correlation-region fit should stabilize",
            "L_corr_peak and L_bragg should move closer",
        ),
        priority=5,
    ),
    SAXSActionSpec(
        name="adjust_idf_smoothing",
        label="Adjust IDF smoothing",
        summary="Use a narrower smoothing move when oscillation looks numerical rather than structural.",
        target_symptoms=(
            "idf_artifact_regular_spacing",
            "gamma_tangent_unstable",
            "beamstop_or_low_q_contamination",
            "thickness_chain_unreliable",
            "low_q_void_dominant",
        ),
        allowed_params=("savgol_window", "savgol_order", "idf_peak_rel_thresh", "idf_valley_rel_thresh"),
        expected_evidence_change=(
            "correlation/idf zero-crossings should drop",
            "lc_tangent_nm and lc_idf_nm should stop diverging",
        ),
        priority=4,
    ),
    SAXSActionSpec(
        name="switch_lorentz_method",
        label="Switch Lorentz backend",
        summary="Change the long-period fit backend only when method disagreement persists.",
        target_symptoms=(
            "multi_method_disagreement",
            "gamma_tangent_unstable",
        ),
        allowed_params=("lorentz_fit_method",),
        expected_evidence_change=(
            "L_confidence should rise as methods converge",
        ),
        priority=2,
    ),
    SAXSActionSpec(
        name="raise_tangent_floor",
        label="Raise tangent floor",
        summary="Protect the tangent-derived crystal thickness from implausibly small values.",
        target_symptoms=(
            "gamma_tangent_unstable",
        ),
        allowed_params=("tangent_lc_min_nm",),
        expected_evidence_change=(
            "lc_tangent_nm should stay in a plausible range",
        ),
        priority=2,
    ),
    SAXSActionSpec(
        name="rerun_condition_recovery",
        label="Recover condition axis",
        summary="Recover missing or weak temperature/strain context before another sequence optimization round.",
        target_symptoms=(
            "condition_axis_missing",
            "condition_axis_unstable",
            "strain_axis_low_confidence",
            "temperature_calibration_fallback_active",
        ),
        allowed_params=(),
        expected_evidence_change=(
            "condition_missing_frames should drop",
            "condition_confidence should rise",
        ),
        priority=6,
    ),
    SAXSActionSpec(
        name="split_batch_by_sample",
        label="Split mixed batch",
        summary="Separate mixed-sample folders before trusting one shared trend line.",
        target_symptoms=(
            "batch_mixed_samples",
        ),
        allowed_params=(),
        expected_evidence_change=(
            "each batch should resolve to one sample identity",
        ),
        priority=6,
    ),
    SAXSActionSpec(
        name="mark_frame_outlier",
        label="Mark frame outlier",
        summary="Exclude an obviously broken frame when one local artifact is poisoning the sequence.",
        target_symptoms=(
            "idf_artifact_regular_spacing",
        ),
        allowed_params=(),
        expected_evidence_change=(
            "sequence continuity should improve after isolating the bad frame",
        ),
        priority=1,
    ),
)

def _normalize_technique(technique: str | None) -> str | None:
    text = str(technique or "").strip().upper()
    return text or None


def _all_action_specs() -> tuple[SAXSActionSpec, ...]:
    return (*SAXS_ACTION_SPECS, *WAXS_ACTION_SPECS)


def _specs_for_technique(technique: str | None) -> tuple[SAXSActionSpec, ...]:
    technique_key = _normalize_technique(technique)
    if technique_key == "SAXS":
        return SAXS_ACTION_SPECS
    if technique_key == "WAXS":
        return WAXS_ACTION_SPECS
    return SAXS_ACTION_SPECS
_PARAM_MAP_BY_TECHNIQUE = {
    "SAXS": SAXS_PARAM_MAP,
    "WAXS": WAXS_PARAM_MAP,
}


def _param_map_for_technique(technique: str | None) -> dict[str, Any]:
    technique_key = _normalize_technique(technique)
    if technique_key in _PARAM_MAP_BY_TECHNIQUE:
        return _PARAM_MAP_BY_TECHNIQUE[technique_key]
    return SAXS_PARAM_MAP


def get_action_spec(name: str, technique: str | None = None) -> dict[str, Any] | None:
    spec = _SPEC_BY_NAME.get(str(name or "").strip())
    if spec is None:
        return None
    technique_key = _normalize_technique(technique)
    if technique_key and spec.technique.upper() != technique_key:
        return None
    return spec.to_dict()


def get_saxs_action_spec(name: str) -> dict[str, Any] | None:
    return get_action_spec(name, technique="SAXS")


def get_waxs_action_spec(name: str) -> dict[str, Any] | None:
    return get_action_spec(name, technique="WAXS")


def list_saxs_actions() -> list[dict[str, Any]]:
    return [item.to_dict() for item in SAXS_ACTION_SPECS]


def list_waxs_actions() -> list[dict[str, Any]]:
    return [item.to_dict() for item in WAXS_ACTION_SPECS]


def actions_for_symptoms_for_technique(
    symptoms: list[dict[str, Any]] | None,
    *,
    technique: str | None,
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


def actions_for_symptoms(symptoms: list[dict[str, Any]] | None, technique: str | None = None) -> list[dict[str, Any]]:
    return actions_for_symptoms_for_technique(symptoms, technique=technique)


def allowed_changes_for_actions(actions: list[dict[str, Any]] | None, technique: str | None = None) -> dict[str, list[Any]]:
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


WAXS_ACTION_SPECS: tuple[SAXSActionSpec, ...] = (
    SAXSActionSpec(
        name="adjust_peak_position",
        label="Adjust peak position",
        summary="Nudge the WAXS peak placement when the residual shows a clear left/right bias around the Bragg family.",
        target_symptoms=("peak_position_bias", "offset_sensitive_solution"),
        allowed_params=("two_theta_offset", "peak_function", "peak_distance"),
        expected_evidence_change=(
            "peak positions should converge",
            "residual_type should move toward random",
        ),
        priority=6,
        technique="WAXS",
    ),
    SAXSActionSpec(
        name="increase_peak_capacity",
        label="Increase peak capacity",
        summary="Allow the fitter to represent an underfit peak family with a slightly larger search budget.",
        target_symptoms=("peak_count_underfit", "peak_visibility", "peak_count_insufficient"),
        allowed_params=("peak_distance", "max_peaks"),
        expected_evidence_change=(
            "peak count should rise",
            "supporting peak regions should narrow",
        ),
        priority=5,
        technique="WAXS",
    ),
    SAXSActionSpec(
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
        technique="WAXS",
    ),
    SAXSActionSpec(
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
        technique="WAXS",
    ),
    SAXSActionSpec(
        name="stabilize_peak_shape",
        label="Stabilize peak shape",
        summary="Switch peak shape handling when shoulders and peak core disagree.",
        target_symptoms=("peak_width_mismatch", "peak_family_unstable", "peak_width_nonphysical"),
        allowed_params=("peak_function", "smooth_window"),
        expected_evidence_change=(
            "shoulders and peak core should agree better",
            "peak widths should stabilize",
        ),
        priority=5,
        technique="WAXS",
    ),
    SAXSActionSpec(
        name="trim_low_angle_drift",
        label="Trim low-angle drift",
        summary="Fix the low-angle background first when the beamstop side still dominates the mismatch.",
        target_symptoms=("low_angle_background_drift", "offset_sensitive_solution"),
        allowed_params=("background_method", "amorphous_subtraction", "two_theta_offset"),
        expected_evidence_change=(
            "low-angle residuals should weaken",
            "max_residual_region should move away from beamstop",
        ),
        priority=6,
        technique="WAXS",
    ),
)

_SPEC_BY_NAME = {item.name: item for item in _all_action_specs()}
