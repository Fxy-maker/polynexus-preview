"""Read-only projection from an evidence package to manuscript source."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

from polynexus.core.project_workflow.evidence_view import load_evidence_package_view
from .paper_contracts import ClaimRecord, FigurePlan, ManuscriptSource, PaperBrief


def build_manuscript_source(package_path: str | Path, brief: PaperBrief | Mapping[str, Any] | None = None) -> ManuscriptSource:
    """Project package facts; no provider or numerical calculation is invoked."""
    view = load_evidence_package_view(package_path)
    if brief is not None and not isinstance(brief, PaperBrief):
        brief = PaperBrief.from_dict(brief)
    selected_evidence = set(brief.comparison_scope.get("selected_evidence_ids", ())) if brief else set()
    evidence = tuple(item for item in view.evidence if not selected_evidence or item.evidence_id in selected_evidence)
    claims: list[ClaimRecord] = []
    for item in evidence:
        ids = tuple(dict.fromkeys((*item.results_metric_ids, *item.discussion_metric_ids)))
        claims.append(ClaimRecord.create(
            text=f"Evidence {item.evidence_id} ({item.technique})",
            evidence_ids=(item.evidence_id,), metric_ids=ids, figure_ids=item.figures,
            role="results" if item.results_metric_ids else "discussion",
        ))
    figures: list[FigurePlan] = []
    for item in view.figure_views:
        figures.append(FigurePlan.create(title=item.id, layout="single", source_ids=(item.svg,), metric_ids=tuple(m.metric_id for m in view.metrics if item.id in m.figures)))
    limitations = tuple(dict.fromkeys((*view.limitations, *(v for e in evidence for v in e.limitations))))
    projection = {
        "package": {"package_id": view.package_id, "version": view.version},
        "metrics": [_metric_dict(m) for m in view.metrics if not selected_evidence or m.evidence_id in selected_evidence],
        "claims": [c.to_dict() for c in claims],
        "figures": [f.to_dict() for f in figures],
        "tables": list(view.tables),
        "limitations": list(limitations),
        "human_review": [{"evidence_id": h.evidence_id, "action": h.action, "reason": h.reason} for h in view.human_review],
    }
    source = ManuscriptSource.create(
        package_id=view.package_id,
        claim_ids=tuple(c.claim_id for c in claims),
        figure_plan_ids=tuple(f.figure_id for f in figures),
        table_ids=view.tables,
        limitations=limitations,
    )
    return replace(source, projection=projection)


def _metric_dict(metric: Any) -> dict[str, Any]:
    return {"metric_id": metric.metric_id, "technique": metric.technique, "metric_key": metric.metric_key, "value": metric.value, "unit": metric.unit, "method": metric.method, "source_locator": metric.source_locator, "evidence_id": metric.evidence_id, "run_id": metric.run_id, "status": metric.status, "writing_eligibility": metric.writing_eligibility, "reason_codes": list(metric.reason_codes), "figures": list(metric.figures), "tables": list(metric.tables)}


__all__ = ["build_manuscript_source"]
