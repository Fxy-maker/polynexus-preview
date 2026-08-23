"""Validated ARS/Codex manuscript preparation plans."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .evidence_view import EvidencePackageView, load_evidence_package_view
from .models import canonical_json


@dataclass(frozen=True)
class PaperBrief:
    """AI-authored scope for one manuscript, without analysis controls."""

    version: int
    title_hint: str | None
    research_question: str
    selected_techniques: tuple[str, ...]
    selected_evidence_ids: tuple[str, ...]
    selected_metric_ids: tuple[str, ...]
    main_max: int
    supporting_max: int
    figure_intent: Mapping[str, str]
    technique_roles: Mapping[str, str]
    notes: str | None

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PaperBrief":
        scope = payload.get("comparison_scope", {})
        budget = payload.get("figure_budget", {})
        return cls(
            version=int(payload.get("version", 0)),
            title_hint=_optional_text(payload.get("title_hint")),
            research_question=str(payload.get("research_question", "")).strip(),
            selected_techniques=tuple(str(value).lower() for value in scope.get("selected_techniques", ())),
            selected_evidence_ids=tuple(str(value) for value in scope.get("selected_evidence_ids", ())),
            selected_metric_ids=tuple(str(value) for value in scope.get("selected_metric_ids", ())),
            main_max=int(budget.get("main_max", 6)),
            supporting_max=int(budget.get("supporting_max", 12)),
            figure_intent={str(key): str(value) for key, value in payload.get("figure_intent", {}).items()},
            technique_roles={str(key).lower(): str(value) for key, value in payload.get("technique_roles", {}).items()},
            notes=_optional_text(payload.get("notes")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "title_hint": self.title_hint,
            "research_question": self.research_question,
            "comparison_scope": {
                "selected_techniques": list(self.selected_techniques),
                "selected_evidence_ids": list(self.selected_evidence_ids),
                "selected_metric_ids": list(self.selected_metric_ids),
            },
            "figure_budget": {"main_max": self.main_max, "supporting_max": self.supporting_max},
            "figure_intent": dict(sorted(self.figure_intent.items())),
            "technique_roles": dict(sorted(self.technique_roles.items())),
            "notes": self.notes,
        }


@dataclass(frozen=True)
class ManuscriptPlan:
    """A hashable, package-pinned writing preparation artifact."""

    version: int
    plan_id: str
    plan_hash: str
    package: Mapping[str, Any]
    brief: Mapping[str, Any]
    selection: Mapping[str, tuple[str, ...]]
    writing_boundaries: Mapping[str, Any]
    status: str = "draft"

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "plan_id": self.plan_id,
            "plan_hash": self.plan_hash,
            "package": dict(self.package),
            "brief": dict(self.brief),
            "selection": {key: list(value) for key, value in self.selection.items()},
            "writing_boundaries": dict(self.writing_boundaries),
            "status": self.status,
        }


def build_manuscript_plan(package_path: str | Path, brief: PaperBrief) -> ManuscriptPlan:
    """Build a writing plan from package facts without altering the package."""
    root = Path(package_path).expanduser().resolve()
    manifest = _read_manifest(root)
    view = load_evidence_package_view(root)
    techniques = _selected(brief.selected_techniques, tuple(item.key for item in view.techniques))
    evidence = _selected(brief.selected_evidence_ids, tuple(item.evidence_id for item in view.evidence))
    metrics = _selected(brief.selected_metric_ids, tuple(item.metric_id for item in view.metrics))
    metric_by_id = {item.metric_id: item for item in view.metrics}
    results = tuple(item for item in metrics if metric_by_id[item].writing_eligibility == "results_candidate")
    discussion = tuple(item for item in metrics if metric_by_id[item].writing_eligibility != "results_candidate")
    main_figures = tuple(key for key, role in brief.figure_intent.items() if role == "main")
    supporting_figures = tuple(key for key, role in brief.figure_intent.items() if role == "supporting")
    evidence_by_id = {item.evidence_id: item for item in view.evidence}
    prohibited = tuple(dict.fromkeys(
        value for evidence_id in evidence for value in evidence_by_id[evidence_id].prohibited_conclusions
    ))
    human_review = tuple(
        {"evidence_id": item.evidence_id, "action": item.action, "reason": item.reason}
        for item in view.human_review if item.evidence_id in evidence
    )
    package = {
        "package_id": view.package_id,
        "version": view.version,
        "package_hash": str(manifest.get("package_hash", "")),
        "path": str(root),
    }
    selection = {
        "techniques": techniques,
        "evidence_ids": evidence,
        "results_metric_ids": results,
        "discussion_metric_ids": discussion,
        "main_figure_ids": main_figures,
        "supporting_figure_ids": supporting_figures,
    }
    boundaries = {
        "limitations": view.limitations,
        "prohibited_conclusions": prohibited,
        "human_review": human_review,
    }
    stable = {
        "version": 1,
        "package": {key: value for key, value in package.items() if key != "path"},
        "brief": brief.to_dict(),
        "selection": {key: list(value) for key, value in selection.items()},
        "writing_boundaries": boundaries,
        "status": "draft",
    }
    plan_hash = hashlib.sha256(canonical_json(stable).encode("utf-8")).hexdigest()
    return ManuscriptPlan(
        version=1,
        plan_id=f"manuscript-{plan_hash[:12]}",
        plan_hash=plan_hash,
        package=package,
        brief=brief.to_dict(),
        selection=selection,
        writing_boundaries=boundaries,
    )


def _read_manifest(root: Path) -> Mapping[str, Any]:
    try:
        value = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("evidence package manifest is invalid") from exc
    if not isinstance(value, Mapping):
        raise ValueError("evidence package manifest is invalid")
    return value


def _selected(requested: tuple[str, ...], available: tuple[str, ...]) -> tuple[str, ...]:
    return requested or available


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


__all__ = ["PaperBrief", "ManuscriptPlan", "build_manuscript_plan"]
