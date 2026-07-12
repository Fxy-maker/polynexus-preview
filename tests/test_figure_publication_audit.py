from dataclasses import replace

import pytest
from matplotlib.figure import Figure

from polynexus.core.figures.publication_audit import (
    FigurePublicationAuditResult,
    FigurePublicationAuditService,
)
from polynexus.plotting import AXIS_LABELS, WONG_COLORS


def test_publication_audit_reports_structured_issues(render_plan, tmp_path):
    result = FigurePublicationAuditService().audit(
        plan=render_plan,
        assets={
            "pdf": tmp_path / "figure.pdf",
            "tiff": tmp_path / "figure.tiff",
        },
    )

    assert result.passed is False
    issues_by_code = {issue["code"]: issue for issue in result.issues}
    assert set(issues_by_code["missing_panel_label"]) == {
        "code",
        "message",
        "severity",
        "detail",
    }
    assert issues_by_code["missing_panel_label"]["message"]
    assert issues_by_code["missing_panel_label"]["severity"] == "error"
    assert issues_by_code["missing_panel_label"]["detail"]
    assert "non_standard_axis_label" in issues_by_code


def test_publication_audit_accepts_compliant_render_plan(render_plan, tmp_path):
    panel = replace(
        render_plan.panels[0],
        x_axis=replace(
            render_plan.panels[0].x_axis,
            label=AXIS_LABELS["wavenumber"],
            unit="",
        ),
        y_axis=replace(
            render_plan.panels[0].y_axis,
            label=AXIS_LABELS["absorbance"],
            unit="",
        ),
        panel_label="(a)",
    )
    figure_object = {
        **render_plan.objects[0],
        "style": {
            **render_plan.objects[0]["style"],
            "color": WONG_COLORS[0],
        },
    }
    compliant_plan = replace(
        render_plan,
        panels=(panel,),
        objects=(figure_object,),
    )

    result = FigurePublicationAuditService().audit(
        plan=compliant_plan,
        assets={
            "pdf": tmp_path / "figure.pdf",
            "tiff": tmp_path / "figure.tiff",
        },
    )

    assert result.passed is True
    assert result.issues == ()


def test_publication_audit_clears_figure_when_audit_raises(
    render_plan,
    tmp_path,
    monkeypatch,
):
    figure = Figure()
    figure.add_subplot(111)

    class _Renderer:
        def render(self, _plan, *, dpi):
            assert dpi > 0
            return figure

    def _raise(*_args, **_kwargs):
        raise RuntimeError("audit failed")

    monkeypatch.setattr(
        "polynexus.core.figures.publication_audit.audit_figure_sci",
        _raise,
    )

    with pytest.raises(RuntimeError, match="audit failed"):
        FigurePublicationAuditService(renderer=_Renderer()).audit(
            plan=render_plan,
            assets={"pdf": tmp_path / "figure.pdf"},
        )

    assert figure.axes == []


def test_publication_audit_result_copies_and_normalises_issue_payloads():
    issue = {
        "code": "missing_panel_label",
        "message": "Expected panel labels.",
        "severity": "error",
        "detail": "found 0, expected 1",
    }

    result = FigurePublicationAuditResult(passed=False, issues=(issue,))
    issue["message"] = "mutated"

    assert result.issues[0]["message"] == "Expected panel labels."
