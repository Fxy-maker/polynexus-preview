from __future__ import annotations

import re
from typing import Any


def _benchmark_summary(self: Any) -> dict[str, Any]:
    candidate_history = [record for record in self.history if record.round_num > 0]
    if not candidate_history:
        return {
            "rounds": 0,
            "accepted_rounds": 0,
            "rejected_rounds": 0,
            "acceptance_rate": 0.0,
            "rollback_rate": 0.0,
            "objective_gain_rounds": 0,
            "objective_loss_rounds": 0,
            "objective_gain_rate": 0.0,
            "objective_delta_average": 0.0,
            "rollback_reasons": {},
            "constraint_hits": {
                "rounds": 0,
                "hard_fail_rounds": 0,
                "soft_warn_rounds": 0,
                "evidence_only_rounds": 0,
                "hit_rate": 0.0,
            },
            "symptom_hits": {
                "rounds": 0,
                "hit_rounds": 0,
                "hit_rate": 0.0,
            },
            "joint_context": {
                "rounds": 0,
                "penalty_total": 0.0,
            },
        }

    accepted_rounds = 0
    rejected_rounds = 0
    objective_gains = 0
    objective_losses = 0
    objective_deltas: list[float] = []
    rollback_reasons: dict[str, int] = {}
    constraint_rounds = 0
    hard_fail_rounds = 0
    soft_warn_rounds = 0
    evidence_only_rounds = 0
    symptom_hit_rounds = 0
    joint_context_rounds = 0
    joint_context_penalty_total = 0.0

    for index, record in enumerate(candidate_history, start=1):
        previous = self.history[index - 1] if index - 1 < len(self.history) else None
        if record.accepted:
            accepted_rounds += 1
        else:
            rejected_rounds += 1
            advice = record.llm_advice if isinstance(record.llm_advice, dict) else {}
            rollback_reason = str(advice.get("rollback_reason") or "").strip()
            if rollback_reason:
                rollback_reasons[rollback_reason] = rollback_reasons.get(rollback_reason, 0) + 1

        if previous is not None:
            delta = record.eval_score - previous.eval_score
            objective_deltas.append(delta)
            if delta > max(0.0, self._objective_gain_threshold() - 0.001):
                objective_gains += 1
            elif delta < -self._component_drop_tolerance():
                objective_losses += 1

            if self._round_symptom_hit(record, previous):
                symptom_hit_rounds += 1

        analysis_evidence = record.analysis_evidence if isinstance(record.analysis_evidence, dict) else {}
        constraint_summary = analysis_evidence.get("constraint_summary", {}) if isinstance(analysis_evidence, dict) else {}
        if isinstance(constraint_summary, dict):
            triggered_counts = constraint_summary.get("triggered_counts", {})
            if isinstance(triggered_counts, dict):
                hard_fail = int(triggered_counts.get("hard_fail", 0) or 0)
                soft_warn = int(triggered_counts.get("soft_warn", 0) or 0)
                evidence_only = int(triggered_counts.get("evidence_only", 0) or 0)
                if hard_fail or soft_warn or evidence_only:
                    constraint_rounds += 1
                if hard_fail:
                    hard_fail_rounds += 1
                if soft_warn:
                    soft_warn_rounds += 1
                if evidence_only:
                    evidence_only_rounds += 1

        score_snapshot = self._score_snapshot(record.output_parameters, record.residuals_pattern, analysis_evidence)
        joint_context = score_snapshot.get("joint_ai_context", {})
        if isinstance(joint_context, dict) and joint_context:
            joint_context_rounds += 1
            joint_context_penalty_total += self._safe_float(score_snapshot.get("joint_context_penalty", 0.0)) or 0.0

    candidate_rounds = len(candidate_history)
    return {
        "rounds": candidate_rounds,
        "accepted_rounds": accepted_rounds,
        "rejected_rounds": rejected_rounds,
        "acceptance_rate": accepted_rounds / candidate_rounds,
        "rollback_rate": rejected_rounds / candidate_rounds,
        "objective_gain_rounds": objective_gains,
        "objective_loss_rounds": objective_losses,
        "objective_gain_rate": objective_gains / candidate_rounds,
        "objective_delta_average": self._mean_or_none(objective_deltas) or 0.0,
        "rollback_reasons": rollback_reasons,
        "constraint_hits": {
            "rounds": constraint_rounds,
            "hard_fail_rounds": hard_fail_rounds,
            "soft_warn_rounds": soft_warn_rounds,
            "evidence_only_rounds": evidence_only_rounds,
            "hit_rate": constraint_rounds / candidate_rounds,
        },
        "symptom_hits": {
            "rounds": candidate_rounds,
            "hit_rounds": symptom_hit_rounds,
            "hit_rate": symptom_hit_rounds / candidate_rounds,
        },
        "joint_context": {
            "rounds": joint_context_rounds,
            "penalty_total": joint_context_penalty_total,
        },
    }


def _round_symptom_hit(self: Any, record: Any, previous_record: Any) -> bool:
    if previous_record is None or not isinstance(record.changes, dict) or not record.changes:
        return False

    change_keys = {str(name).strip().lower() for name in record.changes.keys() if str(name).strip()}
    if not change_keys:
        return False

    target_keys = self._symptom_target_params(record.analysis_evidence)
    if not target_keys:
        return False

    if not (change_keys & target_keys):
        return False

    delta = record.eval_score - previous_record.eval_score
    if delta > max(0.0, self._objective_gain_threshold() - 0.001):
        return True
    return (record.r_squared - previous_record.r_squared) > self._r_squared_drop_tolerance()


def _symptom_target_params(self: Any, analysis_evidence: dict[str, Any]) -> set[str]:
    targets: set[str] = set()
    if isinstance(analysis_evidence, dict):
        structured = analysis_evidence.get("symptoms", [])
        if isinstance(structured, list):
            for symptom in structured:
                if not isinstance(symptom, dict):
                    continue
                for item in symptom.get("target_params", []):
                    param = str(item or "").strip().lower()
                    if param and " " not in param and len(param) <= 40:
                        targets.add(param)

        symptoms = analysis_evidence.get("actionable_symptoms", [])
        if isinstance(symptoms, list):
            for symptom in symptoms:
                text = str(symptom or "").strip().lower()
                if not text:
                    continue
                if "->" in text:
                    text = text.split("->", 1)[1]
                if "expected evidence change:" in text:
                    text = text.split("expected evidence change:", 1)[0]
                for piece in re.split(r"[/,;|]", text):
                    param = piece.strip().strip(".")
                    if param and " " not in param and len(param) <= 40:
                        targets.add(param)

    focus = self._joint_tuning_focus()
    targets.update(name.lower() for name in focus.keys())
    return targets
