from __future__ import annotations

from polynexus.gui.main_window import MainWindow


def test_main_window_reuses_guidance_panel_builders_from_guidance_mixin() -> None:
    from polynexus.gui.main_window_guidance_panels_mixin import MainWindowGuidancePanelsMixin

    assert MainWindow._build_context_suggestion_panel is MainWindowGuidancePanelsMixin._build_context_suggestion_panel
    assert MainWindow._build_work_memory_panel is MainWindowGuidancePanelsMixin._build_work_memory_panel
    assert MainWindow._invoke_context_suggestion_action is MainWindowGuidancePanelsMixin._invoke_context_suggestion_action
    assert MainWindow._invoke_work_memory_action is MainWindowGuidancePanelsMixin._invoke_work_memory_action
