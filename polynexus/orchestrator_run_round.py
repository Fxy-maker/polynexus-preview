from __future__ import annotations

import inspect
from typing import Any

from llm.llm_client import LLMCancelledError
from .orchestrator_run_round_handlers import (
    _handle_candidate_plan_round,
    _handle_direct_change_round,
    _handle_invalid_changes_round,
    _handle_noop_converged_round,
)


def _execute_round_iteration(self, engine, baseline, round_num: int) -> dict[str, Any]:
    from polynexus import orchestrator as orchestrator_module

    if self._cancel_event and self._cancel_event.is_set():
        return {"stop": True, "converged": False, "convergence_reason": "cancelled"}

    self._restore_best(engine)
    state = self._build_agent_state(engine, round_num)
    try:
        advise_kwargs: dict[str, Any] = {}
        if "workspace_context" in inspect.signature(self.advisor.advise).parameters:
            advise_kwargs["workspace_context"] = self.workspace_context
        if self._cancel_event is not None and "cancel_event" in inspect.signature(self.advisor.advise).parameters:
            advise_kwargs["cancel_event"] = self._cancel_event
        advice = self.advisor.advise(state, **advise_kwargs)
    except LLMCancelledError:
        return {"stop": True, "converged": False, "convergence_reason": "cancelled"}

    prompt = str(getattr(self.advisor, "last_prompt", ""))
    changes = advice.get("changes", {})
    previous_record = self._best_record or baseline
    previous_r_squared = previous_record.r_squared

    if not isinstance(changes, dict):
        return _handle_invalid_changes_round(
            self,
            engine,
            round_num,
            advice,
            changes,
            previous_r_squared,
            prompt,
        )

    candidate_plans: list[dict[str, Any]] = []
    if self.technique in {"dsc", "ir", "saxs", "waxs"}:
        candidate_plans = self._expand_technique_candidates(advice if isinstance(advice, dict) else {}, state)

    if not changes and not candidate_plans:
        return _handle_noop_converged_round(
            self,
            engine,
            round_num,
            advice,
            state,
            previous_r_squared,
            changes,
            prompt,
        )

    if candidate_plans:
        return _handle_candidate_plan_round(
            self,
            engine,
            round_num,
            advice,
            previous_record,
            previous_r_squared,
            candidate_plans,
            prompt,
        )
    return _handle_direct_change_round(
        self,
        engine,
        round_num,
        advice,
        previous_record,
        previous_r_squared,
        changes,
        prompt,
    )
