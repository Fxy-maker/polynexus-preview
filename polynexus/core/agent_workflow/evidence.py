"""Normalize public provider evidence into explicit scientific conclusion scopes."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from polynexus.core.compute.projection import (
    merge_compute_run_projections,
    parse_compute_run_projection,
)

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

    # Do not trust polymorphic state objects at an evidence boundary: a
    # subclass can override ``computability`` or ``to_dict`` after validation.
    if type(value) is ComputationState:
        return value
    if isinstance(value, ComputationState):
        return None
    if not isinstance(value, Mapping):
        return None
    try:
        return ComputationState.from_dict(value)
    except Exception:
        # Evidence promotion is a read-only boundary: any malformed state,
        # including a non-standard mapping implementation, must fail closed.
        return None


def _projection_state(projection: Mapping[str, Any]):
    """Read the canonical state from the shared projection parser."""

    parsed = parse_compute_run_projection(projection)
    return parsed.state if parsed.valid else None


def _projection_allows_evidence(projection: Any) -> bool:
    """Require a complete, successful shared ComputeRun projection."""

    parsed = parse_compute_run_projection(projection)
    return parsed.valid and parsed.computed


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
    direct_present = bool(getattr(step, "compute_run_present", False))
    if direct_present or (direct_projection is not _MISSING and direct_projection is not None):
        projections.append(direct_projection)

    summary = getattr(step, "result_summary", None)
    if isinstance(summary, Mapping) and "compute_run" in summary:
        # The key itself marks a shared projection.  ``None`` is therefore a
        # malformed projection rather than an absent legacy field.
        projections.append(summary["compute_run"])

    if not projections:
        return True

    parsed_projections = tuple(parse_compute_run_projection(value) for value in projections)
    merged_projection = merge_compute_run_projections(*parsed_projections)
    if not merged_projection.valid or not merged_projection.computed:
        return False
    if merged_projection.state is None:
        return False
    if normalized_top_state is not None and normalized_top_state.to_dict() != merged_projection.state.to_dict():
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
