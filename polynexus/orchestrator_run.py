from __future__ import annotations

import inspect
from polynexus.orchestrator_run_bootstrap import (
    _initialize_run_session,
)
from polynexus.orchestrator_run_round import (
    _execute_round_iteration,
)


def run(self) -> dict[str, Any]:
    data_path, engine, baseline = _initialize_run_session(self)

    converged = False
    convergence_reason = "max_rounds"

    for round_num in range(1, self.max_rounds + 1):
        outcome = _execute_round_iteration(self, engine, baseline, round_num)
        if outcome.get("stop"):
            converged = bool(outcome.get("converged", False))
            reason = str(outcome.get("convergence_reason", "") or "")
            if reason:
                convergence_reason = reason
            break

    return self._final_report(data_path, converged, convergence_reason)

