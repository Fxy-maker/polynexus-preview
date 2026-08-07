from __future__ import annotations

import logging
import math
from copy import deepcopy
from dataclasses import asdict
from typing import Any

from polynexus.config_bridge import apply_changes

logger = logging.getLogger(__name__)


def _restore_best(self: Any, engine: Any) -> None:
    if self._best_config is not None:
        if self.technique == "dsc":
            engine._dsc_config = deepcopy(self._best_config)
        elif self.technique == "saxs":
            engine.cfg = deepcopy(self._best_config)
        elif self.technique == "ir":
            engine._ir_config = deepcopy(self._best_config)
        elif self.technique == "nmr":
            engine._cfg = deepcopy(self._best_config)
        else:
            engine._waxs_config = deepcopy(self._best_config)


def _record_round(
    self: Any,
    engine: Any,
    round_num: int,
    advice: dict[str, Any] | None,
    before_r_squared: float | None = None,
    changes: dict[str, Any] | None = None,
    accepted: bool = True,
    prompt: str = "",
) -> Any:
    from polynexus.orchestrator import RoundRecord

    output = self._output_parameters(engine)
    residuals_pattern = self._residual_pattern(engine)
    analysis_evidence = self._analysis_evidence(output, residuals_pattern)
    score_snapshot = self._score_snapshot(output, residuals_pattern, analysis_evidence)
    self._attach_analysis_evidence(engine, analysis_evidence)
    r_squared = self._safe_float(output.get("r_squared", 0.0))
    config_snapshot = self._config_snapshot(engine)
    clean_advice = self._clean_advice(advice)
    round_changes = changes
    if round_changes is None and isinstance(clean_advice, dict):
        maybe_changes = clean_advice.get("changes", {})
        round_changes = maybe_changes if isinstance(maybe_changes, dict) else {}
    round_changes = round_changes or {}
    before = r_squared if before_r_squared is None else self._safe_float(before_r_squared)
    symptoms = self._analysis_symptoms(analysis_evidence)
    clean_advice_dict = self._to_plain_value(clean_advice) if clean_advice is not None else None
    target_symptom = self._advice_target_symptom(clean_advice_dict, analysis_evidence)
    rollback_detail = self._advice_rollback_detail(clean_advice_dict)
    decision_summary = self._decision_summary(
        accepted,
        target_symptom,
        rollback_detail,
        score_snapshot,
    )
    return RoundRecord(
        round_num=round_num,
        config_snapshot=config_snapshot,
        output_parameters=output,
        residuals_pattern=residuals_pattern,
        analysis_evidence=analysis_evidence,
        polymer_knowledge=self._to_plain_value(self.polymer_knowledge),
        r_squared=r_squared,
        eval_score=score_snapshot["objective_score"],
        llm_advice=clean_advice_dict,
        round_idx=round_num,
        r_squared_before=before,
        r_squared_after=r_squared,
        changes=self._to_plain_value(round_changes),
        accepted=accepted,
        prompt=prompt,
        symptoms=symptoms,
        symptom_names=self._symptom_names(symptoms),
        symptom_summary=self._symptom_summary(symptoms),
        target_symptom=target_symptom,
        rollback_detail=rollback_detail,
        decision_summary=decision_summary,
    )


