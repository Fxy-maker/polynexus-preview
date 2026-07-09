from __future__ import annotations

from typing import Any

from .orchestrator_run_round_direct_failures import _reject_direct_change_attempt
from .orchestrator_run_round_direct_success import _record_direct_change_candidate


def _execute_direct_change_attempt(
    self,
    engine,
    round_num: int,
    advice: dict[str, Any],
    previous_r_squared: float,
    changes: dict[str, Any],
    prompt: str,
) -> dict[str, Any]:
    from polynexus import orchestrator as orchestrator_module

    ok, error = orchestrator_module.apply_changes(
        self._engine_config(engine),
        changes,
        technique=self.technique,
    )
    if not ok:
        return _reject_direct_change_attempt(
            self,
            engine,
            round_num,
            advice,
            previous_r_squared,
            changes,
            prompt,
            rollback_reason=error,
            rollback_detail="The proposed parameter change violates the local config constraints, so the run was skipped.",
            error=error,
        )

    if not engine.analyze():
        return _reject_direct_change_attempt(
            self,
            engine,
            round_num,
            advice,
            previous_r_squared,
            changes,
            prompt,
            rollback_reason="engine.analyze() failed",
            rollback_detail="The core analysis failed to finish, so the candidate was rolled back immediately.",
            error="engine.analyze() failed",
        )

    return _record_direct_change_candidate(
        self,
        engine,
        round_num,
        advice,
        previous_r_squared,
        changes,
        prompt,
    )
