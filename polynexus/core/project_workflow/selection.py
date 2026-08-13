"""ARS-selected group and figure-candidate contracts."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Iterable

from .grouping import CandidateExperimentGroup
from .models import canonical_json


_FIGURE_INTENTS = frozenset({"describe_group", "compare_groups", "show_trend"})


@dataclass(frozen=True)
class FigureSelectionRequest:
    """ARS instruction naming candidate groups to analyze and visualize."""

    question: str
    selected_groups: tuple[str, ...]
    figure_intent: str = "describe_group"
    main_figure_limit: int = 2
    reason_codes: tuple[str, ...] = ()

    @classmethod
    def create(
        cls,
        *,
        question: str,
        selected_groups: Iterable[str],
        figure_intent: str = "describe_group",
        main_figure_limit: int = 2,
    ) -> "FigureSelectionRequest":
        groups = tuple(str(value) for value in selected_groups if str(value))
        intent = str(figure_intent)
        reasons: list[str] = []
        if not groups:
            reasons.append("selected_groups_missing")
        if len(set(groups)) != len(groups):
            reasons.append("selected_groups_duplicate")
        if intent not in _FIGURE_INTENTS:
            reasons.append("figure_intent_invalid")
        if main_figure_limit not in {1, 2}:
            reasons.append("main_figure_limit_invalid")
        if intent in {"describe_group", "show_trend"} and len(groups) != 1:
            reasons.append("selected_groups_intent_count_mismatch")
        if intent == "compare_groups" and len(groups) != 2:
            reasons.append("selected_groups_intent_count_mismatch")
        return cls(
            question=str(question),
            selected_groups=groups,
            figure_intent=intent,
            main_figure_limit=int(main_figure_limit),
            reason_codes=tuple(dict.fromkeys(reasons)),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "question": self.question,
            "selected_groups": list(self.selected_groups),
            "figure_intent": self.figure_intent,
            "main_figure_limit": self.main_figure_limit,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class ResolvedFigureSelection:
    """Validated project-local selection with inventory-backed group paths."""

    selection_id: str
    status: str
    request: FigureSelectionRequest
    groups: tuple[CandidateExperimentGroup, ...] = ()
    reason_codes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "selection_id": self.selection_id,
            "status": self.status,
            "request": self.request.to_dict(),
            "groups": [group.to_dict() for group in self.groups],
            "reason_codes": list(self.reason_codes),
        }


def resolve_figure_selection(
    request: FigureSelectionRequest,
    candidates: Iterable[CandidateExperimentGroup],
) -> ResolvedFigureSelection:
    """Resolve ARS group IDs against one current project inventory."""
    available = {group.group_id: group for group in candidates}
    selected = tuple(
        available[group_id]
        for group_id in request.selected_groups
        if group_id in available
    )
    reasons = list(request.reason_codes)
    if len(selected) != len(request.selected_groups):
        reasons.append("selected_group_unknown")
    if selected and len({group.technique for group in selected}) != 1:
        reasons.append("selected_groups_technique_mismatch")
    if selected and len({group.condition_kind for group in selected}) != 1:
        reasons.append("selected_groups_condition_kind_mismatch")
    codes = tuple(dict.fromkeys(reasons))
    payload = {
        "request": request.to_dict(),
        "groups": [group.to_dict() for group in selected],
    }
    selection_id = "selection-" + hashlib.sha256(
        canonical_json(payload).encode("utf-8")
    ).hexdigest()[:24]
    return ResolvedFigureSelection(
        selection_id=selection_id,
        status="blocked" if codes else "ready",
        request=request,
        groups=selected,
        reason_codes=codes,
    )


__all__ = ["FigureSelectionRequest", "ResolvedFigureSelection", "resolve_figure_selection"]
