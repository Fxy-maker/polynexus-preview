from __future__ import annotations

from .orchestrator_run_round_direct_completion import _complete_direct_change_candidate
from .orchestrator_run_round_direct_resolution import _resolve_direct_change_candidate


def _finalize_direct_change_candidate(
    self,
    engine,
    round_num: int,
    advice: dict[str, Any],
    previous_record,
    previous_r_squared: float,
    changes: dict[str, Any],
    candidate,
    delta: float,
) -> dict[str, Any]:
    resolution = _resolve_direct_change_candidate(
        self,
        engine,
        advice,
        previous_record,
        candidate,
    )
    return _complete_direct_change_candidate(
        self,
        round_num,
        previous_r_squared,
        changes,
        resolution["candidate"],
        str(resolution["status"]),
        delta,
    )
