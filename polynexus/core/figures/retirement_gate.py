"""Machine-checkable gate for retiring duplicate legacy figure runtime paths."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class LegacyRetirementGate:
    eligible: bool
    blockers: tuple[str, ...]


def evaluate_legacy_retirement(
    inventory: Mapping[str, str],
    human_review: Mapping[str, bool],
) -> LegacyRetirementGate:
    """Allow retirement only for approved V2-default or explicit static routes."""

    blockers: list[str] = []
    for route, status in inventory.items():
        if status not in {"v2_default", "static_compat"}:
            blockers.append(f"route_not_ready:{route}:{status}")
        if not bool(human_review.get(route, False)):
            blockers.append(f"review_pending:{route}")
    return LegacyRetirementGate(not blockers, tuple(blockers))
