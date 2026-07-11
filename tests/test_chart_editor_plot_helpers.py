from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

from matplotlib.figure import Figure

from polynexus.gui.chart_editor_plot_helpers import make_bar_plot, make_line_plot


def test_make_line_plot_adds_legend_and_returns_axis() -> None:
    fig = Figure()
    ax = fig.subplots()

    returned = make_line_plot(ax, [0, 1], [2, 3], label="Series", color="black")

    assert returned is ax
    assert ax.get_legend() is not None
    assert [line.get_label() for line in ax.lines] == ["Series"]


def test_make_bar_plot_uses_default_palette_and_returns_axis() -> None:
    fig = Figure()
    ax = fig.subplots()

    returned = make_bar_plot(ax, ["A", "B", "C"], [1, 2, 3])

    assert returned is ax
    assert [tick.get_text() for tick in ax.get_xticklabels()] == ["A", "B", "C"]
    assert len(ax.patches) == 3


def test_chart_editor_reexports_plot_helpers() -> None:
    from polynexus.gui.widgets import chart_editor

    assert chart_editor.make_line_plot is make_line_plot
    assert chart_editor.make_bar_plot is make_bar_plot
