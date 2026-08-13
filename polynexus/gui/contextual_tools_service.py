"""Technique-neutral availability state for advanced result-context tools."""

from __future__ import annotations

from typing import Any, Mapping

from .analysis_plan_view_service import analysis_plan_evaluation_view
from .workspace_context import WorkspaceContext, WorkspaceResultStatus


def contextual_tool_state(context: WorkspaceContext, tuning_context: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Expose advanced tools only from a persisted completed result context."""
    context = context if isinstance(context, WorkspaceContext) else WorkspaceContext.empty()
    completed = bool(context.run_id) and context.result_status is WorkspaceResultStatus.COMPLETE
    evaluation_payload = tuning_context.get("analysis_plan_evaluation") if isinstance(tuning_context, Mapping) else None
    evaluation = analysis_plan_evaluation_view(evaluation_payload) if isinstance(evaluation_payload, Mapping) else None
    robustness = {
        "available": bool(completed and evaluation),
        "plan_id": str(evaluation.get("plan_id", "")) if evaluation else "",
        "candidate_count": len(evaluation.get("candidates", ())) if evaluation else 0,
        "review_limits": tuple(str(item) for item in evaluation.get("review_limits", ())) if evaluation else (),
    }
    return {
        "joint": {"available": completed, "run_id": context.run_id if completed else ""},
        "robustness": robustness,
        "convergence": {"available": completed, "run_id": context.run_id if completed else ""},
    }


__all__ = ["contextual_tool_state"]
