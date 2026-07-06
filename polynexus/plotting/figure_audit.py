"""Automated SCI figure checklist auditing.

The audit is intentionally conservative: it catches submission risks that can
be inspected from a Matplotlib figure object and the exported file list, while
leaving visual judgement calls for the manual review step.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Iterable, Sequence

import matplotlib as mpl
from matplotlib.colors import to_hex

from .sci_style import AXIS_LABELS, GRAYSCALE_PALETTE, WONG_COLORS


_CJK_RE = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")
_PANEL_LABEL_RE = re.compile(r"^\([a-z]\)(?:\s|$)", re.IGNORECASE)


@dataclass(frozen=True)
class FigureAuditIssue:
    """One actionable SCI figure checklist issue."""

    code: str
    message: str
    severity: str = "error"
    detail: str = ""


@dataclass
class FigureAuditReport:
    """Result of an SCI figure checklist audit."""

    issues: list[FigureAuditIssue] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    def issue_summary(self) -> str:
        if not self.issues:
            return "No SCI figure checklist issues found."
        return "; ".join(
            f"{issue.code}: {issue.message}" for issue in self.issues
        )


def audit_figure_sci(
    fig: mpl.figure.Figure,
    exported_paths: Sequence[str | Path] | None = None,
    *,
    expected_panel_count: int | None = None,
    min_font_size_pt: float = 8.0,
    min_line_width_pt: float = 0.8,
    allowed_line_colors: Iterable[str] | None = None,
    standard_axis_labels: Iterable[str] | None = None,
) -> FigureAuditReport:
    """Audit a Matplotlib figure against the PolyNexus SCI checklist.

    Parameters
    ----------
    fig:
        Figure to inspect.
    exported_paths:
        Paths produced for this figure. A publication-ready bundle should have
        one vector PDF and one raster PNG/TIFF/TIF.
    expected_panel_count:
        Required number of ``(a)``, ``(b)``, ... labels. Omit for single-panel
        quick checks where panel labels are not required.
    min_font_size_pt:
        Minimum readable font size in points.
    min_line_width_pt:
        Minimum visible line width in points.
    allowed_line_colors:
        Accepted line colors. Defaults to Wong + grayscale palettes.
    standard_axis_labels:
        Accepted axis label strings. Defaults to ``AXIS_LABELS.values()``.
    """
    report = FigureAuditReport()
    allowed_colors = _normalise_colors(
        allowed_line_colors or [*WONG_COLORS, *GRAYSCALE_PALETTE]
    )
    standard_labels = set(standard_axis_labels or AXIS_LABELS.values())

    _audit_titles(fig, report)
    _audit_text_language(fig, report)
    _audit_text_sizes(fig, report, min_font_size_pt)
    _audit_export_formats(exported_paths or [], report)
    _audit_panel_labels(fig, report, expected_panel_count)

    for ax in fig.axes:
        _audit_axis_labels(ax, report, standard_labels)
        _audit_line_styles(ax, report, allowed_colors, min_line_width_pt)
        _audit_annotation_placement(ax, report)

    return report


def _add_once(
    report: FigureAuditReport,
    code: str,
    message: str,
    *,
    detail: str = "",
    severity: str = "error",
) -> None:
    if any(issue.code == code for issue in report.issues):
        return
    report.issues.append(
        FigureAuditIssue(code=code, message=message, severity=severity, detail=detail)
    )


def _normalise_colors(colors: Iterable[str]) -> set[str]:
    normalised: set[str] = set()
    for color in colors:
        try:
            normalised.add(to_hex(color).lower())
        except ValueError:
            continue
    return normalised


def _audit_titles(fig: mpl.figure.Figure, report: FigureAuditReport) -> None:
    suptitle = getattr(fig, "_suptitle", None)
    if suptitle is not None and suptitle.get_text().strip():
        _add_once(
            report,
            "descriptive_title_present",
            "Figure-level title is present; manuscript titles belong in captions.",
        )

    for ax in fig.axes:
        titles = [
            ax.get_title(loc="left"),
            ax.get_title(loc="center"),
            ax.get_title(loc="right"),
        ]
        if any(title.strip() for title in titles):
            _add_once(
                report,
                "descriptive_title_present",
                "Axes title is present; SCI figures should keep titles in captions.",
            )
            return


def _audit_text_language(fig: mpl.figure.Figure, report: FigureAuditReport) -> None:
    for text in fig.findobj(match=mpl.text.Text):
        value = text.get_text()
        if value and _CJK_RE.search(value):
            _add_once(
                report,
                "non_english_text",
                "Figure contains Chinese/CJK text; submission figures should use English labels.",
                detail=value,
            )
            return


def _audit_text_sizes(
    fig: mpl.figure.Figure,
    report: FigureAuditReport,
    min_font_size_pt: float,
) -> None:
    for text in fig.findobj(match=mpl.text.Text):
        if not text.get_visible() or not text.get_text().strip():
            continue
        if float(text.get_fontsize()) < min_font_size_pt:
            _add_once(
                report,
                "font_size_below_8pt",
                f"Text font size is below {min_font_size_pt:g} pt.",
                detail=text.get_text(),
            )
            return


def _audit_export_formats(
    exported_paths: Sequence[str | Path],
    report: FigureAuditReport,
) -> None:
    suffixes = {Path(path).suffix.lower().lstrip(".") for path in exported_paths}
    has_vector = "pdf" in suffixes
    has_raster = bool({"png", "tif", "tiff"} & suffixes)
    if not (has_vector and has_raster):
        _add_once(
            report,
            "missing_required_export_format",
            "Expected PDF plus PNG/TIFF raster export for SCI submission.",
            detail=", ".join(sorted(suffixes)) or "no exports",
        )


def _audit_panel_labels(
    fig: mpl.figure.Figure,
    report: FigureAuditReport,
    expected_panel_count: int | None,
) -> None:
    if expected_panel_count is None:
        return

    found = 0
    for text in fig.findobj(match=mpl.text.Text):
        if _PANEL_LABEL_RE.match(text.get_text().strip()):
            found += 1

    if found < expected_panel_count:
        _add_once(
            report,
            "missing_panel_label",
            "Expected bold top-left panel labels like (a), (b), ...",
            detail=f"found {found}, expected {expected_panel_count}",
        )


def _audit_axis_labels(
    ax: mpl.axes.Axes,
    report: FigureAuditReport,
    standard_labels: set[str],
) -> None:
    labels = [ax.get_xlabel().strip(), ax.get_ylabel().strip()]
    if not all(labels):
        _add_once(
            report,
            "missing_axis_label",
            "All axes should have x and y labels.",
        )

    for label in labels:
        if label and label not in standard_labels:
            _add_once(
                report,
                "non_standard_axis_label",
                "Axis label does not match AXIS_LABELS standard names.",
                detail=label,
            )
            return


def _audit_line_styles(
    ax: mpl.axes.Axes,
    report: FigureAuditReport,
    allowed_colors: set[str],
    min_line_width_pt: float,
) -> None:
    for line in ax.get_lines():
        if not line.get_visible():
            continue

        try:
            color = to_hex(line.get_color()).lower()
        except ValueError:
            color = ""
        if color and color not in allowed_colors:
            _add_once(
                report,
                "non_wong_palette_color",
                "Line color is outside the configured Wong/grayscale palettes.",
                detail=color,
            )

        if float(line.get_linewidth()) < min_line_width_pt:
            _add_once(
                report,
                "line_width_below_0_8pt",
                f"Line width is below {min_line_width_pt:g} pt.",
                detail=str(line.get_linewidth()),
            )


def _audit_annotation_placement(
    ax: mpl.axes.Axes,
    report: FigureAuditReport,
) -> None:
    for text in ax.texts:
        value = text.get_text().strip()
        if not value or _PANEL_LABEL_RE.match(value):
            continue

        axes_position = _text_position_in_axes(ax, text)
        if axes_position is None:
            continue
        x, y = axes_position
        if 0.08 < x < 0.92 and 0.08 < y < 0.92:
            _add_once(
                report,
                "annotation_overlaps_data",
                "Free annotation text sits inside the central data area; review for overlap.",
                detail=value,
            )
            return


def _text_position_in_axes(
    ax: mpl.axes.Axes,
    text: mpl.text.Text,
) -> tuple[float, float] | None:
    try:
        display = text.get_transform().transform(text.get_position())
        x, y = ax.transAxes.inverted().transform(display)
        return float(x), float(y)
    except Exception:
        return None
