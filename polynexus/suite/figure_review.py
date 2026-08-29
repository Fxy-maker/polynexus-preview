"""Advisory ranking and append-only human figure decisions."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Iterable, Mapping

from .paper_contracts import FigurePlan


def rank_figure_candidates(plans: Iterable[FigurePlan], quality_reports: Mapping[str, Mapping[str, object]] | None = None) -> list[dict[str, object]]:
    quality_reports = quality_reports or {}
    ranked = []
    for plan in plans:
        report = quality_reports.get(plan.figure_id, {})
        quality_ok = report.get("status", "passed") == "passed"
        eligible = bool(plan.source_ids) and quality_ok and plan.status != "diagnostic"
        score = (3 if eligible else 0) + (1 if plan.metric_ids else 0) + (1 if plan.layout != "single" else 0)
        ranked.append({"figure_id": plan.figure_id, "score": score, "eligible": eligible, "reason": "bound_and_quality_checked" if eligible else "unbound_or_quality_review", "quality": dict(report)})
    return sorted(ranked, key=lambda x: (-int(x["score"]), str(x["figure_id"])))


def save_review_decisions(package_dir: str | Path, decisions: Iterable[tuple[str, str, str]], *, freeze: bool = False) -> Path:
    root = Path(package_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    path = root / "review-decision.json"
    values = []
    for figure_id, decision, reason in decisions:
        if decision not in {"selected", "rejected", "deferred"}:
            raise ValueError("figure decision is invalid")
        values.append({"figure_id": str(figure_id), "decision": decision, "reason": str(reason), "actor": "human", "timestamp": datetime.now(timezone.utc).isoformat()})
    payload = {"version": 1, "status": "frozen" if freeze else "review_required", "decisions": values}
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
    temporary.replace(path)
    return path


__all__ = ["rank_figure_candidates", "save_review_decisions"]
