from __future__ import annotations

import math
from typing import Any

from polynexus.config_bridge import DSC_PARAM_MAP, IR_PARAM_MAP, SAXS_PARAM_MAP, WAXS_PARAM_MAP
from polynexus.core.analysis_evidence import build_analysis_evidence
from polynexus.orchestrator_actions import (
    SAXS_LOW_Q_FIRST_ACTION_ORDER,
    SAXS_LOW_Q_PRIORITY_SYMPTOMS,
    SAXS_LOW_Q_SUPPORT_ACTION_ORDER,
)


def _build_agent_state(self: Any, engine: Any, round_num: int) -> dict[str, Any]:
    output = self._output_parameters(engine)
    config = self._config_snapshot(engine)
    residuals_pattern = self._residual_pattern(engine)
    analysis_evidence = self._analysis_evidence(output, residuals_pattern)
    ir_reference_bands = self._ir_reference_bands(engine)
    score_snapshot = self._score_snapshot(output, residuals_pattern, analysis_evidence)
    symptoms = self._analysis_symptoms(analysis_evidence)
    allowed_actions = self._allowed_actions(symptoms)
    allowed_changes = self._allowed_changes(allowed_actions)
    return {
        "case_id": f"live_{self.polymer_name}_{self.technique}",
        "technique": self.technique.upper(),
        "submodule": self._agent_state_submodule(),
        "data_file": self.data_file,
        "polymer_name": self.polymer_name,
        "round": round_num,
        "current_config": config,
        "params": output,
        "output_parameters": output,
        "r_squared": self._safe_float(output.get("r_squared", 0.0)),
        "residuals_pattern": residuals_pattern.get("summary", ""),
        "residual_pattern": residuals_pattern,
        "analysis_evidence": analysis_evidence,
        "ir_reference_bands": ir_reference_bands,
        "symptoms": symptoms,
        "symptom_names": self._symptom_names(symptoms),
        "symptom_summary": self._symptom_summary(symptoms),
        "allowed_actions": allowed_actions,
        "allowed_changes": allowed_changes,
        "polymer_knowledge": self._to_plain_value(self.polymer_knowledge),
        "workspace_context": (
            self._to_plain_value(self.workspace_context) if self.workspace_context else {}
        ),
        "history": [record for record in self.history if record.round_num > 0],
        "previous_score": self._best_eval_score if math.isfinite(self._best_eval_score) else None,
        "objective_score": score_snapshot["objective_score"],
        "tunable_params": self._tunable_params(config, allowed_actions=allowed_actions),
    }


def _clean_advice(self: Any, advice: dict[str, Any] | None) -> dict[str, Any] | None:
    if advice is None:
        return None
    return {key: value for key, value in advice.items() if not str(key).startswith("_")}


def _analysis_evidence(
    self: Any,
    output: dict[str, Any],
    residuals_pattern: dict[str, Any],
) -> dict[str, Any]:
    validation_context: dict[str, Any] = {}
    if self._engine is not None:
        validation_context["config_snapshot"] = self._config_to_dict(
            self._engine_config(self._engine)
        )
        validation_context["submodule_id"] = self._submodule_id()
        if self.technique == "ir":
            validation_context["ir_reference_bands"] = self._ir_reference_bands(self._engine)
    if self.technique == "saxs":
        validation_context["cross_validation"] = self._saxs_cross_validation(output)
    elif self.technique == "dsc":
        validation_context["cross_validation"] = self._dsc_cross_validation(output)
    return build_analysis_evidence(
        self.technique,
        output_parameters=output,
        residual_pattern=residuals_pattern,
        validation_context=validation_context,
    ).to_dict()


def _attach_analysis_evidence(
    self: Any,
    engine: Any,
    analysis_evidence: dict[str, Any],
) -> None:
    if engine is None:
        return
    result = getattr(engine, "result", None)
    if result is None:
        return
    setter = getattr(result, "set_analysis_evidence", None)
    if callable(setter):
        setter(analysis_evidence)
        return
    try:
        result.analysis_evidence = dict(analysis_evidence)
    except Exception:
        pass


