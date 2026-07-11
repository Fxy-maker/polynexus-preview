from __future__ import annotations

from typing import Any


def _complete_direct_change_candidate(
    self,
    round_num: int,
    previous_r_squared: float,
    changes: dict[str, Any],
    candidate,
    status: str,
    delta: float,
) -> dict[str, Any]:
    self.history.append(candidate)
    converged = False
    convergence_reason = ""
    if status != "rolled_back" and delta < 0.001 and self._can_converge_on_small_delta(candidate, round_num):
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
