"""Technique-neutral GUI projection for adaptive analysis plans."""

from __future__ import annotations

from typing import Any, Mapping


def analysis_plan_evaluation_view(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a defensive JSON view shared with CLI and ARS consumers."""
    if not isinstance(payload, Mapping) or payload.get("version") != 1:
        raise ValueError("analysis plan evaluation view is invalid")
    required = ("plan_id", "plan_hash", "candidates", "review_limits", "replay")
    if any(not payload.get(key) and key in {"plan_id", "plan_hash"} for key in required):
        raise ValueError("analysis plan evaluation identity is missing")
    candidates = payload.get("candidates")
    review_limits = payload.get("review_limits")
    replay = payload.get("replay")
    if not isinstance(candidates, list) or not all(isinstance(item, Mapping) for item in candidates):
        raise ValueError("analysis plan evaluation candidates are invalid")
    if not isinstance(review_limits, list) or not all(isinstance(item, str) and item.strip() for item in review_limits):
        raise ValueError("analysis plan evaluation review limits are invalid")
    if not isinstance(replay, Mapping):
        raise ValueError("analysis plan evaluation replay is invalid")
    return dict(payload)


def analysis_plan_evaluation_context(report: Mapping[str, Any]) -> dict[str, Any]:
    """Keep only the shared plan projection in GUI tuning context."""
    projection = report.get("analysis_plan_evaluation") if isinstance(report, Mapping) else None
    if not isinstance(projection, Mapping):
        return {}
    try:
        return {"analysis_plan_evaluation": analysis_plan_evaluation_view(projection)}
    except ValueError:
        return {}


def bind_analysis_plan_evaluation_to_run(
    tuning_context: Mapping[str, Any],
    run_id: str,
) -> dict[str, Any]:
    """Return tuning context whose evaluation is explicitly bound to one run."""
    context = dict(tuning_context) if isinstance(tuning_context, Mapping) else {}
    resolved_run_id = str(run_id or "").strip()
    projection = context.get("analysis_plan_evaluation")
    if not resolved_run_id or not isinstance(projection, Mapping):
        context.pop("analysis_plan_evaluation", None)
        context.pop("analysis_plan_evaluation_run_id", None)
        return context
    try:
        context["analysis_plan_evaluation"] = analysis_plan_evaluation_view(projection)
    except ValueError:
        context.pop("analysis_plan_evaluation", None)
        context.pop("analysis_plan_evaluation_run_id", None)
        return context
    context["analysis_plan_evaluation_run_id"] = resolved_run_id
    return context


def analysis_plan_evaluation_summary(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Project a concise, technique-neutral robustness summary for the GUI."""
    evaluation = analysis_plan_evaluation_view(payload)
    candidates = evaluation["candidates"]
    return {
        "plan_id": str(evaluation["plan_id"]),
        "candidate_count": len(candidates),
        "stable_candidate_count": sum(
            str(candidate.get("status", "")).strip().lower() == "stable"
            for candidate in candidates
            if isinstance(candidate, Mapping)
        ),
        "review_limits": tuple(str(item) for item in evaluation["review_limits"]),
        "replay_status": str(evaluation["replay"].get("status", "")),
    }


__all__ = [
    "analysis_plan_evaluation_view",
    "analysis_plan_evaluation_context",
    "bind_analysis_plan_evaluation_to_run",
    "analysis_plan_evaluation_summary",
]
