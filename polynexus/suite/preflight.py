"""Deterministic structural checks for manuscript source projections."""

from __future__ import annotations

from typing import Any, Mapping

from .paper_contracts import PreflightReport


def preflight_manuscript(manuscript: Mapping[str, Any]) -> PreflightReport:
    errors: list[str] = []
    warnings: list[str] = []
    source_id = str(manuscript.get("source_id", ""))
    if not source_id:
        errors.append("source_id_missing")
    claims = manuscript.get("claims", [])
    figures = manuscript.get("figures", [])
    citations = manuscript.get("citations", [])
    citation_keys = {str(c.get("key")) for c in citations if isinstance(c, Mapping)}
    formula_ids = {str(f.get("formula_id")) for f in manuscript.get("formulas", []) if isinstance(f, Mapping)}
    claim_ids = {str(c.get("claim_id")) for c in claims if isinstance(c, Mapping)}
    for section in manuscript.get("sections", []):
        if isinstance(section, Mapping):
            for claim_id in section.get("claim_ids", []):
                if str(claim_id) not in claim_ids:
                    errors.append(f"claim_unbound:{claim_id}")
    if not figures:
        warnings.append("no_figures")
    if not citations:
        warnings.append("no_citations")
    for claim in claims:
        if isinstance(claim, Mapping) and not (claim.get("evidence_ids") or claim.get("metric_ids")):
            errors.append(f"claim_without_evidence:{claim.get('claim_id', '')}")
        if isinstance(claim, Mapping):
            for key in claim.get("citation_keys", ()):
                if str(key) not in citation_keys:
                    errors.append(f"citation_unbound:{key}")
    checks = {"claims": "passed" if not errors else "failed", "figures": "passed" if figures else "review_required", "citations": "passed" if citations else "review_required", "formulas": "passed" if formula_ids or not manuscript.get("formulas") else "failed"}
    return PreflightReport.create(source_id=source_id or "unknown", errors=tuple(dict.fromkeys(errors)), warnings=tuple(dict.fromkeys(warnings)), checks=checks)


__all__ = ["preflight_manuscript"]
