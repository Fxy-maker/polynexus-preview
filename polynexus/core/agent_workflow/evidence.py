"""Normalize public provider evidence into explicit scientific conclusion scopes."""

from __future__ import annotations

from collections.abc import Iterable

from .models import EvidenceRecord, WorkflowStepResult


_WORKFLOW_LIMITS = (
    "unique_hydrogen_bond_species",
    "absolute_scattering_quantity_without_background",
)


def build_evidence(steps: Iterable[WorkflowStepResult]) -> EvidenceRecord:
    """Keep direct outputs and technique limits visible to every consumer."""
    observed: list[str] = []
    supported: list[str] = []
    disallowed = list(_WORKFLOW_LIMITS)
    for step in steps:
        if step.status not in {"completed", "review_required"}:
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