def _execute_candidate_trial(
    self: Any,
    engine: Any,
    round_num: int,
    previous_record: Any,
    advice: dict[str, Any],
    changes: dict[str, Any],
    prompt: str,
) -> dict[str, Any]:
    candidate_plan = (
        advice.get("candidate_plan", {})
        if isinstance(advice.get("candidate_plan"), dict)
        else {}
    )
    action_name = str(candidate_plan.get("action_name", "") or "").strip()
    if self.technique == "saxs" and action_name == "rerun_condition_recovery":
        recovery_context = candidate_plan.get("recovery_context", {})
        if not isinstance(recovery_context, dict) or not recovery_context:
            rejected = dict(advice)
            rejected["rejected"] = True
            rejected["rollback_reason"] = "No recoverable SAXS condition_context was available."
            rejected["rollback_detail"] = (
                "Condition recovery needs a real context payload before the SAXS directory can be rescanned."
            )
            return {
                "status": "rejected",
                "reason": rejected["rollback_reason"],
                "record": None,
                "advice": rejected,
            }

        config = self._engine_config(engine)
        if config is None or not hasattr(config, "condition_context"):
            rejected = dict(advice)
            rejected["rejected"] = True
            rejected["rollback_reason"] = "SAXS config does not expose condition_context."
            rejected["rollback_detail"] = (
                "The current SAXS engine config cannot accept recovered condition context."
            )
            return {
                "status": "rejected",
                "reason": rejected["rollback_reason"],
                "record": None,
                "advice": rejected,
            }

        merged_context = deepcopy(getattr(config, "condition_context", {}))
        if not isinstance(merged_context, dict):
            merged_context = {}
        for key, value in recovery_context.items():
            if key not in merged_context or merged_context[key] in (None, "", {}, []):
                merged_context[key] = deepcopy(value)
        config.condition_context = merged_context

        data_path = str(self._resolve_data_file(self.data_file))
        try:
            run_result = engine.run_pipeline(data_path, output_dir="")
        except Exception as exc:
            rejected = dict(advice)
            rejected["rejected"] = True
            rejected["rollback_reason"] = f"engine.run_pipeline() failed: {exc}"
            rejected["rollback_detail"] = (
                "Condition recovery could not rebuild the SAXS batch, so the trial was rolled back."
            )
            return {
                "status": "rejected",
                "reason": rejected["rollback_reason"],
                "record": None,
                "advice": rejected,
            }

        if run_result is None:
            rejected = dict(advice)
            rejected["rejected"] = True
            rejected["rollback_reason"] = "engine.run_pipeline() returned no result"
            rejected["rollback_detail"] = "Condition recovery did not produce a usable SAXS rerun."
            return {
                "status": "rejected",
                "reason": rejected["rollback_reason"],
                "record": None,
                "advice": rejected,
            }

        engine.result.parameters = engine.get_parameters()
        candidate = self._record_round(
            engine,
            round_num,
            advice,
            before_r_squared=previous_record.r_squared,
            changes={},
            accepted=True,
            prompt=prompt,
        )
        if isinstance(candidate.llm_advice, dict):
            candidate.llm_advice["recovery_context"] = self._to_plain_value(recovery_context)

        quality_ok, quality_error = self._quality_guard(candidate)
        if not quality_ok:
            rejected = dict(candidate.llm_advice or advice)
            rejected["rejected"] = True
            rejected["rollback_reason"] = quality_error
            rejected["decision_metrics"] = self._decision_metrics(candidate, previous_record)
            rejected["rollback_detail"] = self._advice_rollback_detail(rejected)
            candidate.llm_advice = rejected
            candidate.accepted = False
            candidate.target_symptom = self._advice_target_symptom(
                rejected,
                candidate.analysis_evidence,
            )
            candidate.rollback_detail = rejected["rollback_detail"]
            candidate.decision_summary = self._decision_summary(
                False,
                candidate.target_symptom,
                candidate.rollback_detail,
                {"objective_score": candidate.eval_score},
            )
            return {
                "status": "rolled_back",
                "reason": quality_error,
                "record": candidate,
                "advice": rejected,
            }

        accepted, rollback_reason, decision_metrics = self._evaluate_candidate(
            candidate,
            previous_record,
        )
        if accepted:
            return {
                "status": "accepted",
                "reason": "",
                "record": candidate,
                "advice": (
                    candidate.llm_advice
                    if isinstance(candidate.llm_advice, dict)
                    else dict(advice)
                ),
            }

        rejected = dict(candidate.llm_advice or advice)
        rejected["rejected"] = True
        rejected["rollback_reason"] = rollback_reason
        rejected["decision_metrics"] = decision_metrics
        rejected["rollback_detail"] = self._advice_rollback_detail(rejected)
        candidate.llm_advice = rejected
        candidate.accepted = False
        candidate.target_symptom = self._advice_target_symptom(
            rejected,
            candidate.analysis_evidence,
        )
        candidate.rollback_detail = rejected["rollback_detail"]
        candidate.decision_summary = self._decision_summary(
            False,
            candidate.target_symptom,
            candidate.rollback_detail,
            {"objective_score": candidate.eval_score},
        )
        return {
            "status": "rolled_back",
            "reason": rollback_reason,
            "record": candidate,
            "advice": rejected,
        }

    ok, error = apply_changes(self._engine_config(engine), changes, technique=self.technique)
    if not ok:
        rejected = dict(advice)
        rejected["rejected"] = True
        rejected["rollback_reason"] = error
        rejected["rollback_detail"] = (
            "The proposed parameter change violates the local config constraints, so the candidate was skipped."
        )
        return {
            "status": "rejected",
            "reason": error,
            "record": None,
            "advice": rejected,
        }

    if not engine.analyze():
        rejected = dict(advice)
        rejected["rejected"] = True
        rejected["rollback_reason"] = "engine.analyze() failed"
        rejected["rollback_detail"] = (
            "The core analysis failed to finish, so the candidate was rolled back immediately."
        )
        return {
            "status": "rejected",
            "reason": "engine.analyze() failed",
            "record": None,
            "advice": rejected,
        }

    engine.result.parameters = engine.get_parameters()
    candidate = self._record_round(
        engine,
        round_num,
        advice,
        before_r_squared=previous_record.r_squared,
        changes=changes,
        accepted=True,
        prompt=prompt,
    )

    quality_ok, quality_error = self._quality_guard(candidate)
    if not quality_ok:
        rejected = dict(advice)
        rejected["rejected"] = True
        rejected["rollback_reason"] = quality_error
        rejected["decision_metrics"] = self._decision_metrics(candidate, previous_record)
        rejected["rollback_detail"] = self._advice_rollback_detail(rejected)
        candidate.llm_advice = rejected
        candidate.accepted = False
        candidate.target_symptom = self._advice_target_symptom(
            rejected,
            candidate.analysis_evidence,
        )
        candidate.rollback_detail = rejected["rollback_detail"]
        candidate.decision_summary = self._decision_summary(
            False,
            candidate.target_symptom,
            candidate.rollback_detail,
            {"objective_score": candidate.eval_score},
        )
        return {
            "status": "rolled_back",
            "reason": quality_error,
            "record": candidate,
            "advice": rejected,
        }

    accepted, rollback_reason, decision_metrics = self._evaluate_candidate(
        candidate,
        previous_record,
    )
    if accepted:
        return {
            "status": "accepted",
            "reason": "",
            "record": candidate,
            "advice": (
                candidate.llm_advice if isinstance(candidate.llm_advice, dict) else dict(advice)
            ),
        }

    rejected = dict(advice)
    rejected["rejected"] = True
    rejected["rollback_reason"] = rollback_reason
    rejected["decision_metrics"] = decision_metrics
    rejected["rollback_detail"] = self._advice_rollback_detail(rejected)
    candidate.llm_advice = rejected
    candidate.accepted = False
    candidate.target_symptom = self._advice_target_symptom(
        rejected,
        candidate.analysis_evidence,
    )
    candidate.rollback_detail = rejected["rollback_detail"]
    candidate.decision_summary = self._decision_summary(
        False,
        candidate.target_symptom,
        candidate.rollback_detail,
        {"objective_score": candidate.eval_score},
    )
    return {
        "status": "rolled_back",
        "reason": rollback_reason,
        "record": candidate,
        "advice": rejected,
    }


