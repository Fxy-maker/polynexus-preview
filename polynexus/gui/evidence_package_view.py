"""GUI adapter for the technique-neutral evidence package DTO."""

from __future__ import annotations

from polynexus.core.project_workflow.evidence_view import EvidencePackageView


class EvidencePackageViewAdapter:
    """Expose compact presentation data without provider-specific branching."""

    def __init__(self, view: EvidencePackageView) -> None:
        self.view = view

    def summary(self) -> dict[str, object]:
        return {
            "status": self.view.status,
            "techniques": tuple(item.key for item in self.view.techniques),
            "metric_count": len(self.view.metrics),
            "human_review_count": len(self.view.human_review),
        }

    def techniques(self):
        return self.view.techniques

    def evidence(self):
        return self.view.evidence

    def metrics(self):
        return self.view.metrics

    def human_review(self):
        return self.view.human_review


__all__ = ["EvidencePackageViewAdapter"]
