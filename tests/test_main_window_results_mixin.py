from __future__ import annotations

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QTabWidget, QWidget

from polynexus.gui.main_window import MainWindow
from polynexus.gui.main_window_results_mixin import MainWindowResultsMixin
from polynexus.gui.main_window_workspace_mixin import MainWindowWorkspaceMixin
from polynexus.gui.theme import DARK_TOKENS, LIGHT_TOKENS, ThemeEngine
from polynexus.gui.workspace_context import WorkspaceContext, WorkspaceResultStatus


class _FakeResultsWindow(MainWindowResultsMixin):
    def __init__(self) -> None:
        self._results_compare_selected_run_id = "  run-42  "
        self._confirmed = False

    def _current_results_record(self) -> dict:
        return {"id": "current", "confirmed": self._confirmed, "results_summary": {}}

    def _is_current_result_confirmed(self) -> bool:
        return self._confirmed


def test_results_compare_selected_candidate_id_trims_whitespace() -> None:
    window = _FakeResultsWindow()

    assert window._results_compare_selected_candidate_id() == "run-42"


def test_results_confirm_state_text_reflects_confirmation_state() -> None:
    window = _FakeResultsWindow()

    assert window._results_confirm_state_text()

    window._confirmed = True

    assert window._results_confirm_state_text() != ""


def test_main_window_reuses_result_context_helpers_from_results_mixin() -> None:
    assert MainWindow._current_results_payload is MainWindowResultsMixin._current_results_payload
    assert MainWindow._current_results_record is MainWindowResultsMixin._current_results_record
    assert MainWindow._current_result_history_context is MainWindowResultsMixin._current_result_history_context
    assert MainWindow._current_result_tuning_context is MainWindowResultsMixin._current_result_tuning_context
    assert MainWindow._current_analysis_evidence is MainWindowResultsMixin._current_analysis_evidence
    assert MainWindow._current_result_origin is MainWindowResultsMixin._current_result_origin
    assert MainWindow._current_result_origin_label is MainWindowResultsMixin._current_result_origin_label
    assert MainWindow._result_origin_label is MainWindowResultsMixin._result_origin_label
    assert MainWindow._build_results_tab is MainWindowResultsMixin._build_results_tab
    assert MainWindow._build_joint_metric_label is MainWindowResultsMixin._build_joint_metric_label


def test_main_tab_route_does_not_apply_full_page_opacity_effect() -> None:
    QApplication.instance() or QApplication([])

    class _FakeTabWindow:
        def __init__(self) -> None:
            self._tabs = QTabWidget()
            self._tabs.addTab(QWidget(), "Results")
            self.context_updates = 0

        def _update_context_suggestions(self) -> None:
            self.context_updates += 1

    window = _FakeTabWindow()

    MainWindow._on_tab_changed(window, 0)

    assert window._tabs.widget(0).graphicsEffect() is None
    assert window.context_updates == 1


def test_results_text_uses_active_light_theme_tokens() -> None:
    QApplication.instance() or QApplication([])
    theme = ThemeEngine.instance()
    previous_theme = theme.current
    theme.switch("light")
    window = MainWindow()
    try:
        assert LIGHT_TOKENS.text_primary in window._results_summary_label.styleSheet()
        assert LIGHT_TOKENS.text_muted in window._results_summary_risk_label.styleSheet()
        assert LIGHT_TOKENS.text_primary in window._results_review_title.styleSheet()
        theme.switch("dark")
        assert DARK_TOKENS.text_primary in window._results_summary_label.styleSheet()
        assert DARK_TOKENS.text_muted in window._results_summary_risk_label.styleSheet()
    finally:
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        theme.switch(previous_theme)


def test_light_theme_muted_text_meets_body_contrast() -> None:
    def relative_luminance(value: str) -> float:
        channels = [int(value[index : index + 2], 16) / 255.0 for index in (1, 3, 5)]
        linear = [
            channel / 12.92
            if channel <= 0.04045
            else ((channel + 0.055) / 1.055) ** 2.4
            for channel in channels
        ]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    background = relative_luminance(LIGHT_TOKENS.bg_deep)
    muted = relative_luminance(LIGHT_TOKENS.text_muted)
    lighter, darker = max(background, muted), min(background, muted)

    assert (lighter + 0.05) / (darker + 0.05) >= 4.5


class _StaleResultsWindow(MainWindowResultsMixin, MainWindowWorkspaceMixin):
    def __init__(self) -> None:
        self._current_technique = "waxs"
        self._results = {"waxs": {"parameters": {"r2": 0.9}}}
        self._result_contexts = {
            "waxs": WorkspaceContext(
                technique="saxs",
                source_path="D:/old/sample.edf",
                run_id="run-old",
                result_status=WorkspaceResultStatus.COMPLETE,
            )
        }
        self._workspace_context = WorkspaceContext(
            technique="waxs",
            source_path="D:/new/sample.edf",
            result_status=WorkspaceResultStatus.EMPTY,
        )
        self._results_context_banner = type("Banner", (), {
            "setVisible": lambda self, value: setattr(self, "visible", value),
            "setText": lambda self, value: setattr(self, "text", value),
        })()


def test_stale_result_context_is_not_projected_as_current_payload() -> None:
    window = _StaleResultsWindow()

    assert window._current_results_payload() == {}
    assert window._results_context_banner.visible is True
