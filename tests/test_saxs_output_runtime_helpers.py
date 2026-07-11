from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

from matplotlib import pyplot as plt

from polynexus.core.saxs_engine.saxs_output_runtime_helpers import (
    _downsample_plot,
    _make_output_dirs,
    _safe_legend,
)


def test_downsample_plot_keeps_endpoints() -> None:
    x = list(range(10))
    y = [value * 2 for value in x]

    x_small, y_small = _downsample_plot(x, y, max_pts=4)

    assert len(x_small) == len(y_small) == 4
    assert x_small[0] == 0
    assert x_small[-1] == 9


def test_safe_legend_ignores_private_labels() -> None:
    fig, ax = plt.subplots()
    ax.plot([0, 1], [1, 2], label="_hidden")

    assert _safe_legend(ax) is None

    ax.plot([0, 1], [2, 3], label="Visible")
    legend = _safe_legend(ax)

    assert legend is not None
    assert [text.get_text() for text in legend.get_texts()] == ["Visible"]
    plt.close(fig)


def test_make_output_dirs_creates_expected_layout(tmp_path) -> None:
    root = _make_output_dirs(str(tmp_path / "exports"))

    assert (root / "summary").is_dir()
    assert (root / "figures" / "SI").is_dir()
    assert (root / "data" / "parameters").is_dir()
    assert (root / "data" / "raw_1d").is_dir()
    assert (root / "data" / "fit_results").is_dir()
    assert (root / "report").is_dir()
