from __future__ import annotations

from polynexus.gui.main_window import MainWindow
from polynexus.gui.main_window_history_mixin import MainWindowHistoryMixin


def test_main_window_reuses_history_and_persistence_helpers_from_history_mixin():
    assert MainWindow._history_context_snapshot is MainWindowHistoryMixin._history_context_snapshot
    assert MainWindow._history_context_lines is MainWindowHistoryMixin._history_context_lines
    assert MainWindow._history_result_origin_label is MainWindowHistoryMixin._history_result_origin_label
    assert MainWindow._result_to_jsonable is MainWindowHistoryMixin._result_to_jsonable
    assert MainWindow._history_submodule_text is MainWindowHistoryMixin._history_submodule_text
    assert MainWindow._history_technique_text is MainWindowHistoryMixin._history_technique_text
    assert MainWindow._persist_analysis_run is MainWindowHistoryMixin._persist_analysis_run
    assert MainWindow._build_history_panel is MainWindowHistoryMixin._build_history_panel


def test_history_text_includes_project_release_snapshot_when_present():
    window = object.__new__(MainWindowHistoryMixin)
    text = window._scientific_review_text(
        {
            "technique": "joint",
            "submodule": "joint.compare",
            "scientific_release": {
                "allowed": True,
                "reason": "review_accepted",
                "record_id": "release-history-1",
                "scope": "release",
                "source_ref": "joint-run",
            },
        }
    )

    assert "release-history-1" in text
    assert "review_accepted" in text
