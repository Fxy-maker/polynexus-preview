from __future__ import annotations

import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QTextEdit

from polynexus.gui.main_window import MainWindow
from polynexus.gui.main_window_run_mixin import MainWindowRunMixin
from polynexus.gui.run_state_service import RunState


def test_main_window_reuses_run_workflow_helpers_from_run_mixin():
    assert MainWindow._run_analysis is MainWindowRunMixin._run_analysis
    assert MainWindow._run_joint_hub is MainWindowRunMixin._run_joint_hub
    assert MainWindow._on_joint_hub_finished is MainWindowRunMixin._on_joint_hub_finished
    assert MainWindow._run_single is MainWindowRunMixin._run_single
    assert MainWindow._run_batch is MainWindowRunMixin._run_batch
    assert MainWindow._replot is MainWindowRunMixin._replot
    assert MainWindow._on_replot_finished is MainWindowRunMixin._on_replot_finished
    assert MainWindow._transition_run_state is MainWindowRunMixin._transition_run_state
    assert MainWindow._copy_error_diagnostics is MainWindowRunMixin._copy_error_diagnostics
    assert MainWindow._log_analysis_diagnostics is MainWindowRunMixin._log_analysis_diagnostics
    assert MainWindow._log_run_completion_summary is MainWindowRunMixin._log_run_completion_summary
    assert MainWindow._on_finished is MainWindowRunMixin._on_finished
    assert MainWindow._on_joint_hub_error is MainWindowRunMixin._on_joint_hub_error
    assert MainWindow._on_error is MainWindowRunMixin._on_error
    assert MainWindow._on_batch_file_done is MainWindowRunMixin._on_batch_file_done
    assert MainWindow._on_batch_finished is MainWindowRunMixin._on_batch_finished


def test_log_copy_action_copies_complete_plain_text_log():
    app = QApplication.instance() or QApplication([])

    class Harness:
        def __init__(self):
            self._log_panel = QTextEdit()
            self.logged = []

        def _main_window_module(self):
            return SimpleNamespace(QApplication=QApplication)

        def log(self, message):
            self.logged.append(message)

    harness = Harness()
    harness._log_panel.setPlainText("Traceback line 1\nAttributeError: boom")

    assert MainWindowRunMixin._copy_log_to_clipboard(harness) is True
    assert QApplication.clipboard().text() == harness._log_panel.toPlainText()
    assert harness.logged

    app.processEvents()


def test_run_error_diagnostics_can_be_copied_without_copying_ui_status_text():
    app = QApplication.instance() or QApplication([])

    class Harness:
        def __init__(self):
            self.logged = []

        def _main_window_module(self):
            return SimpleNamespace(QApplication=QApplication)

        def log(self, message):
            self.logged.append(message)

    harness = Harness()
    MainWindowRunMixin._record_error_diagnostic(harness, "bad input\ntraceback line")

    assert MainWindowRunMixin._copy_error_diagnostics(harness) is True
    assert QApplication.clipboard().text().startswith("analysis: bad input")
    assert "traceback line" in QApplication.clipboard().text()
    assert harness.logged

    app.processEvents()


class _StaleWorkerHarness(MainWindowRunMixin):
    def __init__(self):
        self._run_request_token = 2
        self._results = {}
        self._batch_results = []
        self._run_state = RunState()
        self._current_technique = "saxs"


def test_stale_single_worker_completion_does_not_publish_after_quick_switch():
    harness = _StaleWorkerHarness()

    harness._on_finished({"parameters": {"r2": 0.99}}, token=1)

    assert harness._results == {}


def test_stale_batch_worker_completion_does_not_publish_after_quick_switch():
    harness = _StaleWorkerHarness()

    harness._on_batch_finished([{"file": "old.csv", "params": {"r2": 0.99}}], token=1)

    assert harness._batch_results == []
