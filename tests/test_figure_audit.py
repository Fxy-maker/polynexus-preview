from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt

from polynexus.plotting import (
    AXIS_LABELS,
    WONG_COLORS,
    apply_panel_label,
    audit_figure_sci,
    set_sci_style,
)


@mpl.rc_context()
def test_sci_figure_audit_accepts_publication_ready_figure(tmp_path) -> None:
    set_sci_style()
    fig, axes = plt.subplots(1, 2, figsize=(6.89, 2.56))

    for idx, ax in enumerate(axes):
        ax.plot(
            [0.0, 1.0, 2.0],
            [idx, idx + 1.0, idx + 2.0],
            color=WONG_COLORS[idx],
            linewidth=1.2,
        )
        ax.set_xlabel(AXIS_LABELS["q"])
        ax.set_ylabel(AXIS_LABELS["I_saxs"])
        apply_panel_label(ax, f"({chr(ord('a') + idx)})")

    report = audit_figure_sci(
        fig,
        exported_paths=[tmp_path / "figure.pdf", tmp_path / "figure.png"],
        expected_panel_count=2,
    )

    assert report.passed, report.issue_summary()

    plt.close(fig)


@mpl.rc_context()
def test_sci_figure_audit_reports_submission_checklist_violations(tmp_path) -> None:
    set_sci_style()
    fig, ax = plt.subplots(figsize=(3.35, 2.56))
    ax.plot([0.0, 1.0], [0.0, 1.0], color="#ff0000", linewidth=0.4)
    ax.set_title("\u7ed3\u679c\u56fe")
    ax.set_xlabel("custom q")
    ax.text(0.5, 0.5, "overlap", transform=ax.transAxes, fontsize=7)

    report = audit_figure_sci(
        fig,
        exported_paths=[tmp_path / "figure.svg"],
        expected_panel_count=1,
    )

    issue_codes = {issue.code for issue in report.issues}
    assert "descriptive_title_present" in issue_codes
    assert "non_english_text" in issue_codes
    assert "non_wong_palette_color" in issue_codes
    assert "font_size_below_8pt" in issue_codes
    assert "missing_required_export_format" in issue_codes
    assert "missing_panel_label" in issue_codes
    assert "line_width_below_0_8pt" in issue_codes
    assert "missing_axis_label" in issue_codes
    assert "non_standard_axis_label" in issue_codes
    assert "annotation_overlaps_data" in issue_codes

    plt.close(fig)
