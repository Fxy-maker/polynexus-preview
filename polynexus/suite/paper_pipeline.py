"""Evidence-first manuscript source assembly."""

from __future__ import annotations

from typing import Iterable, Any

from .paper_contracts import CitationRequest, ClaimRecord, FigurePlan, FormulaRecord, ManuscriptSource


def assemble_manuscript(
    source: ManuscriptSource,
    claims: Iterable[ClaimRecord] = (),
    figures: Iterable[FigurePlan] = (),
    citations: Iterable[CitationRequest] = (),
    formulas: Iterable[FormulaRecord] = (),
) -> dict[str, Any]:
    """Create a writing input projection; never changes scientific values."""
    claim_values = tuple(claims)
    figure_values = tuple(figures)
    citation_values = tuple(citations)
    formula_values = tuple(formulas)
    return {
        "version": 1, "source_id": source.source_id, "package_id": source.package_id,
        "sections": [
            {"name": "Results", "claim_ids": [c.claim_id for c in claim_values if c.role == "results"]},
            {"name": "Discussion", "claim_ids": [c.claim_id for c in claim_values if c.role != "results"]},
        ],
        "claims": [c.to_dict() for c in claim_values],
        "figures": [f.to_dict() for f in figure_values],
        "citations": [c.to_dict() for c in citation_values],
        "formulas": [f.to_dict() for f in formula_values],
        "limitations": list(source.limitations),
        "evidence_projection": dict(source.projection),
    }


__all__ = ["assemble_manuscript"]
