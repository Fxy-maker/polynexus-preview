from __future__ import annotations

from typing import Any

from polynexus.core.dsc_action_registry import (
    actions_for_symptoms as dsc_actions_for_symptoms,
)
from polynexus.core.dsc_action_registry import (
    allowed_changes_for_actions as dsc_allowed_changes_for_actions,
)
from polynexus.core.ir_action_registry import actions_for_symptoms as ir_actions_for_symptoms
from polynexus.core.ir_action_registry import (
    allowed_changes_for_actions as ir_allowed_changes_for_actions,
)
from polynexus.core.saxs_action_registry import actions_for_symptoms as saxs_actions_for_symptoms
from polynexus.core.saxs_action_registry import (
    allowed_changes_for_actions as saxs_allowed_changes_for_actions,
)
from polynexus.core.waxs_temperature_action_registry import (
    actions_for_symptoms as waxs_temperature_actions_for_symptoms,
)
from polynexus.core.waxs_temperature_action_registry import (
    allowed_changes_for_actions as waxs_temperature_allowed_changes_for_actions,
)


SAXS_LOW_Q_PRIORITY_SYMPTOMS = {
    "beamstop_or_low_q_contamination",
    "low_q_void_dominant",
    "strain_void_lamellar_conflict",
    "lamellar_anchor_lost_under_strain",
    "qstar_rel_without_lamellar_support",
    "orientation_shift_breaks_lamellar_comparison",
    "idf_artifact_regular_spacing",
    "gamma_tangent_unstable",
    "temperature_calibration_fallback_active",
    "batch_summary_conflicts_with_frame_evidence",
    "thickness_chain_unreliable",
}

SAXS_LOW_Q_FIRST_ACTION_ORDER = (
    "adjust_q_crop",
    "adjust_corr_window",
    "adjust_idf_smoothing",
)

SAXS_LOW_Q_SUPPORT_ACTION_ORDER = (
    "rerun_condition_recovery",
    "mark_frame_outlier",
    "split_batch_by_sample",
)


def _allowed_actions(self: Any, symptoms: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if self.technique not in {"dsc", "ir", "saxs", "waxs"}:
        return []
    if self.technique == "dsc":
        return dsc_actions_for_symptoms(symptoms, technique="DSC")
    if self.technique == "ir":
        return ir_actions_for_symptoms(symptoms, technique="IR")
    if self.technique == "waxs" and self._submodule_id() in {"waxs.temperature", "waxs.in_situ_temp"}:
        return waxs_temperature_actions_for_symptoms(symptoms, technique="WAXS.TEMPERATURE")
    actions = saxs_actions_for_symptoms(symptoms, technique=self.technique.upper())
    if not actions:
        return []

    if self.technique != "saxs":
        return actions

    symptom_names = set(self._symptom_names(symptoms))
    low_q_first = bool(symptom_names & SAXS_LOW_Q_PRIORITY_SYMPTOMS)
    fallback_conflict_active = bool(
        "temperature_calibration_fallback_active" in symptom_names
        and (
            "batch_summary_conflicts_with_frame_evidence" in symptom_names
            or "thickness_chain_unreliable" in symptom_names
        )
    )

    prioritized_names = set(SAXS_LOW_Q_FIRST_ACTION_ORDER)
    support_names = set(SAXS_LOW_Q_SUPPORT_ACTION_ORDER)
    deferred_names = {"switch_lorentz_method", "raise_tangent_floor"}

    if fallback_conflict_active:
        actions = [
            action for action in actions if str(action.get("name", "") or "").strip() not in deferred_names
        ]

    if not low_q_first:
        return actions

    def _rank(action: dict[str, Any]) -> tuple[int, int, int, str]:
        name = str(action.get("name", "") or "").strip()
        if name in SAXS_LOW_Q_FIRST_ACTION_ORDER:
            lane = 0
            slot = SAXS_LOW_Q_FIRST_ACTION_ORDER.index(name)
        elif name in SAXS_LOW_Q_SUPPORT_ACTION_ORDER:
            lane = 1
            slot = SAXS_LOW_Q_SUPPORT_ACTION_ORDER.index(name)
        elif name in prioritized_names:
            lane = 0
            slot = 99
        elif name in support_names:
            lane = 1
            slot = 99
        else:
            lane = 2
            slot = 99
        return (
            lane,
            slot,
            -int(action.get("priority", 0) or 0),
            name,
        )

    actions.sort(key=_rank)
    return actions


def _allowed_changes(self: Any, allowed_actions: list[dict[str, Any]] | None) -> dict[str, list[Any]]:
    if self.technique not in {"dsc", "ir", "saxs", "waxs"}:
        return {}
    if self.technique == "dsc":
        return dsc_allowed_changes_for_actions(allowed_actions, technique="DSC")
    if self.technique == "ir":
        return ir_allowed_changes_for_actions(allowed_actions, technique="IR")
    if self.technique == "waxs" and self._submodule_id() in {"waxs.temperature", "waxs.in_situ_temp"}:
        return waxs_temperature_allowed_changes_for_actions(allowed_actions, technique="WAXS.TEMPERATURE")
    return saxs_allowed_changes_for_actions(allowed_actions, technique=self.technique.upper())
