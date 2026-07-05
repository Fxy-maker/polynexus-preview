from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from polynexus.config_bridge import DSC_PARAM_MAP


@dataclass(frozen=True)
class DSCActionSpec:
    name: str
    label: str
    summary: str
    target_symptoms: tuple[str, ...]
    allowed_params: tuple[str, ...]
    expected_evidence_change: tuple[str, ...] = ()
    priority: int = 0
    technique: str = "DSC"

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


DSC_ACTION_SPECS: tuple[DSCActionSpec, ...] = (
    DSCActionSpec(
        name="stabilize_baseline",
        label="Stabilize baseline",
        summary="Repair baseline handling before trusting Tg/Tm/Tc interpretation.",
        target_symptoms=(
            "baseline_sensitive_result",
            "baseline_drift_low_t",
            "baseline_drift_high_t",
        ),
        allowed_params=("baseline_type", "smooth_window"),
        expected_evidence_change=(
            "baseline-related warnings should weaken",
            "thermal-event evidence should stop being steered by drift",
        ),
        priority=9,
    ),
    DSCActionSpec(
        name="align_polarity",
        label="Align polarity",
        summary="Make the scan convention explicit before using signed enthalpy or exo/endo interpretation.",
        target_symptoms=(
            "event_polarity_conflict",
            "exo_up_down_confusion",
        ),
        allowed_params=("exo_up", "baseline_type"),
        expected_evidence_change=(
            "signed enthalpy should stop contradicting the event",
            "polarity-related warnings should disappear",
        ),
        priority=10,
    ),
    DSCActionSpec(
        name="restore_tg_support",
        label="Restore Tg support",
        summary="Re-center the Tg search window before promoting Tg as stable.",
        target_symptoms=(
            "Tg_without_DCp_step",
            "Tg_outside_supported_window",
        ),
        allowed_params=("tg_search_low_C", "tg_search_high_C", "baseline_type"),
        expected_evidence_change=(
            "Tg support should become clearer",
            "DCp should stop looking flat inside the active window",
        ),
        priority=8,
    ),
    DSCActionSpec(
        name="tighten_melting_window",
        label="Tighten melting window",
        summary="Re-center the melting support before trusting the reported Tm.",
        target_symptoms=(
            "melting_without_supported_event",
            "melting_peak_shift",
            "event_window_too_narrow",
            "event_window_too_wide",
        ),
        allowed_params=("tm_search_low_C", "tm_search_high_C", "peak_function", "max_melting_peak_width_C"),
        expected_evidence_change=(
            "Tm_peak_C should align better",
            "melting-window support should stop spilling into the wrong region",
        ),
        priority=8,
    ),
    DSCActionSpec(
        name="separate_cold_crystallization",
        label="Separate cold crystallization",
        summary="Separate cold crystallisation from the melting window before reusing the result.",
        target_symptoms=(
            "cold_crystallization_conflicts_with_melting",
            "cold_crystallization_overlap",
            "multi_event_underfit",
            "segment_split_issue",
        ),
        allowed_params=("tc_search_low_C", "tc_search_high_C", "tm_search_low_C", "peak_function"),
        expected_evidence_change=(
            "Tcc and Tm should separate more cleanly",
            "the event windows should stop overlapping",
        ),
        priority=7,
    ),
    DSCActionSpec(
        name="strengthen_event_detection",
        label="Strengthen event detection",
        summary="Make weak event detection stricter before promoting crystallinity or quality claims.",
        target_symptoms=(
            "peak_components_too_sparse",
            "peak_width_nonphysical",
            "crystallinity_without_event_support",
            "quality_score_without_event_support",
        ),
        allowed_params=("peak_prominence_ratio", "min_event_enthalpy_Jg", "max_melting_peak_width_C", "smooth_window"),
        expected_evidence_change=(
            "marginal events should stop driving the conclusion",
            "peak width and enthalpy support should become more physical",
        ),
        priority=6,
    ),
    DSCActionSpec(
        name="stabilize_scan_consistency",
        label="Stabilize scan consistency",
        summary="Keep the scan-to-scan evidence consistent before accepting the file-level result.",
        target_symptoms=(
            "multi_scan_inconsistent",
            "noise_dominant",
        ),
        allowed_params=("baseline_type", "smooth_window", "peak_prominence_ratio"),
        expected_evidence_change=(
            "scan-to-scan warnings should weaken",
            "noise should stop dominating the thermal-event path",
        ),
        priority=6,
    ),
)


def _normalize_technique(technique: str | None) -> str | None:
    text = str(technique or "").strip().upper()
    return text or None


def _specs_for_technique(technique: str | None) -> tuple[DSCActionSpec, ...]:
    technique_key = _normalize_technique(technique)
    if technique_key in {None, "DSC"}:
        return DSC_ACTION_SPECS
    return ()


def _param_map_for_technique(technique: str | None) -> dict[str, Any]:
    technique_key = _normalize_technique(technique)
    if technique_key == "DSC" or technique_key is None:
        return DSC_PARAM_MAP
    return DSC_PARAM_MAP


def get_action_spec(name: str, technique: str | None = None) -> dict[str, Any] | None:
    spec = _SPEC_BY_NAME.get(str(name or "").strip())
    if spec is None:
        return None
    technique_key = _normalize_technique(technique)
    if technique_key and spec.technique.upper() != technique_key:
        return None
    return spec.to_dict()


def list_dsc_actions() -> list[dict[str, Any]]:
    return [item.to_dict() for item in DSC_ACTION_SPECS]


def actions_for_symptoms(
    symptoms: list[dict[str, Any]] | None,
    technique: str | None = None,
) -> list[dict[str, Any]]:
    technique_key = _normalize_technique(technique)
    if technique_key not in {None, "DSC"}:
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
            if rule.constraint is None:
                allowed[name] = []
            else:
                allowed[name] = list(rule.constraint)
    return allowed


_SPEC_BY_NAME = {item.name: item for item in DSC_ACTION_SPECS}
