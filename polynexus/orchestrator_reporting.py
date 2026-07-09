from __future__ import annotations

from typing import Any

from polynexus.orchestrator_reporting_benchmark import _benchmark_summary
from polynexus.orchestrator_reporting_benchmark import _round_symptom_hit
from polynexus.orchestrator_reporting_benchmark import _symptom_target_params
from polynexus.orchestrator_reporting_guards import _component_drop_tolerance
from polynexus.orchestrator_reporting_guards import _objective_gain_threshold
from polynexus.orchestrator_reporting_guards import _quality_guard
from polynexus.orchestrator_reporting_guards import _r_squared_drop_tolerance

def _decision_summary(
    self: Any,
    accepted: bool,
    target_symptom: str,
    rollback_detail: str,
    score_snapshot: dict[str, Any],
) -> str:
    symptom_part = f"target={target_symptom}" if target_symptom else ""
    objective_part = f"objective={self._safe_float(score_snapshot.get('objective_score', 0.0)):.3f}"
    if accepted:
        parts = [part for part in (symptom_part, objective_part) if part]
        return "accepted" + (f" | {' | '.join(parts)}" if parts else "")
    detail = rollback_detail or "rolled back"
    parts = [part for part in (symptom_part, objective_part) if part]
    return detail + (f" | {' | '.join(parts)}" if parts else "")
