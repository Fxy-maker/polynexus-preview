from __future__ import annotations

from .orchestrator_run_round_direct_resolution_helpers import (
    _accept_direct_change_candidate,
    _reject_direct_change_candidate,
)


def _resolve_direct_change_candidate(
    self,
    engine,
    advice: dict[str, Any],
    previous_record,
    candidate,
) -> dict[str, Any]:
    quality_ok, quality_error = self._quality_guard(candidate)
    if not quality_ok:
        return _reject_direct_change_candidate(
            self,
            engine,
            advice,
            candidate,
            rollback_reason=quality_error,
            decision_metrics=self._decision_metrics(candidate, previous_record),
        )

    accepted, rollback_reason, decision_metrics = self._evaluate_candidate(candidate, previous_record)
    if accepted:
        return _accept_direct_change_candidate(self, engine, candidate)

    return _reject_direct_change_candidate(
        self,
        engine,
        advice,
        candidate,
        rollback_reason=rollback_reason,
        decision_metrics=decision_metrics,
    )
