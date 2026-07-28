from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QSizePolicy

from polynexus.gui.main_window import MainWindow


def test_long_results_evidence_uses_available_viewport_without_changing_text():
    QApplication.instance() or QApplication([])
    window = MainWindow()
    risk_text = "Risk note | " + ("reason_code_without_spaces," * 32)
    next_text = "Next step | " + ("Review the diagnostic evidence before release; " * 24)
    try:
        window.resize(900, 700)
        window._set_results_summary("SAXS results", risk_text, next_text)
        window.show()
        QApplication.processEvents()

        risk_label = window._results_summary_risk_label
        next_label = window._results_summary_next_label
        assert risk_label.wordWrap()
        assert next_label.wordWrap()
        assert risk_label.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Ignored
        assert next_label.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Ignored
        assert risk_label.text() == risk_text
        assert next_label.text() == next_text
        assert window._results_summary_group.minimumSizeHint().width() < 1000
    finally:
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
