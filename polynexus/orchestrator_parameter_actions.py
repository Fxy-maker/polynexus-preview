from __future__ import annotations

import math
from copy import deepcopy
from typing import Any

from polynexus.config_bridge import DSC_PARAM_MAP, IR_PARAM_MAP, SAXS_PARAM_MAP, WAXS_PARAM_MAP


def _guard_technique_direct_changes(
    self: Any,
    changes: dict[str, Any],
    allowed_changes: dict[str, list[Any]],
    current_config: dict[str, Any],
    param_map: dict[str, Any],
    technique_label: str,
) -> tuple[dict[str, Any], str]:
    if not isinstance(changes, dict) or not changes:
        return {}, ""

    # Keep SAXS tightly action-gated, but let WAXS direct tuning explore
    # any known config field and rely on scoring / rollback to veto bad trials.
    if allowed_changes and technique_label == "SAXS":
        disallowed = [str(name) for name in changes.keys() if str(name) not in allowed_changes]
        if disallowed:
            joined = ", ".join(disallowed)
            return {}, f"Advisor changes are outside the current {technique_label} action whitelist: {joined}."

    normalized: dict[str, Any] = {}
    for name, value in changes.items():
        param_name = str(name or "").strip()
        if not param_name or param_name not in param_map:
            return {}, f"Advisor changes include an unknown {technique_label} parameter: {param_name or name}."
        candidate_value = self._normalize_candidate_value(param_name, value, param_map)
        current_value = self._current_config_value(current_config, param_name, param_map)
        if self._candidate_values_equal(candidate_value, current_value):
            continue
        normalized[param_name] = candidate_value
    return normalized, ""


