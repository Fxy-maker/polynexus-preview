"""Validated ARS/Codex manuscript preparation plans."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .evidence_view import EvidencePackageView, load_evidence_package_view
from .models import canonical_json


_BRIEF_FIELDS = frozenset({
    "version", "title_hint", "research_question", "comparison_scope",
    "figure_budget", "figure_intent", "technique_roles", "notes",
})
_SCOPE_FIELDS = frozenset({"selected_techniques", "selected_evidence_ids", "selected_metric_ids"})
_BUDGET_FIELDS = frozenset({"main_max", "supporting_max"})
_FIGURE_ROLES = frozenset({"main", "supporting"})
_TECHNIQUE_ROLES = frozenset({"observed_result", "structural_context", "diagnostic_context"})


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
        if set(payload) - _BRIEF_FIELDS:
            raise ValueError("paper brief fields are invalid")
        scope = _mapping(payload.get("comparison_scope", {}), "comparison scope")
        budget = _mapping(payload.get("figure_budget", {}), "figure budget")
        figure_intent = _mapping(payload.get("figure_intent", {}), "figure intent")
        technique_roles = _mapping(payload.get("technique_roles", {}), "technique roles")
        if set(scope) - _SCOPE_FIELDS or set(budget) - _BUDGET_FIELDS:
            raise ValueError("paper brief fields are invalid")
        version = _integer(payload.get("version"), "version")
        research_question = _required_text(payload.get("research_question"), "research question")
        main_max = _integer(budget.get("main_max", 6), "main figure budget")
        supporting_max = _integer(budget.get("supporting_max", 12), "supporting figure budget")
        if version != 1 or main_max < 0 or supporting_max < 0:
            raise ValueError("paper brief is invalid")
        intents = {str(key): _required_text(value, "figure intent") for key, value in figure_intent.items()}
        roles = {str(key).lower(): _required_text(value, "technique role") for key, value in technique_roles.items()}
        if any(value not in _FIGURE_ROLES for value in intents.values()):
            raise ValueError("figure intent is invalid")
        if any(value not in _TECHNIQUE_ROLES for value in roles.values()):
            raise ValueError("technique role is invalid")
        return cls(
            version=version,
            title_hint=_optional_text(payload.get("title_hint")),
            research_question=research_question,
            selected_techniques=tuple(value.lower() for value in _string_list(scope.get("selected_techniques", ()), "technique")),
            selected_evidence_ids=_string_list(scope.get("selected_evidence_ids", ()), "evidence"),
            selected_metric_ids=_string_list(scope.get("selected_metric_ids", ()), "metric"),
            main_max=main_max,
            supporting_max=supporting_max,
            figure_intent=intents,
            technique_roles=roles,
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
    package_hash = _validate_package_pin(root, manifest)
    if not (root / "figure-index.json").is_file():
        raise ValueError("figure index is invalid")
    view = load_evidence_package_view(root)
    known_techniques = tuple(item.key for item in view.techniques)
    techniques = _require_known(brief.selected_techniques, known_techniques, "technique")
    if any(key not in known_techniques or key not in techniques for key in brief.technique_roles):
        raise ValueError("technique role selection is invalid")
    evidence = _require_known(brief.selected_evidence_ids, (item.evidence_id for item in view.evidence), "evidence")
    metrics = _require_known(brief.selected_metric_ids, (item.metric_id for item in view.metrics), "metric")
    metric_by_id = {item.metric_id: item for item in view.metrics}
    results = tuple(item for item in metrics if metric_by_id[item].writing_eligibility == "results_candidate")
    discussion = tuple(item for item in metrics if metric_by_id[item].writing_eligibility != "results_candidate")
    figure_ids = {item.id for item in view.figure_views}
    _require_known(tuple(brief.figure_intent), figure_ids, "figure")
    main_figures = tuple(key for key, role in brief.figure_intent.items() if role == "main")
    supporting_figures = tuple(key for key, role in brief.figure_intent.items() if role == "supporting")
    if len(main_figures) > brief.main_max or len(supporting_figures) > brief.supporting_max:
        raise ValueError("figure budget is invalid")
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
        "package_hash": package_hash,
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


def _validate_package_pin(root: Path, manifest: Mapping[str, Any]) -> str:
    expected = str(manifest.get("package_hash", ""))
    unsigned = {key: value for key, value in manifest.items() if key != "package_hash"}
    actual = hashlib.sha256(canonical_json(unsigned).encode("utf-8")).hexdigest()
    if not expected or not hmac.compare_digest(expected, actual):
        raise ValueError("evidence package hash is invalid")
    _validate_package_artifacts(root, manifest)
    return expected


def _validate_package_artifacts(root: Path, manifest: Mapping[str, Any]) -> None:
    values = manifest.get("artifact_hashes")
    if not isinstance(values, list):
        raise ValueError("package artifact integrity is invalid")
    expected: dict[str, str] = {}
    for value in values:
        if not isinstance(value, Mapping):
            raise ValueError("package artifact integrity is invalid")
        relative = str(value.get("path", ""))
        digest = str(value.get("sha256", ""))
        path = Path(relative)
        if (
            not relative or Path(relative).is_absolute() or "\\" in relative
            or ".." in path.parts or relative in expected
            or len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest)
        ):
            raise ValueError("package artifact integrity is invalid")
        expected[relative] = digest
    actual = {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file() and path.name != "manifest.json"
    }
    if actual != expected:
        raise ValueError("package artifact integrity is invalid")


def _require_known(requested: tuple[str, ...], available: Iterable[str], kind: str) -> tuple[str, ...]:
    known = tuple(dict.fromkeys(str(value) for value in available))
    selected = requested or known
    if any(value not in known for value in selected):
        raise ValueError(f"{kind} selection is invalid")
    return tuple(dict.fromkeys(selected))


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} is invalid")
    return value


def _integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label} is invalid")
    return value


def _string_list(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{label} selection is invalid")
    return tuple(dict.fromkeys(item.strip() for item in value))


def _required_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is invalid")
    return value.strip()


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


__all__ = ["PaperBrief", "ManuscriptPlan", "build_manuscript_plan"]
