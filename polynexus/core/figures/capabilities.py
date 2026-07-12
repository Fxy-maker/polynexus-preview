"""Independent editing and publication capability resolution."""

from __future__ import annotations

from dataclasses import dataclass

from .inspector import FigureArtifactInspection
from .publication_audit import FigurePublicationAuditResult
from .render_plan import FigureRenderPlan


_OBJECT_EDITABLE_TYPES = frozenset({"plot_series", "heatmap", "line", "text"})


@dataclass(frozen=True)
class FigureCapabilityReport:
    editing_mode: str
    object_editing: bool
    static_annotation: bool
    reason_code: str
    publication_status: str
    audit_passed: bool = True
    audit_issues: tuple[dict[str, str], ...] = ()

    def to_payload(self) -> dict[str, object]:
        return {
            "editing_mode": self.editing_mode,
            "object_editing": self.object_editing,
            "static_annotation": self.static_annotation,
            "reason_code": self.reason_code,
            "publication_status": self.publication_status,
            "audit_passed": self.audit_passed,
            "audit_issues": [dict(issue) for issue in self.audit_issues],
        }


def resolve_figure_capabilities(
    *,
    plan: FigureRenderPlan,
    inspection: FigureArtifactInspection,
    audit: FigurePublicationAuditResult | None = None,
    working_revision: int,
    published_revision: int,
) -> FigureCapabilityReport:
    audit_result = audit or FigurePublicationAuditResult(passed=True, issues=())
    object_types = {
        str(figure_object.get("type") or "") for figure_object in plan.objects
    }
    if not plan.panels:
        object_editing = False
        reason_code = "missing_panels"
    elif not object_types.issubset(_OBJECT_EDITABLE_TYPES):
        object_editing = False
        reason_code = "unsupported_object_types"
    else:
        object_editing = True
        reason_code = ""

    return FigureCapabilityReport(
        editing_mode="object" if object_editing else "static",
        object_editing=object_editing,
        static_annotation=True,
        reason_code=reason_code,
        publication_status=_publication_status(
            inspection,
            audit_result,
            working_revision=working_revision,
            published_revision=published_revision,
        ),
        audit_passed=audit_result.passed,
        audit_issues=tuple(dict(issue) for issue in audit_result.issues),
    )


def _publication_status(
    inspection: FigureArtifactInspection,
    audit: FigurePublicationAuditResult,
    working_revision: int,
    published_revision: int,
) -> str:
    if published_revision <= 0:
        return "not_published"
    if not inspection.complete:
        return "needs_repair"
    if not audit.passed:
        return "quality_failed"
    if working_revision > published_revision:
        return "unpublished_changes"
    return "complete"
