"""Publication-quality auditing for manifest-backed figure assets."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from polynexus.plotting.figure_audit import audit_figure_sci

from .render_plan import FigureRenderPlan
from .renderer import MatplotlibFigureRenderer


@dataclass(frozen=True)
class FigurePublicationAuditResult:
    passed: bool
    issues: tuple[dict[str, str], ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "issues",
            tuple(
                {str(key): str(value) for key, value in issue.items()}
                for issue in self.issues
            ),
        )


class FigurePublicationAuditService:
    """Render one plan and report actionable publication issue codes."""

    def __init__(self, *, renderer: MatplotlibFigureRenderer | None = None) -> None:
        self._renderer = renderer or MatplotlibFigureRenderer()

    def audit(
        self,
        *,
        plan: FigureRenderPlan,
        assets: dict[str, Path],
    ) -> FigurePublicationAuditResult:
        figure = self._renderer.render(plan, dpi=150)
        try:
            report = audit_figure_sci(
                figure,
                exported_paths=tuple(assets.values()),
                expected_panel_count=len(plan.panels),
            )
            return FigurePublicationAuditResult(
                passed=report.passed,
                issues=tuple(
                    {
                        str(key): str(value)
                        for key, value in asdict(issue).items()
                    }
                    for issue in report.issues
                ),
            )
        finally:
            figure.clear()
