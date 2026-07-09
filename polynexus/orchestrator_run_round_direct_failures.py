from __future__ import annotations

from typing import Any


def _reject_direct_change_attempt(
    self,
    engine,
    round_num: int,
    advice: dict[str, Any],
    previous_r_squared: float,
    changes: dict[str, Any],
    prompt: str,
    rollback_reason: str,
    rollback_detail: str,
    error: str,
) -> dict[str, Any]:
    rejected = dict(advice)
    rejected["rejected"] = True
    rejected["rollback_reason"] = rollback_reason
    rejected["rollback_detail"] = rollback_detail
    self._restore_best(engine)
    self.history.append(
        self._record_round(
            engine,
            round_num,
            rejected,
            before_r_squared=previous_r_squared,
            changes=changes,
            accepted=False,
            prompt=prompt,
        )
    )
    self._emit_progress(round_num, previous_r_squared, previous_r_squared, changes, "rejected", error)
    return {
        "terminal_outcome": {
            "stop": False,
            "converged": False,
            "convergence_reason": "",
        }
    }
