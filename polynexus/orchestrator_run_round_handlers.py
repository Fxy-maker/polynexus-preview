from __future__ import annotations

from typing import Any

from .orchestrator_run_round_candidate_handler import _handle_candidate_plan_round
from .orchestrator_run_round_direct_handler import _handle_direct_change_round


def _handle_invalid_changes_round(
    self,
    engine,
    round_num: int,
    advice: dict[str, Any],
    invalid_changes: Any,
    previous_r_squared: float,
    prompt: str,
) -> dict[str, Any]:
    advice = dict(advice)
    changes: dict[str, Any] = {}
    advice["changes"] = {}
    advice["rejected"] = True
    advice["rollback_reason"] = f"changes must be a dict, got {type(invalid_changes).__name__}"
    advice["rollback_detail"] = "The advisor returned an invalid changes payload, so this round was rejected before execution."
    self.history.append(
        self._record_round(
            engine,
            round_num,
            advice,
            before_r_squared=previous_r_squared,
            changes=changes,
            accepted=False,
            prompt=prompt,
        )
    )
    self._emit_progress(round_num, previous_r_squared, previous_r_squared, changes, "rejected", advice["rollback_reason"])
    return {"stop": False, "converged": False, "convergence_reason": ""}


def _handle_noop_converged_round(
    self,
    engine,
    round_num: int,
    advice: dict[str, Any],
    state: dict[str, Any],
    previous_r_squared: float,
    changes: dict[str, Any],
    prompt: str,
) -> dict[str, Any]:
    target_symptom = self._advice_target_symptom(advice if isinstance(advice, dict) else None, state.get("analysis_evidence", {}))
    symptom_summary = self._symptom_summary(state.get("symptoms", []))
    self.history.append(
        self._record_round(
            engine,
            round_num,
            advice,
            before_r_squared=previous_r_squared,
            changes=changes,
            accepted=True,
            prompt=prompt,
        )
    )
    self._emit_progress(
        round_num,
        previous_r_squared,
        previous_r_squared,
        changes,
        "converged",
        converged=True,
        target_symptom=target_symptom,
        symptom_summary=symptom_summary,
    )
    return {"stop": True, "converged": True, "convergence_reason": "optimal"}

