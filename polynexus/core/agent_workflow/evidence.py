"""Normalize public provider evidence into explicit scientific conclusion scopes."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .models import EvidenceRecord, WorkflowStepResult


_WORKFLOW_LIMITS = (
    "unique_hydrogen_bond_species",
    "absolute_scattering_quantity_without_background",
)


_MISSING = object()


def _normalized_state(value: Any):
    """Return a canonical computation state, or ``None`` when malformed.

    Shared projections are serialized mappings, while in-memory workflow
    steps normally carry the canonical ``ComputationState`` object.  Parsing
    mappings through the shared contract keeps this consumer aligned with the
    producer and, importantly, treats partial/unknown state as unusable.
    """

    from polynexus.core.ai_platform.contracts import ComputationState

    if isinstance(value, ComputationState):
        return value
    if not isinstance(value, Mapping):
        return None
    try:
        return ComputationState.from_dict(value)
    except Exception:
        # Evidence promotion is a read-only boundary: any malformed state,
        # including a non-standard mapping implementation, must fail closed.
        return None


def _projection_state(projection: Mapping[str, Any]):
    """Read the canonical state aliases from one serialized ComputeRun."""

    states: list[Any] = []
    for key in ("computation_state", "state"):
        if key in projection:
            states.append(projection[key])
    if not states:
        return None

    normalized = [_normalized_state(value) for value in states]
    if any(value is None for value in normalized):
        return None
    first = normalized[0]
    if any(value.to_dict() != first.to_dict() for value in normalized[1:]):
        return None
    return first


def _projection_allows_evidence(projection: Any) -> bool:
    """Require a complete, successful shared ComputeRun projection."""

    if not isinstance(projection, Mapping):
        return False
    status = projection.get("status", _MISSING)
    if not isinstance(status, str) or status.strip().casefold() != "completed":
        return False
    state = _projection_state(projection)
    return state is not None and state.computability == "computed"


def _step_allows_evidence(step: WorkflowStepResult) -> bool:
    """Apply the shared state gate while retaining legacy no-projection steps."""

    top_state = getattr(step, "computation_state", None)
    normalized_top_state = None
    if top_state is not None:
        normalized_top_state = _normalized_state(top_state)
        if normalized_top_state is None or normalized_top_state.computability != "computed":
            return False

    projections: list[Any] = []
    direct_projection = getattr(step, "compute_run", _MISSING)
    if direct_projection is not _MISSING and direct_projection is not None:
        projections.append(direct_projection)

    summary = getattr(step, "result_summary", None)
    if isinstance(summary, Mapping) and "compute_run" in summary:
        # The key itself marks a shared projection.  ``None`` is therefore a
        # malformed projection rather than an absent legacy field.
        projections.append(summary["compute_run"])

    if not projections:
        return True

    normalized_projection_states = []
    for projection in projections:
        if not _projection_allows_evidence(projection):
            return False
        state = _projection_state(projection)
        # _projection_allows_evidence already guarantees a canonical state;
        # retaining it here lets us reject contradictory duplicate projections.
        normalized_projection_states.append(state)

    first_projection_state = normalized_projection_states[0]
    if normalized_top_state is not None and normalized_top_state.to_dict() != first_projection_state.to_dict():
        return False
    if any(state.to_dict() != first_projection_state.to_dict() for state in normalized_projection_states[1:]):
        return False
    return True


def build_evidence(steps: Iterable[WorkflowStepResult]) -> EvidenceRecord:
    """Keep direct outputs and technique limits visible to every consumer."""
    observed: list[str] = []
    supported: list[str] = []
    disallowed = list(_WORKFLOW_LIMITS)
    for step in steps:
        if step.status not in {"completed", "review_required"}:
            continue
        # A lifecycle status can remain ``review_required`` for compatibility,
        # but the shared ComputeRun/state projection is authoritative for
        # promotion.  Never turn a needs-input/blocked/failed or malformed
        # node into evidence merely because a legacy adapter labelled its step
        # as reviewable.  Steps with no shared projection retain the historical
        # compatibility behavior.
        if not _step_allows_evidence(step):
            continue
        observed.append(f"{step.step_id}:public_result_available")
        summary = step.analysis_evidence.get("summary")
        if isinstance(summary, str) and summary:
            supported.append(f"{step.step_id}:{summary}")
        warnings = step.result_summary.get("validation_warnings", [])
        if warnings:
            disallowed.append(f"{step.step_id}:unqualified_export")
    return EvidenceRecord(
        observed=tuple(observed),
        supported_interpretations=tuple(supported),
        disallowed_conclusions=tuple(dict.fromkeys(disallowed)),
    )
