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
    if not isinstance(payload.get("candidates"), list) or not isinstance(payload.get("review_limits"), list):
        raise ValueError("analysis plan evaluation candidates are invalid")
    return dict(payload)


def analysis_plan_evaluation_context(report: Mapping[str, Any]) -> dict[str, Any]:
    """Keep only the shared plan projection in GUI tuning context."""
    projection = report.get("analysis_plan_evaluation") if isinstance(report, Mapping) else None
    if not isinstance(projection, Mapping):
        return {}
    return {"analysis_plan_evaluation": analysis_plan_evaluation_view(projection)}


__all__ = ["analysis_plan_evaluation_view", "analysis_plan_evaluation_context"]
