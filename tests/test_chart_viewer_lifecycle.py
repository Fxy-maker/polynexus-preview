from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QApplication

from polynexus.gui.widgets.chart_viewer import FigureFilePreview


def test_figure_preview_does_not_run_deferred_fit_after_widget_deletion(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "preview.png"
    pixmap = QPixmap(48, 32)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    preview = FigureFilePreview(show_edit_button=False)
    preview.load_figure(str(image_path))
    preview.deleteLater()

    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()
