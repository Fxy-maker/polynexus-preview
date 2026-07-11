from __future__ import annotations

from polynexus.gui.main_window import MainWindow


def test_main_window_reuses_joint_diagnostics_and_artifact_helpers_from_joint_diagnostics_mixin() -> None:
    from polynexus.gui.main_window_joint_diagnostics_mixin import (
        MainWindowJointDiagnosticsMixin,
    )

    assert (
        MainWindow._update_joint_diagnostics
        is MainWindowJointDiagnosticsMixin._update_joint_diagnostics
    )
    assert (
        MainWindow._hide_joint_diagnostics
        is MainWindowJointDiagnosticsMixin._hide_joint_diagnostics
    )
    assert (
        MainWindow._save_joint_hub_artifacts
        is MainWindowJointDiagnosticsMixin._save_joint_hub_artifacts
    )