def _candidate_trial_summary(
    self: Any,
    plan: dict[str, Any],
    status: str,
    previous_record: Any,
    record: Any | None = None,
    reason: str = "",
) -> dict[str, Any]:
    summary = {
        "action_name": str(plan.get("action_name", "") or "").strip(),
        "label": str(plan.get("label", "") or "").strip(),
        "target_symptom": str(plan.get("target_symptom", "") or "").strip(),
        "changes": self._to_plain_value(plan.get("changes", {})),
        "status": status,
        "reason": reason,
        "expected_evidence_change": str(plan.get("expected_evidence_change", "") or "").strip(),
    }
    if record is None:
        return summary

    rollback_reason = ""
    if isinstance(record.llm_advice, dict):
        rollback_reason = str(record.llm_advice.get("rollback_reason", "") or "").strip()
    summary.update(
        {
            "accepted": bool(record.accepted),
            "r_squared": record.r_squared,
            "objective_score": record.eval_score,
            "r_squared_delta": record.r_squared - previous_record.r_squared,
            "objective_delta": record.eval_score - previous_record.eval_score,
            "rollback_reason": rollback_reason,
            "decision_summary": record.decision_summary,
        }
    )
    return self._to_plain_value(summary)


def _candidate_rank(self: Any, record: Any) -> tuple[float, float, float]:
    change_count = len(record.changes or {}) if isinstance(record.changes, dict) else 0
    return (record.eval_score, record.r_squared, -float(change_count))


def _restore_best_with_refresh(self: Any, engine: Any) -> None:
    self._restore_best(engine)
    if engine is None or self._best_record is None:
        return
    try:
        if engine.analyze():
            engine.result.parameters = engine.get_parameters()
    except Exception:
        logger.warning(
            "Failed to refresh the best engine state after rollback.",
            exc_info=True,
        )


