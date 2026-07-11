"""Pure Matplotlib helpers used by the chart editor."""

from __future__ import annotations


def make_line_plot(ax, x, y, title="", xlabel="X", ylabel="Y", label="Data", **kw):
    ax.plot(x, y, label=label, **kw)
    ax.legend()
    return ax


def make_bar_plot(ax, labels, values, title="", ylabel="Value", colors=None, **kw):
    if colors is None:
        colors = ["#2166AC", "#B2182B", "#1B7837", "#E69F00", "#762A83"]
    ax.bar(
        range(len(labels)),
        values,
        color=colors[: len(labels)],
        edgecolor="white",
        linewidth=0.5,
    )
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=30, ha="right")
    return ax