def _analysis_symptoms(self: Any, analysis_evidence: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(analysis_evidence, dict):
        return []
    symptoms = analysis_evidence.get("symptoms", [])
    if not isinstance(symptoms, list):
        return []
    out: list[dict[str, Any]] = []
    for symptom in symptoms:
        if not isinstance(symptom, dict):
            continue
        name = str(symptom.get("name", "") or "").strip()
        if not name:
            continue
        out.append(self._to_plain_value(symptom))
    return out


def _symptom_names(self: Any, symptoms: list[dict[str, Any]] | None) -> list[str]:
    names: list[str] = []
    for symptom in symptoms or []:
        if not isinstance(symptom, dict):
            continue
        name = str(symptom.get("name", "") or "").strip()
        if name and name not in names:
            names.append(name)
    return names


def _symptom_summary(self: Any, symptoms: list[dict[str, Any]] | None) -> str:
    parts: list[str] = []
    for symptom in symptoms or []:
        if not isinstance(symptom, dict):
            continue
        name = str(symptom.get("name", "") or "").strip()
        summary = str(symptom.get("summary", "") or "").strip()
        if not name:
            continue
        if summary:
            parts.append(f"{name}: {summary}")
        else:
            parts.append(name)
    return " | ".join(parts[:3])


def _advice_target_symptom(
    self: Any,
    advice: dict[str, Any] | None,
    analysis_evidence: dict[str, Any],
) -> str:
    if isinstance(advice, dict):
        target = str(advice.get("target_symptom", "") or "").strip()
        if target:
            return target
    names = self._symptom_names(self._analysis_symptoms(analysis_evidence))
    return names[0] if names else ""


def _advice_rollback_detail(
    self: Any,
    advice: dict[str, Any] | None,
) -> str:
    if not isinstance(advice, dict):
        return ""
    detail = str(advice.get("rollback_detail", "") or "").strip()
    if detail:
        return detail
    reason = str(advice.get("rollback_reason", "") or "").strip()
    decision = (
        advice.get("decision_metrics", {})
        if isinstance(advice.get("decision_metrics"), dict)
        else {}
    )
    candidate = decision.get("candidate", {}) if isinstance(decision.get("candidate"), dict) else {}
    previous = decision.get("previous", {}) if isinstance(decision.get("previous"), dict) else {}
    target = str(advice.get("target_symptom", "") or "").strip()

    if not reason:
        return ""
    if reason.startswith("new_hard_fail_introduced:"):
        hard_names = reason.split(":", 1)[1]
        return f"New hard-fail evidence appeared: {hard_names}."
    if reason == "no_meaningful_gain":
        return f"Target symptom {target or 'current symptom'} did not improve enough to keep the change."
    if reason == "fit_score_dropped":
        return "The fit score regressed after the trial change."
    if reason == "quality_score_dropped":
        return "The quality score dropped after the trial change."
    if reason == "validation_risk_increased":
        return "Validation risk increased after the trial change."
    if reason == "residual_risk_increased":
        return "Residual structure became less trustworthy after the trial change."
    if reason == "fit_improved_but_phys_worse":
        return "The fit looked better, but the physical evidence became weaker."
    if reason == "condition_continuity_worsened":
        return "The recovered series axis became less continuous after the trial change."
    if reason == "structure_jump_too_large":
        return "Cross-method structure agreement drifted too far after the trial change."
    if reason == "symptom_unresolved":
        return "The targeted SAXS symptom stayed unresolved, so the result still needs manual review."
    if reason == "stability_score_dropped":
        return "Overall SAXS stability dropped after the trial change."
    if reason == "low_q_contamination_unresolved":
        return "Low-q contamination is still the dominant problem, so this round should keep repairing the low-q evidence chain first."
    if reason == "fallback_still_dominant":
        return "Fallback-derived thickness values are still dominating the batch summary, so the system will not keep this result before the low-q evidence stabilizes."
    if reason == "raw_calibrated_conflict_worsened":
        return "The calibrated batch summary moved further away from the raw frame structure evidence after the trial change."
    if reason == "thickness_chain_still_unreliable":
        return "Thickness-chain evidence is still not trustworthy enough to keep this trial result."
    if reason == "peak_family_became_less_stable":
        return "The WAXS peak family became less stable after the trial change."
    if reason == "background_partition_worsened":
        return "The WAXS background and amorphous partition became less trustworthy after the trial change."
    if reason == "crystallinity_support_collapsed":
        return "Crystallinity or size support weakened too much after the trial change."
    if reason == "physical_support_weakened":
        return "The overall WAXS physical support weakened too much after the trial change."
    if reason.startswith("quality_score below"):
        return reason
    if candidate or previous:
        candidate_score = self._safe_float(candidate.get("objective_score", 0.0))
        previous_score = self._safe_float(previous.get("objective_score", 0.0))
        return (
            f"Objective score did not justify keeping the change "
            f"({previous_score:.3f} -> {candidate_score:.3f})."
        )
    return reason


def _expand_technique_candidates(
    self: Any,
    advice: dict[str, Any] | None,
    state: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if self.technique not in {"dsc", "ir", "saxs", "waxs"}:
        return []

    advice_dict = advice if isinstance(advice, dict) else {}
    state_dict = state if isinstance(state, dict) else {}
    current_config = (
        state_dict.get("current_config", {})
        if isinstance(state_dict.get("current_config"), dict)
        else {}
    )
    allowed_actions = (
        state_dict.get("allowed_actions", [])
        if isinstance(state_dict.get("allowed_actions"), list)
        else []
    )
    allowed_changes = (
        state_dict.get("allowed_changes", {})
        if isinstance(state_dict.get("allowed_changes"), dict)
        else {}
    )
    symptom_names = state_dict.get("symptom_names", [])
    symptom_names = symptom_names if isinstance(symptom_names, list) else []
    target_symptom = str(advice_dict.get("target_symptom", "") or "").strip()
    if not target_symptom and symptom_names:
        target_symptom = str(symptom_names[0] or "").strip()

    action_specs: dict[str, dict[str, Any]] = {}
    for action in allowed_actions:
        if not isinstance(action, dict):
            continue
        name = str(action.get("name", "") or "").strip()
        if name:
            action_specs[name] = action

    plans: list[dict[str, Any]] = []
    direct_changes = advice_dict.get("changes", {})
    if self.technique == "dsc":
        param_map = DSC_PARAM_MAP
    if self.technique == "ir":
        param_map = IR_PARAM_MAP
    elif self.technique == "saxs":
        param_map = SAXS_PARAM_MAP
    elif self.technique == "waxs":
        param_map = WAXS_PARAM_MAP
    technique_label = self.technique.upper()

    if isinstance(direct_changes, dict) and direct_changes:
        guarded_changes, guard_error = self._guard_technique_direct_changes(
            direct_changes,
            allowed_changes,
            current_config,
            param_map,
            technique_label,
        )
        if guarded_changes:
            plans.append(
                {
                    "action_name": "advisor_changes",
                    "label": "Advisor changes",
                    "reason": str(advice_dict.get("reasoning", "") or "").strip(),
                    "target_symptom": target_symptom,
                    "expected_evidence_change": "",
                    "changes": guarded_changes,
                    "executable": True,
                }
            )
        elif guard_error:
            plans.append(
                {
                    "action_name": "advisor_changes",
                    "label": "Advisor changes",
                    "reason": str(advice_dict.get("reasoning", "") or "").strip(),
                    "target_symptom": target_symptom,
                    "expected_evidence_change": "",
                    "changes": {},
                    "executable": False,
                    "skip_reason": guard_error,
                }
            )

    recommended_actions = advice_dict.get("recommended_actions", [])
    if not isinstance(recommended_actions, list):
        recommended_actions = [recommended_actions] if recommended_actions else []

    low_q_first = self.technique == "saxs" and bool(
        set(str(item or "").strip() for item in symptom_names) & SAXS_LOW_Q_PRIORITY_SYMPTOMS
    )
    requested_action_names = {
        (
            str(item.get("name", "") or "").strip()
            if isinstance(item, dict)
            else str(item or "").strip()
        )
        for item in recommended_actions
    }
    requested_action_names = {name for name in requested_action_names if name}

    if low_q_first:
        prioritized_actions: list[dict[str, Any]] = []
        for action_name in SAXS_LOW_Q_FIRST_ACTION_ORDER:
            spec = action_specs.get(action_name)
            if not isinstance(spec, dict):
                continue
            prioritized_actions.append(
                {
                    "name": action_name,
                    "reason": "Low-q evidence is still unstable, so this round must repair the low-q / correlation chain first.",
                    "expected_evidence_change": "",
                }
            )
        for action_name in SAXS_LOW_Q_SUPPORT_ACTION_ORDER:
            if action_name in requested_action_names:
                continue
            spec = action_specs.get(action_name)
            if not isinstance(spec, dict):
                continue
            prioritized_actions.append(
                {
                    "name": action_name,
                    "reason": "Support the low-q recovery path before trusting the thickness chain.",
                    "expected_evidence_change": "",
                }
            )
        existing = list(recommended_actions)
        recommended_actions = prioritized_actions + existing

    for item in recommended_actions:
        if isinstance(item, dict):
            action_name = str(item.get("name", "") or "").strip()
            reason = str(item.get("reason", "") or "").strip()
            expected = str(item.get("expected_evidence_change", "") or "").strip()
        else:
            action_name = str(item or "").strip()
            reason = ""
            expected = ""
        if not action_name:
            continue
        spec = action_specs.get(action_name, {"name": action_name, "allowed_params": []})
        plans.extend(
            self._candidate_plans_for_action(
                action_name=action_name,
                current_config=current_config,
                allowed_changes=allowed_changes,
                action_spec=spec,
                target_symptom=target_symptom,
                reason=reason,
                expected_evidence_change=expected,
            )
        )

    unique: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    executable_count = 0
    for plan in plans:
        if not isinstance(plan, dict):
            continue
        changes = plan.get("changes", {})
        executable = bool(plan.get("executable", False))
        if executable and isinstance(changes, dict):
            key = (
                "plan",
                str(plan.get("action_name", "") or "").strip(),
                tuple(
                    sorted(
                        (str(name), self._stable_signature(value))
                        for name, value in changes.items()
                    )
                ),
                self._stable_signature(plan.get("recovery_context", {})),
            )
        else:
            key = (
                "skip",
                str(plan.get("action_name", "") or "").strip(),
                str(plan.get("skip_reason", "") or "").strip(),
            )
        if key in seen:
            continue
        seen.add(key)
        if executable:
            if executable_count >= 5:
                continue
            executable_count += 1
        unique.append(self._to_plain_value(plan))
    return unique


def _expand_saxs_candidates(
    self: Any,
    advice: dict[str, Any] | None,
    state: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    return self._expand_technique_candidates(advice, state)
