from __future__ import annotations

from typing import Any


def _handle_candidate_plan_round(
    self,
    engine,
    round_num: int,
    advice: dict[str, Any],
    previous_record,
    previous_r_squared: float,
    candidate_plans: list[dict[str, Any]],
    prompt: str,
) -> dict[str, Any]:
    candidate_outcome = self._run_saxs_candidate_round(
        engine,
        round_num,
        advice if isinstance(advice, dict) else {},
        previous_record,
        candidate_plans,
        prompt,
    )
    candidate = candidate_outcome["record"]
    status = str(candidate_outcome.get("status", "rejected") or "rejected")
    changes = dict(candidate_outcome.get("changes", {}) or {})
    delta = candidate.r_squared - previous_r_squared

    self.history.append(candidate)
    converged = False
    convergence_reason = ""
    if candidate.accepted and delta < 0.001 and self._can_converge_on_small_delta(candidate, round_num):
        converged = True
        convergence_reason = "delta_r_squared<0.001"
        if status == "improved":
            status = "converged"
    elif status == "rolled_back" and self._can_converge_after_rollback(round_num):
        converged = True
        convergence_reason = "no_improvement_after_history"
    current_advice = candidate.llm_advice if isinstance(candidate.llm_advice, dict) else {}
    self._emit_progress(
        round_num,
        previous_r_squared,
        candidate.r_squared,
        changes,
        status,
        error=str(current_advice.get("rollback_reason", "") or ""),
        converged=converged,
        target_symptom=candidate.target_symptom,
        symptom_summary=candidate.symptom_summary,
    )
    return {
        "stop": converged,
        "converged": converged,
        "convergence_reason": convergence_reason,
    }