def _run_saxs_candidate_round(
    self: Any,
    engine: Any,
    round_num: int,
    advice: dict[str, Any],
    previous_record: Any,
    candidate_plans: list[dict[str, Any]],
    prompt: str,
) -> dict[str, Any]:
    from polynexus.orchestrator import RoundRecord

    trial_summaries: list[dict[str, Any]] = []
    accepted_trials: list[dict[str, Any]] = []
    failed_trials: list[dict[str, Any]] = []
    attempted_execution = False

    for index, plan in enumerate(candidate_plans, start=1):
        plan_dict = dict(plan or {})
        plan_dict["candidate_index"] = index
        plan_dict["candidate_total"] = len(candidate_plans)
        executable = bool(plan_dict.get("executable", False))
        if not executable:
            trial_summaries.append(
                self._candidate_trial_summary(
                    plan_dict,
                    "skipped",
                    previous_record,
                    reason=str(plan_dict.get("skip_reason", "") or "").strip(),
                )
            )
            continue

        attempted_execution = True
        self._restore_best(engine)
        trial_advice = dict(advice)
        trial_advice["changes"] = dict(plan_dict.get("changes", {}))
        action_name = str(plan_dict.get("action_name", "") or "").strip()
        action_target = str(plan_dict.get("target_symptom", "") or "").strip()
        if action_name == "advisor_changes":
            action_target = action_target or str(
                advice.get("target_symptom", "") or ""
            ).strip()
        trial_advice["target_symptom"] = action_target
        trial_advice["candidate_plan"] = {
            "action_name": action_name,
            "label": str(plan_dict.get("label", "") or "").strip(),
            "reason": str(plan_dict.get("reason", "") or "").strip(),
            "expected_evidence_change": str(
                plan_dict.get("expected_evidence_change", "") or ""
            ).strip(),
            "changes": self._to_plain_value(plan_dict.get("changes", {})),
            "recovery_context": self._to_plain_value(plan_dict.get("recovery_context", {})),
        }
        if trial_advice["candidate_plan"]["action_name"] != "advisor_changes":
            trial_advice["recommended_actions"] = [
                {
                    "name": trial_advice["candidate_plan"]["action_name"],
                    "reason": trial_advice["candidate_plan"]["reason"],
                    "expected_evidence_change": trial_advice["candidate_plan"][
                        "expected_evidence_change"
                    ],
                }
            ]

        outcome = self._execute_candidate_trial(
            engine,
            round_num,
            previous_record,
            trial_advice,
            dict(plan_dict.get("changes", {})),
            prompt,
        )
        trial_record = outcome.get("record")
        reason = str(outcome.get("reason", "") or "").strip()
        trial_summaries.append(
            self._candidate_trial_summary(
                plan_dict,
                str(outcome.get("status", "rejected") or "rejected"),
                previous_record,
                record=trial_record if isinstance(trial_record, RoundRecord) else None,
                reason=reason,
            )
        )
        if isinstance(trial_record, RoundRecord) and str(outcome.get("status")) == "accepted":
            accepted_trials.append({"plan": plan_dict, "record": trial_record})
        elif isinstance(trial_record, RoundRecord):
            failed_trials.append({"plan": plan_dict, "record": trial_record})
        else:
            failed_trials.append(
                {
                    "plan": plan_dict,
                    "advice": outcome.get("advice", {}),
                    "reason": reason,
                }
            )

    if accepted_trials:
        best_trial = max(accepted_trials, key=lambda item: self._candidate_rank(item["record"]))
        best_plan = best_trial["plan"]
        best_record = best_trial["record"]
        selected_advice = dict(best_record.llm_advice or advice)
        selected_advice["candidate_trials"] = self._to_plain_value(trial_summaries)
        selected_advice["selected_candidate"] = self._to_plain_value(
            {
                "action_name": str(best_plan.get("action_name", "") or "").strip(),
                "label": str(best_plan.get("label", "") or "").strip(),
                "changes": best_plan.get("changes", {}),
                "target_symptom": str(best_plan.get("target_symptom", "") or "").strip(),
                "objective_score": best_record.eval_score,
                "r_squared": best_record.r_squared,
            }
        )
        best_record.llm_advice = selected_advice
        best_record.target_symptom = self._advice_target_symptom(
            selected_advice,
            best_record.analysis_evidence,
        )
        best_record.rollback_detail = self._advice_rollback_detail(selected_advice)
        best_record.decision_summary = self._decision_summary(
            True,
            best_record.target_symptom,
            best_record.rollback_detail,
            {"objective_score": best_record.eval_score},
        )

        self._restore_best(engine)
        ok, error = apply_changes(
            self._engine_config(engine),
            dict(best_plan.get("changes", {})),
            technique=self.technique,
        )
        if ok and engine.analyze():
            engine.result.parameters = engine.get_parameters()
        else:
            logger.warning(
                "Failed to replay the accepted %s candidate; restoring the previous best state. error=%s",
                self.technique.upper(),
                error or "engine.analyze() failed",
            )
            self._restore_best_with_refresh(engine)

        self._best_r_squared = best_record.r_squared
        self._best_eval_score = best_record.eval_score
        self._best_record = best_record
        self._best_config = deepcopy(self._engine_config(engine))
        self._best_output = dict(best_record.output_parameters)
        return {
            "record": best_record,
            "status": "improved",
            "changes": dict(best_plan.get("changes", {})),
        }

    rejected_reason = ""
    rejected_detail = ""
    rejected_changes: dict[str, Any] = {}
    rejected_trial_advice: dict[str, Any] | None = None
    if failed_trials:
        best_failed = max(
            failed_trials,
            key=lambda item: (
                self._candidate_rank(item["record"])
                if isinstance(item.get("record"), RoundRecord)
                else (-math.inf, -math.inf, 0.0)
            ),
        )
        failed_record = best_failed.get("record")
        if isinstance(failed_record, RoundRecord):
            final_advice = dict(failed_record.llm_advice or advice)
            final_advice["candidate_trials"] = self._to_plain_value(trial_summaries)
            failed_record.llm_advice = final_advice
            failed_record.accepted = False
            failed_record.target_symptom = self._advice_target_symptom(
                final_advice,
                failed_record.analysis_evidence,
            )
            failed_record.rollback_detail = self._advice_rollback_detail(final_advice)
            failed_record.decision_summary = self._decision_summary(
                False,
                failed_record.target_symptom,
                failed_record.rollback_detail,
                {"objective_score": failed_record.eval_score},
            )
            if attempted_execution:
                self._restore_best_with_refresh(engine)
            return {
                "record": failed_record,
                "status": "rolled_back",
                "changes": dict(failed_record.changes or {}),
            }
        rejected_reason = str(best_failed.get("reason", "") or "").strip()
        rejected_changes = dict(best_failed.get("plan", {}).get("changes", {}) or {})
        if isinstance(best_failed.get("advice"), dict):
            rejected_trial_advice = best_failed["advice"]

    if not rejected_reason:
        for item in trial_summaries:
            if not isinstance(item, dict):
                continue
            rejected_reason = str(
                item.get("reason", "") or item.get("rollback_reason", "") or ""
            ).strip()
            if rejected_reason:
                break
    if not rejected_reason:
        rejected_reason = (
            f"No executable {self.technique.upper()} candidate could be produced from the advisor action list."
        )
    rejected_detail = (
        f"The current action list did not yield a guarded {self.technique.upper()} re-run candidate that improved the objective score."
    )

    rejected_advice = dict(rejected_trial_advice or advice)
    rejected_advice["rejected"] = True
    rejected_advice["rollback_reason"] = rejected_reason
    rejected_advice["rollback_detail"] = rejected_detail
    rejected_advice["candidate_trials"] = self._to_plain_value(trial_summaries)
    record = self._record_round(
        engine,
        round_num,
        rejected_advice,
        before_r_squared=previous_record.r_squared,
        changes=rejected_changes,
        accepted=False,
        prompt=prompt,
    )
    if attempted_execution:
        self._restore_best_with_refresh(engine)
    return {
        "record": record,
        "status": "rejected",
        "changes": rejected_changes,
    }


