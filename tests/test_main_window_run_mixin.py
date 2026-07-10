from __future__ import annotations

from polynexus.gui.main_window import MainWindow
from polynexus.gui.main_window_run_mixin import MainWindowRunMixin


def test_main_window_reuses_run_workflow_helpers_from_run_mixin():
    assert MainWindow._run_analysis is MainWindowRunMixin._run_analysis
    assert MainWindow._run_joint_hub is MainWindowRunMixin._run_joint_hub
    assert MainWindow._on_joint_hub_finished is MainWindowRunMixin._on_joint_hub_finished
    assert MainWindow._run_single is MainWindowRunMixin._run_single
    assert MainWindow._run_batch is MainWindowRunMixin._run_batch
    assert MainWindow._replot is MainWindowRunMixin._replot
    assert MainWindow._on_replot_finished is MainWindowRunMixin._on_replot_finished
    assert MainWindow._log_analysis_diagnostics is MainWindowRunMixin._log_analysis_diagnostics
    assert MainWindow._log_run_completion_summary is MainWindowRunMixin._log_run_completion_summary
    assert MainWindow._on_finished is MainWindowRunMixin._on_finished
    assert MainWindow._on_joint_hub_error is MainWindowRunMixin._on_joint_hub_error
    assert MainWindow._on_error is MainWindowRunMixin._on_error
    assert MainWindow._on_batch_file_done is MainWindowRunMixin._on_batch_file_done
    assert MainWindow._on_batch_finished is MainWindowRunMixin._on_batch_finished
