from __future__ import annotations

from typing import Any

from .orchestrator_run_round_direct_flow import (
    _execute_direct_change_attempt,
    _finalize_direct_change_candidate,
)


def _handle_direct_change_round(
    self,
    engine,
    round_num: int,
    advice: dict[str, Any],
    previous_record,
    previous_r_squared: float,
    changes: dict[str, Any],
    prompt: str,
) -> dict[str, Any]:
    attempt = _execute_direct_change_attempt(
        self,
        engine,
        round_num,
        advice,
        previous_r_squared,
        changes,
        prompt,
    )
    terminal_outcome = attempt.get("terminal_outcome")
    if isinstance(terminal_outcome, dict):
        return terminal_outcome

    return _finalize_direct_change_candidate(
        self,
        engine,
        round_num,
        advice,
        previous_record,
        previous_r_squared,
        changes,
        attempt["candidate"],
        float(attempt["delta"]),
    )
