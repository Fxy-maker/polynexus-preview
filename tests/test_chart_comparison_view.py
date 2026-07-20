from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from polynexus.gui.widgets.chart_comparison_view import (
    ChartComparisonRequest,
    ChartComparisonView,
)


def test_chart_comparison_view_exposes_two_panels_and_revision_metadata(tmp_path):
    QApplication.instance() or QApplication([])
    left = tmp_path / "left.png"
    right = tmp_path / "right.png"
    left.write_bytes(b"not-an-image")
    right.write_bytes(b"not-an-image")
    request = ChartComparisonRequest(
        left_id="left",
        right_id="right",
        left_title="Working",
        right_title="Published",
        left_path=str(left),
        right_path=str(right),
        left_revision=3,
        right_revision=2,
    )

    view = ChartComparisonView(request)

    assert view._left_title.text() == "Working · r3"
    assert view._right_title.text() == "Published · r2"
    assert view._splitter.count() == 2
    view.deleteLater()
