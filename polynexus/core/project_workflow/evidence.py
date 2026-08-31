"""Project-workflow run envelopes and provider evidence projection."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any, Iterable, Mapping

from polynexus.core.agent_workflow.models import AnalysisRun, canonical_json

from .models import EvidenceItem


@dataclass(frozen=True)
class ProjectWorkflowRun:
    """Stable project-facing result for one delegated analysis request."""

    run_id: str
    request_hash: str
    plan_hash: str
    recipe_hash: str | None
    status: str
    outputs: tuple[str, ...] = ()
    evidence_items: tuple[EvidenceItem, ...] = ()
    manifest_path: str | None = None
    analysis_run: AnalysisRun | None = None
    reason_codes: tuple[str, ...] = ()

    @property
    def evidence(self) -> tuple[EvidenceItem, ...]:
        return self.evidence_items

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "request_hash": self.request_hash,
            "plan_hash": self.plan_hash,
            "recipe_hash": self.recipe_hash,
            "status": self.status,
            "outputs": list(self.outputs),
            "evidence_items": [item.to_dict() for item in self.evidence_items],
            "manifest_path": self.manifest_path,
            "reason_codes": list(self.reason_codes),
            "analysis_run": self.analysis_run.to_dict() if self.analysis_run else None,
        }


@dataclass(frozen=True)
class ProjectAnalysisSummary:
    """AI-facing projection of a project analysis without provider internals."""

    computation: str
    data_quality: str
    publication: str
    runs: tuple[ProjectWorkflowRun, ...] = ()
    package: Mapping[str, Any] | None = None
    reason_codes: tuple[str, ...] = ()
    messages: tuple[str, ...] = ()
    candidate_groups: tuple[Mapping[str, Any], ...] = ()
    selected_group: Mapping[str, Any] | None = None
    selected_groups: tuple[str, ...] = ()
    figure_candidates: Mapping[str, Any] | None = None
    result_tables: tuple[Mapping[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        evidence_items = tuple(item for run in self.runs for item in run.evidence_items)
        return {
            "computation": self.computation,
            "data_quality": self.data_quality,
            "publication": self.publication,
            "runs": [run.to_dict() for run in self.runs],
            "package": dict(self.package) if self.package else None,
            "evidence_count": len(evidence_items),
            "figures": list(dict.fromkeys(path for item in evidence_items for path in item.figures)),
            "tables": list(dict.fromkeys(path for item in evidence_items for path in item.tables)),
            "reason_codes": list(self.reason_codes),
            "messages": list(self.messages),
            "candidate_groups": [dict(value) for value in self.candidate_groups],
            "selected_group": dict(self.selected_group) if self.selected_group else None,
            "selected_groups": list(self.selected_groups),
            "figure_candidates": dict(self.figure_candidates) if self.figure_candidates else None,
            "result_tables": [dict(value) for value in self.result_tables],
        }


def evidence_items_from_run(
    run: AnalysisRun,
    *,
    run_id: str,
    raw_sources: Iterable[str],
) -> tuple[EvidenceItem, ...]:
    """Convert public provider steps to constrained project evidence records."""
    raw_refs = tuple(str(value) for value in raw_sources)
    items: list[EvidenceItem] = []
    for step in run.steps:
        if step.status not in {"completed", "review_required"}:
            continue
        # Lifecycle labels are intentionally kept compatible with historical
        # Agent bundles, but the shared computation axis is authoritative for
        # evidence promotion.  A legacy adapter must not be able to relabel a
        # missing-input/blocked/failed node as reviewable evidence.
        if not _step_is_computable(step):
            continue
        summary = dict(step.result_summary)
        if step.compute_run is not None and "compute_run" not in summary:
            summary["compute_run"] = dict(step.compute_run)
        analysis_evidence = dict(step.analysis_evidence)
        supported: tuple[str, ...] = ()
        summary_text = analysis_evidence.get("summary")
        if isinstance(summary_text, str) and summary_text:
            supported = (f"{step.step_id}:{summary_text}",)
        elif summary:
            # This is an observed provider output, not a scientific conclusion.
            supported = (
                f"Observed {step.technique} provider result for {step.step_id}; interpretation requires review.",
            )
        figures = _referenced_paths(step.figure_references)
        item = EvidenceItem.create(
            evidence_id=f"{run_id}:{step.step_id}",
            kind="quantitative_result",
            technique=step.technique,
            claim_scope=f"{step.technique} provider result for {step.step_id}",
            observed_results={
                "result_summary": summary,
                "analysis_evidence": analysis_evidence,
            },
            supported_interpretations=supported,
            # Run-wide workflow boundaries remain package-level.  A single
            # observation may only state its own provider limitations plus its
            # own review status.
            disallowed_conclusions=("human_review_required",)
            if step.status == "review_required"
            else (),
            source_runs=(run_id,),
            raw_sources=raw_refs,
            figures=figures,
            tables=(),
            status=step.status,
            limitations=tuple(dict.fromkeys(step.reason_codes)),
        )
        items.append(item)
    return tuple(items)


def _step_is_computable(step: Any) -> bool:
    """Return whether a workflow step may produce an evidence item.

    Historical steps have no shared state and remain packageable when their
    lifecycle status is completed/review_required.  Once a shared state or
    ComputeRun projection is present, non-computed computability is a hard
    gate.  This helper deliberately does not inspect provider-specific values.
    """

    state = getattr(step, "computation_state", None)
    if state is not None:
        computability = getattr(state, "computability", None)
        if computability is None and isinstance(state, Mapping):
            computability = state.get("computability")
        if str(computability or "").strip().lower() != "computed":
            return False
    compute_run = getattr(step, "compute_run", None)
    if isinstance(compute_run, Mapping):
        status = str(compute_run.get("status", "")).strip().lower()
        if status and status != "completed":
            return False
        run_state = compute_run.get("computation_state", compute_run.get("state"))
        if isinstance(run_state, Mapping):
            if str(run_state.get("computability", "")).strip().lower() != "computed":
                return False
        elif run_state is not None:
            computability = getattr(run_state, "computability", None)
            if str(computability or "").strip().lower() != "computed":
                return False
    return True


def _referenced_paths(value: Mapping[str, Any]) -> tuple[str, ...]:
    paths: list[str] = []
    for candidate in value.values():
        if isinstance(candidate, (str, Path)):
            paths.append(str(candidate))
        elif isinstance(candidate, Mapping):
            paths.extend(_referenced_paths(candidate))
        elif isinstance(candidate, (list, tuple)):
            paths.extend(
                str(item)
                for item in candidate
                if isinstance(item, (str, Path))
            )
    return tuple(dict.fromkeys(paths))


def stable_run_id(request_hash: str, recipe_hash: str, source_hashes: Iterable[str]) -> str:
    payload = {
        "request_hash": request_hash,
        "recipe_hash": recipe_hash,
        "source_hashes": sorted(str(value) for value in source_hashes),
    }
    digest = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
    return f"run-{digest[:24]}"


__all__ = ["ProjectAnalysisSummary", "ProjectWorkflowRun", "evidence_items_from_run", "stable_run_id"]
