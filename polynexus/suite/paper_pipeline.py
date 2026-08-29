"""Evidence-first manuscript source assembly."""

from __future__ import annotations

from typing import Iterable, Any
import json
from pathlib import Path

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


def export_manuscript(manuscript: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    """Write non-destructive, reviewable manuscript artifacts."""
    root = Path(output_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "manuscript.json"
    md_path = root / "manuscript.md"
    json_path.write_text(json.dumps(manuscript, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
    lines = ["# Manuscript draft", "", f"Package: `{manuscript.get('package_id', '')}`", ""]
    for section in manuscript.get("sections", []):
        lines.extend([f"## {section.get('name', 'Section')}", ""])
        for claim_id in section.get("claim_ids", []):
            claim = next((c for c in manuscript.get("claims", []) if c.get("claim_id") == claim_id), None)
            if claim:
                lines.extend([claim.get("text", ""), ""])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    result = {"json": str(json_path), "markdown": str(md_path)}
    try:
        from docx import Document
        document = Document()
        document.add_heading("Manuscript draft", level=1)
        for section in manuscript.get("sections", []):
            document.add_heading(str(section.get("name", "Section")), level=2)
            for claim_id in section.get("claim_ids", []):
                claim = next((c for c in manuscript.get("claims", []) if c.get("claim_id") == claim_id), None)
                if claim:
                    document.add_paragraph(str(claim.get("text", "")))
        docx_path = root / "manuscript.docx"
        document.save(docx_path)
        result["docx"] = str(docx_path)
    except Exception:
        pass
    return result


__all__ = ["assemble_manuscript", "export_manuscript"]
