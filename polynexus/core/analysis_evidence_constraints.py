from __future__ import annotations

from typing import Any

from .analysis_evidence_action_hints import symptom_action_hints
from .analysis_evidence_constraint_inventory import (
    EvidenceConstraint,
    physical_constraint_inventory,
)


def summarize_constraints(constraints: list[dict[str, Any]] | None) -> dict[str, Any]:
    items = constraints if isinstance(constraints, list) else []
    inventory = {"hard_fail": 0, "soft_warn": 0, "evidence_only": 0}
    triggered_by_kind = {"hard_fail": [], "soft_warn": [], "evidence_only": []}

    for item in items:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind", "") or "").strip()
        if kind not in inventory:
            continue
        inventory[kind] += 1
        if item.get("triggered"):
            name = str(item.get("name", "") or "").strip()
            if name:
                triggered_by_kind[kind].append(name)

    status = "ok"
    if triggered_by_kind["hard_fail"]:
        status = "hard_fail"
    elif triggered_by_kind["soft_warn"]:
        status = "soft_warn"
    elif triggered_by_kind["evidence_only"]:
        status = "evidence_only"

    triggered_counts = {
        kind: len(names)
        for kind, names in triggered_by_kind.items()
    }

    return {
        "status": status,
        "inventory": inventory,
        "triggered_total": sum(triggered_counts.values()),
        "triggered_counts": triggered_counts,
        "triggered_names": triggered_by_kind,
    }