def _final_report(
    self: Any,
    data_path: Any,
    converged: bool,
    convergence_reason: str,
) -> dict[str, Any]:
    best_config = self._config_to_dict(self._best_config)
    report = {
        "technique": self.technique,
        "submodule": self._public_submodule(),
        "polymer_name": self.polymer_name,
        "data_file": str(data_path),
        "rounds": len(self.history) - 1,
        "converged": converged,
        "convergence_reason": convergence_reason,
        "baseline_r_squared": self._baseline_r_squared,
        "best_r_squared": self._best_r_squared,
        "baseline_eval_score": self._baseline_eval_score,
        "best_eval_score": self._best_eval_score,
        "improvement": {
            "r_squared_abs": self._best_r_squared - self._baseline_r_squared,
            "eval_score_abs": self._best_eval_score - self._baseline_eval_score,
        },
        "benchmark_summary": self._benchmark_summary(),
        "best_config": best_config,
        "best_output_parameters": self._to_plain_value(self._best_output),
        "history": [self._to_plain_value(asdict(record)) for record in self.history],
    }
    preprocess_report = getattr(self, "_last_preprocess_report", {})
    if isinstance(preprocess_report, dict) and preprocess_report:
        report.update(self._to_plain_value(preprocess_report))
    stability_report = getattr(self, "_last_stability_report", {})
    if isinstance(stability_report, dict) and stability_report:
        report["stability_report"] = self._to_plain_value(stability_report)
        _attach_stability_confirmation_contract(report, stability_report)
    return self._to_plain_value(report)


