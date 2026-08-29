"""Suite-level handoff projection for writing skills."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from polynexus.core.project_workflow.evidence_view import load_evidence_package_view


def build_suite_handoff(package_path: str | Path) -> dict[str, Any]:
    """Validate an evidence package and return package-relative skill inputs."""
    root = Path(package_path).expanduser().resolve()
    try:
        view = load_evidence_package_view(root)
    except (OSError, ValueError) as exc:
        return {
            "status": "blocked",
            "reason_codes": ["evidence_package_invalid"],
            "package": str(root),
            "error": str(exc),
        }
    files = {
        "ars_writing_input": "ars-writing-input.json",
        "result_tables": "result-tables.json",
        "writing_evidence": "writing-evidence.json",
        "citation_metrics": "citation-metrics.json",
    }
    optional = {"review_decisions": "review-decision.json"}
    missing = [name for name, relative in files.items() if not (root / relative).is_file()]
    if missing:
        return {"status": "blocked", "reason_codes": ["evidence_package_invalid", "handoff_file_missing"], "missing": missing, "package": str(root)}
    payload: dict[str, Any] = {
        "version": 1,
        "status": "ready",
        "package": {
            "path": str(root),
            "package_id": view.package_id,
            "version": view.version,
            "status": view.status,
            "handoff_schema": "v1",
        },
        "files": files,
        "human_review_required": bool(view.human_review) or view.status == "review_required",
        "human_review_count": len(view.human_review),
        "techniques": [item.key for item in view.techniques],
        "run_ids": list(view.run_ids),
        "metric_count": len(view.metrics),
    }
    if (root / optional["review_decisions"]).is_file():
        payload["files"]["review_decisions"] = optional["review_decisions"]
    return payload


__all__ = ["build_suite_handoff"]
