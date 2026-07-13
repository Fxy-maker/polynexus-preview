from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QDialogButtonBox

from polynexus.gui.main_window import SideTuningReportDialog


def report_with(decision: str, confidence: str, simulated: str | None = None):
    return {
        "preprocess_decision": {
            "decision": decision,
            "simulated_decision": simulated or decision,
            "confidence_band": confidence,
            "reason_codes": ["noise_reduced"],
        },
        "selected_preprocess_config": {"smooth_window": 15},
        "preprocess_evidence": [
            {"candidate_id": "c1", "weak_peak_retention": 1.0, "peak_shift": 0.01}
        ],
    }


def test_confirm_dialog_enables_apply_and_uses_selected_config() -> None:
    app = QApplication.instance() or QApplication([])
    dialog = SideTuningReportDialog(report_with("request_confirmation", "medium"))

    assert dialog.best_config() == {"smooth_window": 15}
    assert dialog._buttons.button(QDialogButtonBox.Ok).isEnabled() is True
    assert "weak_peak_retention" in dialog._preprocess_metrics_label.text()

    dialog.deleteLater()
    app.processEvents()


def test_shadow_disables_apply_and_auto_accept_offers_undo() -> None:
    app = QApplication.instance() or QApplication([])
    shadow = SideTuningReportDialog(
        report_with("keep_original", "high", simulated="auto_accept")
    )
    auto = SideTuningReportDialog(report_with("auto_accept", "high"))

    assert shadow._buttons.button(QDialogButtonBox.Ok).isEnabled() is False
    assert "Undo" in auto._buttons.button(QDialogButtonBox.Ok).text()

    shadow.deleteLater()
    auto.deleteLater()
    app.processEvents()