def _attach_stability_confirmation_contract(
    report: dict[str, Any],
    stability: dict[str, Any],
    mode: str | None = None,
) -> None:
    """Expose stability evidence through the existing confirmation boundary."""
    from polynexus.core.preprocess_optimization import stable_config_hash
    from polynexus.core.saxs_mode import canonical_saxs_mode

    if "mode" in stability:
        raw_mode = stability.get("mode")
    elif mode is not None:
        raw_mode = mode
    elif "mode" in report:
        raw_mode = report.get("mode")
    else:
        raw_mode = report.get("submodule") or "static"
    projected_mode = canonical_saxs_mode(raw_mode)

    baseline = stability.get("baseline_config", {})
    selected = stability.get("selected_config", {})
    if not isinstance(baseline, dict) or not isinstance(selected, dict):
        return
    changed_keys = sorted(
        key for key in selected
        if key in baseline and selected.get(key) != baseline.get(key)
    )
    original_subset = {key: deepcopy(baseline[key]) for key in changed_keys}
    selected_subset = {key: deepcopy(selected[key]) for key in changed_keys}
    candidate_id = stable_config_hash(
        {"base": stable_config_hash(original_subset), "selected": selected_subset}
    )[:24]
    decision = str(stability.get("decision", "keep_original") or "keep_original")
    guards = {
        "stability_plateau": bool(stability.get("plateau", {}).get("connected", False)),
        "physical_gate": bool(stability.get("physics_gate_passed", False)),
        "quality_gate": bool(stability.get("quality_gate_passed", False)),
        "cross_frame_continuity": bool(stability.get("continuity", {}).get("passed", False)),
    }
    applicable = bool(stability.get("complete", True)) and projected_mode in {
        "static",
        "temperature",
        "strain",
    }
    if applicable:
        projected_original = original_subset
        projected_selected = selected_subset
        candidates = [
            {
                "candidate_id": candidate_id,
                "base_config_hash": stable_config_hash(original_subset),
                "config_delta": deepcopy(selected_subset),
                "generation_reason": "saxs_stability_map",
            }
        ]
    else:
        decision = "keep_original"
        projected_original = {}
        projected_selected = {}
        candidates = []
    report.update(
        {
            "mode": projected_mode,
            "selected_candidate_id": candidate_id if applicable else "",
            "original_preprocess_config": projected_original,
            "selected_preprocess_config": projected_selected,
            "preprocess_candidates": candidates,
            "preprocess_decision": {
                "decision": decision if changed_keys else "keep_original",
                "simulated_decision": decision if changed_keys else "keep_original",
                "confidence_band": "high" if decision == "auto_accept" else "medium" if decision == "request_confirmation" else "low",
                "hard_guard_results": guards,
                "reason_codes": list(stability.get("reason_codes", [])),
            },
        }
    )


def _can_converge_on_small_delta(self: Any, record: Any, round_num: int) -> bool:
    if round_num >= 3:
        return True
    if self.technique not in {"waxs", "dsc"}:
        return True
    section = "dsc" if self.technique == "dsc" else "waxs"
    knowledge = (
        self.polymer_knowledge.get(section, {})
        if isinstance(self.polymer_knowledge, dict)
        else {}
    )
    xc_range = knowledge.get("xc_range")
    if not (isinstance(xc_range, list) and len(xc_range) == 2):
        return True
    current_xc = record.output_parameters.get("Xc_pct")
    try:
        value = float(current_xc)
        low, high = float(xc_range[0]), float(xc_range[1])
    except (TypeError, ValueError):
        return True
    return low <= value <= high


def _can_converge_after_rollback(self: Any, round_num: int) -> bool:
    if round_num < 3:
        return False
    return (self._best_r_squared - self._baseline_r_squared) >= 0.001
