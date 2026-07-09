from __future__ import annotations

from typing import Any


def _record_direct_change_candidate(
    self,
    engine,
    round_num: int,
    advice: dict[str, Any],
    previous_r_squared: float,
    changes: dict[str, Any],
    prompt: str,
) -> dict[str, Any]:
    engine.result.parameters = engine.get_parameters()

    candidate = self._record_round(
        engine,
        round_num,
        advice,
        before_r_squared=previous_r_squared,
        changes=changes,
        accepted=True,
        prompt=prompt,
    )
    return {
        "candidate": candidate,
        "delta": candidate.r_squared - previous_r_squared,
    }
