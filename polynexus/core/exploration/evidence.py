"""Curated projection from exploration history into shared evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from polynexus.core.ai_platform.contracts import canonical_json_hash
from polynexus.core.project_workflow.models import EvidenceItem

from .contracts import ExplorationRun


def _lookup(metrics: Mapping[str, Any], path: str) -> tuple[bool, Any]:
    if path in metrics:
        return True, metrics[path]
    parts = path.split(".")
    current: Any = metrics
    index = 0
    while index < len(parts):
        if not isinstance(current, Mapping):
            return False, None
        for end in range(len(parts), index, -1):
            key = ".".join(parts[index:end])
            if key in current:
                current = current[key]
                index = end
                break
        else:
            return False, None
    return True, current


@dataclass(frozen=True)
class ExplorationEvidenceSelection:
    """Explicit metric-level selection made by Codex or a user."""

    metric_paths: tuple[str, ...]
    claim_scope: str
    selector: str = "codex"
    selection_hash: str = ""

    def __post_init__(self) -> None:
        if isinstance(self.metric_paths, (str, bytes, bytearray)):
            raise TypeError("metric_paths must be a sequence")
        paths = tuple(dict.fromkeys(str(path).strip() for path in self.metric_paths))
        if not paths or any(not path for path in paths):
            raise ValueError("metric_paths must contain at least one nonempty path")
        object.__setattr__(self, "metric_paths", paths)
        claim_scope = str(self.claim_scope).strip()
        selector = str(self.selector).strip()
        if not claim_scope or not selector:
            raise ValueError("claim_scope and selector must be nonempty")
        object.__setattr__(self, "claim_scope", claim_scope)
        object.__setattr__(self, "selector", selector)
        expected = canonical_json_hash(self._identity_payload())
        if self.selection_hash and self.selection_hash != expected:
            raise ValueError("evidence selection hash does not match its content")
        object.__setattr__(self, "selection_hash", expected)

    @classmethod
    def create(
        cls,
        *,
        metric_paths: Sequence[str],
        claim_scope: str,
        selector: str = "codex",
    ) -> "ExplorationEvidenceSelection":
        return cls(tuple(metric_paths), claim_scope, selector)

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "metric_paths": list(self.metric_paths),
            "claim_scope": self.claim_scope,
            "selector": self.selector,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._identity_payload(), "selection_hash": self.selection_hash}

    def project(self, run: ExplorationRun) -> EvidenceItem:
        if type(run) is not ExplorationRun or run.status != "completed" or run.provider_result is None:
            raise ValueError("only completed exploration runs can be curated")
        rows = {str(row.get("path")): row for row in run.provider_result.metric_manifest}
        selected_rows: list[Mapping[str, Any]] = []
        selected_metrics: dict[str, Any] = {}
        for path in self.metric_paths:
            row = rows.get(path)
            if row is None or row.get("status") != "computed":
                raise ValueError(f"selected metric is not computed: {path}")
            present, value = _lookup(run.provider_result.metrics, path)
            if not present or value is None:
                raise ValueError(f"selected metric value is missing: {path}")
            selected_rows.append(dict(row))
            selected_metrics[path] = value
        return EvidenceItem.create(
            evidence_id=f"{run.run_id}:exploration:{self.selection_hash}",
            kind="exploration_result",
            technique=run.request.technique,
            claim_scope=self.claim_scope,
            observed_results={
                "exploration_run": {
                    "run_id": run.run_id,
                    "run_hash": run.run_hash,
                    "request_id": run.request.request_id,
                },
                "selected_metrics": selected_metrics,
                "metric_manifest": selected_rows,
                "selection": self.to_dict(),
                "curated_projection_only": True,
            },
            source_runs=(run.run_id,),
            raw_sources=(run.request.source_artifact_id,),
            status="review_required",
            limitations=("exploration_method_requires_review", "curated_projection_only"),
        )


__all__ = ["ExplorationEvidenceSelection"]
