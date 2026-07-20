"""Previewed, validated batch editing for persisted figure documents."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping

from .figure_template_service import apply_template


@dataclass(frozen=True)
class BatchEditTarget:
    target_id: str
    document_path: Any
    before: dict[str, Any]
    after: dict[str, Any]
    changed_fields: tuple[str, ...] = ()
    error: str = ""


@dataclass(frozen=True)
class BatchEditPlan:
    targets: tuple[BatchEditTarget, ...]

    @property
    def valid(self) -> bool:
        return bool(self.targets) and all(not target.error for target in self.targets)


def _changed_fields(before: dict[str, Any], after: dict[str, Any]) -> tuple[str, ...]:
    return tuple(
        key
        for key in ("canvas", "style", "objects")
        if before.get(key) != after.get(key)
    )


def build_batch_edit_plan(
    entries: Iterable[Mapping[str, Any]],
    template: Mapping[str, Any],
) -> BatchEditPlan:
    targets = []
    for entry in entries:
        target_id = str(entry.get("id", "") or "")
        path = entry.get("document_path", "")
        document = entry.get("document")
        if not isinstance(document, dict):
            targets.append(
                BatchEditTarget(
                    target_id=target_id,
                    document_path=path,
                    before={},
                    after={},
                    error=f"{target_id}: document is unavailable",
                )
            )
            continue
        try:
            after = apply_template(document, dict(template))
        except (TypeError, ValueError) as exc:
            targets.append(
                BatchEditTarget(
                    target_id=target_id,
                    document_path=path,
                    before=deepcopy(document),
                    after={},
                    error=f"{target_id}: {exc}",
                )
            )
            continue
        targets.append(
            BatchEditTarget(
                target_id=target_id,
                document_path=path,
                before=deepcopy(document),
                after=deepcopy(after),
                changed_fields=_changed_fields(document, after),
            )
        )
    return BatchEditPlan(tuple(targets))


def apply_batch_edit_plan(
    plan: BatchEditPlan,
    save_document: Callable[[Any, dict[str, Any]], object],
) -> tuple[str, ...]:
    if not plan.valid:
        error = next((target.error for target in plan.targets if target.error), "Batch edit plan is invalid.")
        raise ValueError(error)
    written: list[BatchEditTarget] = []
    try:
        for target in plan.targets:
            save_document(target.document_path, deepcopy(target.after))
            written.append(target)
    except Exception:
        for target in reversed(written):
            try:
                save_document(target.document_path, deepcopy(target.before))
            except Exception:
                pass
        raise
    return tuple(target.target_id for target in written)


__all__ = [
    "BatchEditPlan",
    "BatchEditTarget",
    "apply_batch_edit_plan",
    "build_batch_edit_plan",
]
