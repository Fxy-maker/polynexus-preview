from __future__ import annotations

from copy import deepcopy
from typing import Any


def _reject_direct_change_candidate(
    self,
    engine,
    advice: dict[str, Any],
    candidate,
    rollback_reason: str,
    decision_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rejected = dict(advice)
    rejected["rejected"] = True
    rejected["rollback_reason"] = rollback_reason
    if decision_metrics is not None:
        rejected["decision_metrics"] = decision_metrics
    rejected["rollback_detail"] = self._advice_rollback_detail(rejected)
    candidate.llm_advice = rejected
    candidate.accepted = False
    candidate.target_symptom = self._advice_target_symptom(rejected, candidate.analysis_evidence)
    candidate.rollback_detail = rejected["rollback_detail"]
    candidate.decision_summary = self._decision_summary(
        False,
        candidate.target_symptom,
        candidate.rollback_detail,
        {"objective_score": candidate.eval_score},
    )
    self._restore_best(engine)
    return {
        "candidate": candidate,
        "status": "rolled_back",
    }


def _accept_direct_change_candidate(
    self,
    engine,
    candidate,
) -> dict[str, Any]:
    self._best_r_squared = candidate.r_squared
    self._best_eval_score = candidate.eval_score
    self._best_record = candidate
    self._best_config = deepcopy(self._engine_config(engine))
    self._best_output = dict(candidate.output_parameters)
    return {
        "candidate": candidate,
        "status": "improved",
    }