def _guard_saxs_direct_changes(
    self: Any,
    changes: dict[str, Any],
    allowed_changes: dict[str, list[Any]],
    current_config: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    return self._guard_technique_direct_changes(
        changes,
        allowed_changes,
        current_config,
        SAXS_PARAM_MAP,
        "SAXS",
    )


def _candidate_plans_for_action(
    self: Any,
    *,
    action_name: str,
    current_config: dict[str, Any],
    allowed_changes: dict[str, list[Any]],
    action_spec: dict[str, Any],
    target_symptom: str,
    reason: str,
    expected_evidence_change: str,
) -> list[dict[str, Any]]:
    if self.technique == "saxs" and action_name == "rerun_condition_recovery":
        recovery_context = self._saxs_recovery_context(current_config)
        expected = expected_evidence_change.strip() if expected_evidence_change else ""
        if not expected:
            expected_items = action_spec.get("expected_evidence_change", [])
            if isinstance(expected_items, list) and expected_items:
                expected = " | ".join(
                    str(item or "").strip()
                    for item in expected_items
                    if str(item or "").strip()
                )
        if recovery_context:
            return [
                {
                    "action_name": action_name,
                    "label": str(
                        action_spec.get("label", action_name.replace("_", " ").title()) or ""
                    ).strip(),
                    "reason": reason,
                    "target_symptom": target_symptom,
                    "expected_evidence_change": expected,
                    "changes": {},
                    "recovery_context": recovery_context,
                    "executable": True,
                }
            ]
        return [
            {
                "action_name": action_name,
                "label": str(
                    action_spec.get("label", action_name.replace("_", " ").title()) or ""
                ).strip(),
                "reason": reason,
                "target_symptom": target_symptom,
                "expected_evidence_change": expected,
                "changes": {},
                "recovery_context": {},
                "executable": False,
                "skip_reason": "Action 'rerun_condition_recovery' did not find a recoverable condition_context in the current SAXS config.",
            }
        ]
    if self.technique == "waxs" and self._submodule_id() in {"waxs.temperature", "waxs.in_situ_temp"}:
        raw_candidates = self._waxs_temperature_action_candidates(action_name, current_config)
        if raw_candidates:
            return self._candidate_plans_from_raw_candidates(
                action_name=action_name,
                current_config=current_config,
                allowed_changes=allowed_changes,
                allowed_params=[
                    str(item or "").strip()
                    for item in action_spec.get("allowed_params", [])
                    if str(item or "").strip()
                ],
                action_spec=action_spec,
                target_symptom=target_symptom,
                reason=reason,
                expected=expected_evidence_change.strip() if expected_evidence_change else "",
                raw_candidates=raw_candidates,
                param_map=WAXS_PARAM_MAP,
                technique_label="WAXS temperature",
            )
        return [
            {
                "action_name": action_name,
                "label": str(
                    action_spec.get("label", action_name.replace("_", " ").title()) or ""
                ).strip(),
                "reason": reason,
                "target_symptom": target_symptom,
                "expected_evidence_change": expected_evidence_change.strip()
                if expected_evidence_change
                else "",
                "changes": {},
                "executable": False,
                "skip_reason": f"Action '{action_name}' is advisory-only for WAXS temperature and has no direct config edit in the current engine.",
            }
        ]
    if self.technique == "waxs":
        return self._candidate_plans_for_waxs_action(
            action_name=action_name,
            current_config=current_config,
            allowed_changes=allowed_changes,
            action_spec=action_spec,
            target_symptom=target_symptom,
            reason=reason,
            expected_evidence_change=expected_evidence_change,
        )
    if self.technique == "ir":
        return self._candidate_plans_for_ir_action(
            action_name=action_name,
            current_config=current_config,
            allowed_changes=allowed_changes,
            action_spec=action_spec,
            target_symptom=target_symptom,
            reason=reason,
            expected_evidence_change=expected_evidence_change,
        )
    if self.technique == "dsc":
        return self._candidate_plans_for_dsc_action(
            action_name=action_name,
            current_config=current_config,
            allowed_changes=allowed_changes,
            action_spec=action_spec,
            target_symptom=target_symptom,
            reason=reason,
            expected_evidence_change=expected_evidence_change,
        )

    allowed_params = [
        str(item or "").strip()
        for item in action_spec.get("allowed_params", [])
        if str(item or "").strip()
    ]
    label = str(action_spec.get("label", action_name.replace("_", " ").title()) or "").strip()
    expected = expected_evidence_change.strip() if expected_evidence_change else ""
    if not expected:
        expected_items = action_spec.get("expected_evidence_change", [])
        if isinstance(expected_items, list) and expected_items:
            expected = " | ".join(
                str(item or "").strip()
                for item in expected_items
                if str(item or "").strip()
            )

    if not allowed_params:
        return [
            {
                "action_name": action_name,
                "label": label,
                "reason": reason,
                "target_symptom": target_symptom,
                "expected_evidence_change": expected,
                "changes": {},
                "executable": False,
                "skip_reason": f"Action '{action_name}' is recognized, but this orchestrator pass cannot execute it automatically yet.",
            }
        ]

    raw_candidates: list[dict[str, Any]] = []
    if action_name == "adjust_peak_window":
        raw_candidates = self._saxs_range_action_candidates(
            current_config,
            "q_bragg_min",
            "q_bragg_max",
            inward_first=True,
        )
    elif action_name == "adjust_corr_window":
        raw_candidates = self._saxs_range_action_candidates(
            current_config,
            "q_corr_min",
            "q_corr_max",
            inward_first=True,
        )
    elif action_name == "adjust_q_crop":
        raw_candidates = self._saxs_crop_action_candidates(current_config)
    elif action_name == "adjust_idf_smoothing":
        raw_candidates = self._saxs_idf_smoothing_candidates(current_config)
    elif action_name == "switch_lorentz_method":
        current_method = str(current_config.get("lorentz_fit_method", "") or "").strip()
        choices = SAXS_PARAM_MAP["lorentz_fit_method"].constraint
        for choice in choices:
            if str(choice) == current_method:
                continue
            raw_candidates.append({"lorentz_fit_method": str(choice)})
    elif action_name == "raise_tangent_floor":
        current_value = self._safe_float(current_config.get("tangent_lc_min_nm", 2.0))
        raw_candidates.append({"tangent_lc_min_nm": current_value + 0.5})
        raw_candidates.append({"tangent_lc_min_nm": current_value + 1.0})

    return self._candidate_plans_from_raw_candidates(
        action_name=action_name,
        current_config=current_config,
        allowed_changes=allowed_changes,
        allowed_params=allowed_params,
        action_spec=action_spec,
        target_symptom=target_symptom,
        reason=reason,
        expected=expected,
        raw_candidates=raw_candidates,
        param_map=SAXS_PARAM_MAP,
        technique_label="SAXS",
    )


def _saxs_recovery_context(self: Any, current_config: dict[str, Any]) -> dict[str, Any]:
    context: dict[str, Any] = {}
    if isinstance(current_config, dict):
        cfg_context = current_config.get("condition_context", {})
        if isinstance(cfg_context, dict) and cfg_context:
            context = deepcopy(cfg_context)
    workspace_context = self.workspace_context if isinstance(self.workspace_context, dict) else {}
    if isinstance(workspace_context, dict) and workspace_context:
        for key in ("condition_context", "sample", "batch", "condition_values"):
            value = workspace_context.get(key)
            if not value:
                continue
            if key == "condition_context" and isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if sub_key not in context or context[sub_key] in (None, "", {}, []):
                        context[sub_key] = deepcopy(sub_value)
                continue
            if key not in context or context[key] in (None, "", {}, []):
                context[key] = deepcopy(value)
    return context


def _candidate_plans_for_ir_action(
    self: Any,
    *,
    action_name: str,
    current_config: dict[str, Any],
    allowed_changes: dict[str, list[Any]],
    action_spec: dict[str, Any],
    target_symptom: str,
    reason: str,
    expected_evidence_change: str,
) -> list[dict[str, Any]]:
    allowed_params = [
        str(item or "").strip()
        for item in action_spec.get("allowed_params", [])
        if str(item or "").strip()
    ]
    expected = expected_evidence_change.strip() if expected_evidence_change else ""
    if not expected:
        expected_items = action_spec.get("expected_evidence_change", [])
        if isinstance(expected_items, list) and expected_items:
            expected = " | ".join(
                str(item or "").strip()
                for item in expected_items
                if str(item or "").strip()
            )

    raw_candidates: list[dict[str, Any]] = []
    if action_name == "rebalance_baseline":
        raw_candidates = self._ir_baseline_candidates(current_config)
    elif action_name == "reduce_noise":
        raw_candidates = self._ir_noise_candidates(current_config)
    elif action_name == "tighten_key_band_fit":
        raw_candidates = self._ir_key_band_candidates(current_config)
    elif action_name == "separate_crowded_bands":
        raw_candidates = self._ir_crowded_band_candidates(current_config)
    elif action_name == "lift_weak_band_support":
        raw_candidates = self._ir_weak_support_candidates(current_config)
    elif action_name == "expand_band_window":
        raw_candidates = self._ir_band_window_candidates(current_config)
    elif action_name == "repair_sequence_axis":
        raw_candidates = self._ir_band_window_candidates(current_config)
    elif action_name == "stabilize_matrix_baseline":
        raw_candidates = self._ir_baseline_candidates(current_config)
    elif action_name == "recover_dynamic_signal":
        raw_candidates = self._ir_dynamic_signal_candidates(current_config)
    elif action_name == "denoise_2dcos":
        raw_candidates = self._ir_2dcos_denoise_candidates(current_config)
    elif action_name == "stabilize_band_tracking":
        raw_candidates = self._ir_band_tracking_candidates(current_config)
    elif action_name == "tighten_cross_peak_assignment":
        raw_candidates = self._ir_cross_peak_assignment_candidates(current_config)

    return self._candidate_plans_from_raw_candidates(
        action_name=action_name,
        current_config=current_config,
        allowed_changes=allowed_changes,
        allowed_params=allowed_params,
        action_spec=action_spec,
        target_symptom=target_symptom,
        reason=reason,
        expected=expected,
        raw_candidates=raw_candidates,
        param_map=IR_PARAM_MAP,
        technique_label="IR",
    )


def _candidate_plans_for_waxs_action(
    self: Any,
    *,
    action_name: str,
    current_config: dict[str, Any],
    allowed_changes: dict[str, list[Any]],
    action_spec: dict[str, Any],
    target_symptom: str,
    reason: str,
    expected_evidence_change: str,
) -> list[dict[str, Any]]:
    allowed_params = [
        str(item or "").strip()
        for item in action_spec.get("allowed_params", [])
        if str(item or "").strip()
    ]
    expected = expected_evidence_change.strip() if expected_evidence_change else ""
    if not expected:
        expected_items = action_spec.get("expected_evidence_change", [])
        if isinstance(expected_items, list) and expected_items:
            expected = " | ".join(
                str(item or "").strip()
                for item in expected_items
                if str(item or "").strip()
            )

    raw_candidates = self._waxs_action_candidates(action_name, current_config)
    return self._candidate_plans_from_raw_candidates(
        action_name=action_name,
        current_config=current_config,
        allowed_changes=allowed_changes,
        allowed_params=allowed_params,
        action_spec=action_spec,
        target_symptom=target_symptom,
        reason=reason,
        expected=expected,
        raw_candidates=raw_candidates,
        param_map=WAXS_PARAM_MAP,
        technique_label="WAXS",
    )


def _candidate_plans_for_dsc_action(
    self: Any,
    *,
    action_name: str,
    current_config: dict[str, Any],
    allowed_changes: dict[str, list[Any]],
    action_spec: dict[str, Any],
    target_symptom: str,
    reason: str,
    expected_evidence_change: str,
) -> list[dict[str, Any]]:
    allowed_params = [
        str(item or "").strip()
        for item in action_spec.get("allowed_params", [])
        if str(item or "").strip()
    ]
    expected = expected_evidence_change.strip() if expected_evidence_change else ""
    if not expected:
        expected_items = action_spec.get("expected_evidence_change", [])
        if isinstance(expected_items, list) and expected_items:
            expected = " | ".join(
                str(item or "").strip()
                for item in expected_items
                if str(item or "").strip()
            )

    raw_candidates = self._dsc_action_candidates(action_name, current_config)
    return self._candidate_plans_from_raw_candidates(
        action_name=action_name,
        current_config=current_config,
        allowed_changes=allowed_changes,
        allowed_params=allowed_params,
        action_spec=action_spec,
        target_symptom=target_symptom,
        reason=reason,
        expected=expected,
        raw_candidates=raw_candidates,
        param_map=DSC_PARAM_MAP,
        technique_label="DSC",
    )


def _candidate_plans_from_raw_candidates(
    self: Any,
    *,
    action_name: str,
    current_config: dict[str, Any],
    allowed_changes: dict[str, list[Any]],
    allowed_params: list[str],
    action_spec: dict[str, Any],
    target_symptom: str,
    reason: str,
    expected: str,
    raw_candidates: list[dict[str, Any]],
    param_map: dict[str, Any],
    technique_label: str,
) -> list[dict[str, Any]]:
    label = str(action_spec.get("label", action_name.replace("_", " ").title()) or "").strip()
    plans: list[dict[str, Any]] = []
    for raw_changes in raw_candidates:
        candidate_changes: dict[str, Any] = {}
        skip_reason = ""
        for param_name, value in raw_changes.items():
            if allowed_changes and param_name not in allowed_changes:
                skip_reason = f"Action '{action_name}' proposed '{param_name}', which is outside the current {technique_label} action whitelist."
                break
            if allowed_params and param_name not in allowed_params:
                skip_reason = f"Action '{action_name}' proposed '{param_name}', which is outside the registry spec."
                break
            candidate_value = self._normalize_candidate_value(param_name, value, param_map)
            current_value = self._current_config_value(current_config, param_name, param_map)
            if self._candidate_values_equal(candidate_value, current_value):
                continue
            candidate_changes[param_name] = candidate_value
        if skip_reason:
            plans.append(
                {
                    "action_name": action_name,
                    "label": label,
                    "reason": reason,
                    "target_symptom": target_symptom,
                    "expected_evidence_change": expected,
                    "changes": {},
                    "executable": False,
                    "skip_reason": skip_reason,
                }
            )
            continue
        if not candidate_changes:
            continue
        plans.append(
            {
                "action_name": action_name,
                "label": label,
                "reason": reason,
                "target_symptom": target_symptom,
                "expected_evidence_change": expected,
                "changes": candidate_changes,
                "executable": True,
            }
        )

    if not plans:
        plans.append(
            {
                "action_name": action_name,
                "label": label,
                "reason": reason,
                "target_symptom": target_symptom,
                "expected_evidence_change": expected,
                "changes": {},
                "executable": False,
                "skip_reason": f"Action '{action_name}' did not produce a valid guarded {technique_label} candidate from the current config.",
            }
        )
    return plans


def _current_config_value(
    self: Any,
    current_config: dict[str, Any],
    param_name: str,
    param_map: dict[str, Any],
) -> Any:
    if not isinstance(current_config, dict):
        return None
    if param_name in current_config:
        return current_config.get(param_name)
    rule = param_map.get(param_name)
    if rule is not None:
        field_name = getattr(rule, "field_name", "")
        if field_name and field_name in current_config:
            return current_config.get(field_name)
    return current_config.get(param_name)


def _dsc_action_candidates(
    self: Any,
    action_name: str,
    current_config: dict[str, Any],
) -> list[dict[str, Any]]:
    baseline_choices = [
        choice for choice in DSC_PARAM_MAP["baseline_type"].constraint if isinstance(choice, str)
    ]
    peak_choices = [
        choice for choice in DSC_PARAM_MAP["peak_function"].constraint if isinstance(choice, str)
    ]
    tg_method_choices = [
        choice for choice in DSC_PARAM_MAP["Tg_method"].constraint if isinstance(choice, str)
    ]
    baseline = str(
        current_config.get("baseline_type", current_config.get("baseline_corr", "")) or ""
    ).strip()
    peak_function = str(current_config.get("peak_function", "") or "").strip()
    exo_up = bool(current_config.get("exo_up", True))
    smooth_window = int(round(self._safe_float(current_config.get("smooth_window", 11)) or 11))
    tg_low = (
        self._safe_float(
            current_config.get("tg_search_low_C", current_config.get("Tg_search_low_C", 20.0))
        )
        or 20.0
    )
    tg_high = (
        self._safe_float(
            current_config.get(
                "tg_search_high_C",
                current_config.get("Tg_search_high_C", 120.0),
            )
        )
        or 120.0
    )
    tm_low = (
        self._safe_float(
            current_config.get("tm_search_low_C", current_config.get("Tm_search_low_C", 100.0))
        )
        or 100.0
    )
    tm_high = (
        self._safe_float(
            current_config.get(
                "tm_search_high_C",
                current_config.get("Tm_search_high_C", 300.0),
            )
        )
        or 300.0
    )
    tc_low = (
        self._safe_float(
            current_config.get("tc_search_low_C", current_config.get("Tc_search_low_C", 50.0))
        )
        or 50.0
    )
    tc_high = (
        self._safe_float(
            current_config.get(
                "tc_search_high_C",
                current_config.get("Tc_search_high_C", 250.0),
            )
        )
        or 250.0
    )
    prom = self._safe_float(current_config.get("peak_prominence_ratio", 0.03)) or 0.03
    enthalpy = self._safe_float(current_config.get("min_event_enthalpy_Jg", 0.05)) or 0.05
    max_width = self._safe_float(current_config.get("max_melting_peak_width_C", 50.0)) or 50.0

    candidates: list[dict[str, Any]] = []
    if action_name == "stabilize_baseline":
        for choice in baseline_choices:
            if choice != baseline:
                candidates.append({"baseline_type": choice})
                break
        candidates.append(
            {
                "smooth_window": (
                    smooth_window + 2 if smooth_window < 31 else max(3, smooth_window - 2)
                )
            }
        )
    elif action_name == "align_polarity":
        candidates.append({"exo_up": not exo_up})
        for choice in baseline_choices:
            if choice != baseline:
                candidates.append({"baseline_type": choice})
                break
    elif action_name == "restore_tg_support":
        width = max(10.0, min(35.0, (tg_high - tg_low) * 0.2))
        center = (tg_low + tg_high) / 2.0
        candidates.append({"tg_search_low_C": max(0.0, center - width)})
        candidates.append({"tg_search_high_C": min(240.0, center + width)})
        for choice in tg_method_choices:
            if choice != str(current_config.get("Tg_method", "") or "").strip():
                candidates.append({"Tg_method": choice})
                break
    elif action_name == "tighten_melting_window":
        center = (tm_low + tm_high) / 2.0
        span = max(25.0, min(80.0, (tm_high - tm_low) * 0.75))
        candidates.append({"tm_search_low_C": max(50.0, center - span / 2.0)})
        candidates.append({"tm_search_high_C": min(380.0, center + span / 2.0)})
        for choice in peak_choices:
            if choice != peak_function:
                candidates.append({"peak_function": choice})
                break
    elif action_name == "separate_cold_crystallization":
        candidates.append({"tc_search_low_C": max(0.0, tc_low - 10.0)})
        candidates.append({"tc_search_high_C": min(320.0, tc_high + 10.0)})
        candidates.append({"tm_search_low_C": max(50.0, tm_low + 5.0)})
    elif action_name == "strengthen_event_detection":
        candidates.append({"peak_prominence_ratio": min(0.2, prom * 1.2)})
        candidates.append({"min_event_enthalpy_Jg": min(5.0, enthalpy * 1.2)})
        candidates.append({"max_melting_peak_width_C": max(5.0, max_width * 0.85)})
        candidates.append(
            {
                "smooth_window": (
                    smooth_window + 2 if smooth_window < 31 else max(3, smooth_window - 2)
                )
            }
        )
    elif action_name == "stabilize_scan_consistency":
        candidates.append(
            {
                "smooth_window": (
                    smooth_window + 2 if smooth_window < 31 else max(3, smooth_window - 2)
                )
            }
        )
        candidates.append({"peak_prominence_ratio": min(0.2, prom * 1.15)})
        candidates.append(
            {
                "baseline_type": (
                    baseline_choices[0]
                    if baseline_choices and baseline != baseline_choices[0]
                    else baseline_choices[1]
                    if len(baseline_choices) > 1
                    else baseline
                )
            }
        )
    return candidates[:4]


def _waxs_action_candidates(
    self: Any,
    action_name: str,
    current_config: dict[str, Any],
) -> list[dict[str, Any]]:
    if action_name == "adjust_peak_position":
        return self._waxs_peak_position_candidates(current_config)
    if action_name == "increase_peak_capacity":
        return self._waxs_peak_capacity_candidates(current_config, expand=True)
    if action_name == "reduce_peak_capacity":
        return self._waxs_peak_capacity_candidates(current_config, expand=False)
    if action_name == "rebalance_background_partition":
        return self._waxs_background_candidates(current_config)
    if action_name == "stabilize_peak_shape":
        return self._waxs_peak_shape_candidates(current_config)
    if action_name == "trim_low_angle_drift":
        return self._waxs_low_angle_candidates(current_config)
    return []


def _waxs_temperature_action_candidates(
    self: Any,
    action_name: str,
    current_config: dict[str, Any],
) -> list[dict[str, Any]]:
    if action_name == "stabilize_peak_family_tracking":
        return self._waxs_peak_shape_candidates(current_config)
    if action_name == "rebalance_temperature_background":
        return self._waxs_background_candidates(current_config)
    if action_name == "stabilize_temperature_peak_shape":
        return self._waxs_peak_shape_candidates(current_config)
    if action_name == "recover_temperature_axis":
        return []
    if action_name == "split_temperature_series":
        return []
    if action_name == "mark_temperature_frame_outlier":
        return []
    if action_name == "promote_transition_candidate":
        return []
    return []


def _waxs_peak_position_candidates(
    self: Any,
    current_config: dict[str, Any],
) -> list[dict[str, Any]]:
    offset = self._safe_float(current_config.get("two_theta_offset", 0.0))
    step = max(0.01, min(abs(offset) * 0.5 if offset else 0.04, 0.12))
    if offset > 0:
        toward_zero = {"two_theta_offset": offset - step}
        away_from_zero = {"two_theta_offset": offset + step}
    elif offset < 0:
        toward_zero = {"two_theta_offset": offset + step}
        away_from_zero = {"two_theta_offset": offset - step}
    else:
        toward_zero = {"two_theta_offset": step}
        away_from_zero = {"two_theta_offset": -step}
    return [toward_zero, away_from_zero]


def _waxs_peak_capacity_candidates(
    self: Any,
    current_config: dict[str, Any],
    *,
    expand: bool,
) -> list[dict[str, Any]]:
    max_peaks = int(round(self._safe_float(current_config.get("max_peaks", 8)) or 8))
    peak_distance = self._safe_float(current_config.get("peak_distance", 0.8))
    if expand:
        return [
            {"max_peaks": max_peaks + 1},
            {"max_peaks": max_peaks + 2},
            {"peak_distance": max(0.5, peak_distance - 0.08)},
        ]
    return [
        {"max_peaks": max(4, max_peaks - 1)},
        {"max_peaks": max(4, max_peaks - 2)},
        {"peak_distance": min(2.0, peak_distance + 0.08)},
    ]


def _waxs_background_candidates(
    self: Any,
    current_config: dict[str, Any],
) -> list[dict[str, Any]]:
    background_choices = [
        choice
        for choice in WAXS_PARAM_MAP["background_method"].constraint
        if isinstance(choice, str)
    ]
    amorphous_choices = [
        choice
        for choice in WAXS_PARAM_MAP["amorphous_subtraction"].constraint
        if isinstance(choice, str)
    ]
    current_background = str(current_config.get("background_method", "") or "").strip()
    current_amorphous = str(current_config.get("amorphous_subtraction", "") or "").strip()
    current_n_peaks = int(round(self._safe_float(current_config.get("amorphous_n_peaks", 2)) or 2))

    candidates: list[dict[str, Any]] = []
    for choice in background_choices:
        if choice != current_background:
            candidates.append({"background_method": choice})
            break
    for choice in amorphous_choices:
        if choice != current_amorphous:
            candidates.append({"amorphous_subtraction": choice})
            break
    candidates.append({"amorphous_n_peaks": 1 if current_n_peaks > 1 else 2})
    return candidates


def _waxs_peak_shape_candidates(
    self: Any,
    current_config: dict[str, Any],
) -> list[dict[str, Any]]:
    peak_choices = [
        choice for choice in WAXS_PARAM_MAP["peak_function"].constraint if isinstance(choice, str)
    ]
    current_peak = str(current_config.get("peak_function", "") or "").strip()
    current_window = int(round(self._safe_float(current_config.get("smooth_window", 5)) or 5))
    candidates: list[dict[str, Any]] = []
    for choice in peak_choices:
        if choice != current_peak:
            candidates.append({"peak_function": choice})
    candidates.append(
        {
            "smooth_window": (
                current_window + 2 if current_window < 13 else max(3, current_window - 2)
            )
        }
    )
    return candidates[:3]


def _waxs_low_angle_candidates(
    self: Any,
    current_config: dict[str, Any],
) -> list[dict[str, Any]]:
    offset = self._safe_float(current_config.get("two_theta_offset", 0.0))
    background_choices = [
        choice
        for choice in WAXS_PARAM_MAP["background_method"].constraint
        if isinstance(choice, str)
    ]
    amorphous_choices = [
        choice
        for choice in WAXS_PARAM_MAP["amorphous_subtraction"].constraint
        if isinstance(choice, str)
    ]
    current_background = str(current_config.get("background_method", "") or "").strip()
    current_amorphous = str(current_config.get("amorphous_subtraction", "") or "").strip()
    candidates: list[dict[str, Any]] = []
    if abs(offset) > 0.005:
        candidates.append({"two_theta_offset": offset - (offset * 0.5)})
    else:
        candidates.append({"two_theta_offset": 0.02})
    for choice in background_choices:
        if choice != current_background:
            candidates.append({"background_method": choice})
            break
    for choice in amorphous_choices:
        if choice != current_amorphous:
            candidates.append({"amorphous_subtraction": choice})
            break
    return candidates


def _ir_baseline_candidates(
    self: Any,
    current_config: dict[str, Any],
) -> list[dict[str, Any]]:
    baseline = str(current_config.get("baseline_method", "") or "").strip()
    normalization = str(current_config.get("normalization_method", "") or "").strip()
    smooth_window = int(round(self._safe_float(current_config.get("smooth_window", 7)) or 7))
    baseline_choices = [
        choice for choice in IR_PARAM_MAP["baseline_method"].constraint if isinstance(choice, str)
    ]
    normalization_choices = [
        choice
        for choice in IR_PARAM_MAP["normalization_method"].constraint
        if isinstance(choice, str)
    ]
    candidates: list[dict[str, Any]] = []
    for choice in baseline_choices:
        if choice != baseline:
            candidates.append({"baseline_method": choice})
            break
    for choice in normalization_choices:
        if choice != normalization:
            candidates.append({"normalization_method": choice})
            break
    if smooth_window % 2 == 0:
        smooth_window += 1
    candidates.append({"smooth_window": min(15, max(5, smooth_window + 2))})
    return candidates[:3]


def _ir_noise_candidates(
    self: Any,
    current_config: dict[str, Any],
) -> list[dict[str, Any]]:
    smooth_window = int(round(self._safe_float(current_config.get("smooth_window", 7)) or 7))
    if smooth_window % 2 == 0:
        smooth_window += 1
    larger = min(31, smooth_window + 2)
    if larger % 2 == 0:
        larger += 1
    return [
        {"smooth_window": larger},
        {"smooth_window": min(31, larger + 2 if larger < 31 else larger)},
    ]


def _ir_key_band_candidates(
    self: Any,
    current_config: dict[str, Any],
) -> list[dict[str, Any]]:
    fit_window = self._safe_float(current_config.get("peak_fit_window_cm1", 35.0)) or 35.0
    prominence = self._safe_float(current_config.get("peak_prominence_min", 0.015)) or 0.015
    height = self._safe_float(current_config.get("peak_height_min", 0.02)) or 0.02
    return [
        {"peak_fit_window_cm1": max(8.0, fit_window - 8.0)},
        {"peak_prominence_min": max(0.001, prominence * 0.8)},
        {"peak_height_min": max(0.001, height * 0.85)},
    ]


def _ir_crowded_band_candidates(
    self: Any,
    current_config: dict[str, Any],
) -> list[dict[str, Any]]:
    peak_distance = self._safe_float(current_config.get("peak_distance", 12.0)) or 12.0
    lineshape = str(current_config.get("lineshape", "") or "").strip()
    choices = [choice for choice in IR_PARAM_MAP["lineshape"].constraint if isinstance(choice, str)]
    candidates: list[dict[str, Any]] = []
    candidates.append({"peak_distance": min(80.0, peak_distance + 4.0)})
    for choice in choices:
        if choice != lineshape:
            candidates.append({"lineshape": choice})
            break
    return candidates[:3]


def _ir_weak_support_candidates(
    self: Any,
    current_config: dict[str, Any],
) -> list[dict[str, Any]]:
    height = self._safe_float(current_config.get("peak_height_min", 0.02)) or 0.02
    prominence = self._safe_float(current_config.get("peak_prominence_min", 0.015)) or 0.015
    normalization = str(current_config.get("normalization_method", "") or "").strip()
    choices = [
        choice
        for choice in IR_PARAM_MAP["normalization_method"].constraint
        if isinstance(choice, str)
    ]
    candidates: list[dict[str, Any]] = [
        {"peak_height_min": max(0.001, height * 0.9)},
        {"peak_prominence_min": max(0.001, prominence * 0.85)},
    ]
    for choice in choices:
        if choice != normalization:
            candidates.append({"normalization_method": choice})
            break
    return candidates[:3]


def _ir_band_window_candidates(
    self: Any,
    current_config: dict[str, Any],
) -> list[dict[str, Any]]:
    wn_min = self._safe_float(current_config.get("wavenumber_min", 400.0)) or 400.0
    wn_max = self._safe_float(current_config.get("wavenumber_max", 4000.0)) or 4000.0
    span = max(wn_max - wn_min, 100.0)
    step = max(25.0, min(span * 0.08, 150.0))
    return [
        {"wavenumber_min": max(350.0, wn_min - step)},
        {"wavenumber_max": min(4500.0, wn_max + step)},
    ]


def _ir_dynamic_signal_candidates(
    self: Any,
    current_config: dict[str, Any],
) -> list[dict[str, Any]]:
    baseline = str(current_config.get("baseline_method", "") or "").strip()
    normalization = str(current_config.get("normalization_method", "") or "").strip()
    smooth_window = int(round(self._safe_float(current_config.get("smooth_window", 7)) or 7))
    candidates: list[dict[str, Any]] = []
    if baseline != "mute_zone":
        candidates.append({"baseline_method": "mute_zone"})
    if normalization != "none":
        candidates.append({"normalization_method": "none"})
    smaller = max(3, smooth_window - 2)
    if smaller % 2 == 0:
        smaller += 1
    if smaller != smooth_window:
        candidates.append({"smooth_window": smaller})
    return candidates[:3]


def _ir_2dcos_denoise_candidates(
    self: Any,
    current_config: dict[str, Any],
) -> list[dict[str, Any]]:
    smooth_window = int(round(self._safe_float(current_config.get("smooth_window", 7)) or 7))
    exclusion = self._safe_float(current_config.get("cross_peak_exclusion_cm1", 35.0)) or 35.0
    larger = min(31, smooth_window + 2)
    if larger % 2 == 0:
        larger += 1
    return [
        {"smooth_window": larger},
        {"cross_peak_exclusion_cm1": min(80.0, exclusion + 5.0)},
    ]


def _ir_band_tracking_candidates(
    self: Any,
    current_config: dict[str, Any],
) -> list[dict[str, Any]]:
    peak_fit_window = self._safe_float(current_config.get("peak_fit_window_cm1", 18.0)) or 18.0
    peak_distance = self._safe_float(current_config.get("peak_distance", 18.0)) or 18.0
    smooth_window = int(round(self._safe_float(current_config.get("smooth_window", 7)) or 7))
    wider = min(31, smooth_window + 2)
    if wider % 2 == 0:
        wider += 1
    tighter_fit = max(8.0, peak_fit_window - 2.0)
    tighter_distance = max(8.0, peak_distance - 2.0)
    return [
        {"smooth_window": wider},
        {"peak_fit_window_cm1": tighter_fit},
        {"peak_distance": tighter_distance},
    ]


def _ir_cross_peak_assignment_candidates(
    self: Any,
    current_config: dict[str, Any],
) -> list[dict[str, Any]]:
    tolerance = self._safe_float(current_config.get("assignment_tolerance_cm1", 18.0)) or 18.0
    exclusion = self._safe_float(current_config.get("cross_peak_exclusion_cm1", 35.0)) or 35.0
    return [
        {"assignment_tolerance_cm1": min(30.0, tolerance + 2.0)},
        {"cross_peak_exclusion_cm1": min(80.0, exclusion + 5.0)},
        {"assignment_tolerance_cm1": max(5.0, tolerance - 2.0)},
    ]


def _saxs_range_action_candidates(
    self: Any,
    current_config: dict[str, Any],
    low_name: str,
    high_name: str,
    *,
    inward_first: bool,
) -> list[dict[str, Any]]:
    low_value = self._safe_float(current_config.get(low_name))
    high_value = self._safe_float(current_config.get(high_name))
    if high_value <= low_value:
        rule_low = SAXS_PARAM_MAP[low_name].constraint
        rule_high = SAXS_PARAM_MAP[high_name].constraint
        low_value = float(rule_low[0])
        high_value = float(rule_high[1])
    span = max(high_value - low_value, 0.04)
    step = max(0.01, min(span * 0.15, 0.08))
    inward = {
        low_name: low_value + step,
        high_name: high_value - step,
    }
    outward = {
        low_name: low_value - step,
        high_name: high_value + step,
    }
    return [inward, outward] if inward_first else [outward, inward]


def _saxs_crop_action_candidates(
    self: Any,
    current_config: dict[str, Any],
) -> list[dict[str, Any]]:
    q_bragg_min = self._safe_float(current_config.get("q_bragg_min", 0.15))
    q_bragg_max = self._safe_float(current_config.get("q_bragg_max", 0.9))
    q_corr_min = self._safe_float(current_config.get("q_corr_min", 0.15))
    q_corr_max = self._safe_float(current_config.get("q_corr_max", 1.2))
    low_step = max(0.01, min((q_bragg_max - q_bragg_min) * 0.12, 0.06))
    corr_step = max(0.01, min((q_corr_max - q_corr_min) * 0.12, 0.08))
    return [
        {
            "q_bragg_min": q_bragg_min + low_step,
            "q_corr_min": q_corr_min + corr_step,
        },
        {
            "q_bragg_max": q_bragg_max - low_step,
            "q_corr_max": q_corr_max - corr_step,
        },
    ]


def _saxs_idf_smoothing_candidates(
    self: Any,
    current_config: dict[str, Any],
) -> list[dict[str, Any]]:
    window = int(round(self._safe_float(current_config.get("savgol_window", 7)) or 7))
    peak_thresh = self._safe_float(current_config.get("idf_peak_rel_thresh", 0.05)) or 0.05
    valley_thresh = self._safe_float(current_config.get("idf_valley_rel_thresh", 0.05)) or 0.05
    return [
        {"savgol_window": window + 2},
        {
            "idf_peak_rel_thresh": peak_thresh * 1.2,
            "idf_valley_rel_thresh": valley_thresh * 1.2,
        },
    ]


def _normalize_candidate_value(
    self: Any,
    param_name: str,
    value: Any,
    param_map: dict[str, Any],
) -> Any:
    rule = param_map.get(param_name)
    if rule is None:
        return value
    constraint = rule.constraint
    if constraint is None:
        if rule.value_type is bool:
            return bool(value)
        if rule.value_type is int:
            return int(round(self._safe_float(value)))
        if rule.value_type is float:
            return round(float(self._safe_float(value)), 6)
        return value
    if all(isinstance(item, str) for item in constraint):
        text = str(value or "").strip()
        if text in constraint:
            return text
        return str(constraint[0])

    lower = float(constraint[0])
    upper = float(constraint[1])
    if rule.value_type is int:
        number = int(round(self._safe_float(value)))
        number = max(int(lower), min(int(upper), number))
        if param_name == "savgol_window":
            if number % 2 == 0:
                if number + 1 <= int(upper):
                    number += 1
                else:
                    number -= 1
            number = max(number, 3)
        if param_name == "savgol_order":
            number = max(number, 1)
        return number

    number = self._safe_float(value)
    number = max(lower, min(upper, number))
    return round(float(number), 6)


def _normalize_saxs_candidate_value(self: Any, param_name: str, value: Any) -> Any:
    return self._normalize_candidate_value(param_name, value, SAXS_PARAM_MAP)


def _candidate_values_equal(self: Any, left: Any, right: Any) -> bool:
    if isinstance(left, str) or isinstance(right, str):
        return str(left) == str(right)
    try:
        return math.isclose(float(left), float(right), rel_tol=1e-9, abs_tol=1e-9)
    except (TypeError, ValueError):
        return left == right
