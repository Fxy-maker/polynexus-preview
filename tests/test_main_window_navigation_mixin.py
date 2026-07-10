from __future__ import annotations

from polynexus.gui.main_window import MainWindow


def test_main_window_reuses_navigation_and_mode_selection_helpers_from_navigation_mixin() -> None:
    from polynexus.gui.main_window_navigation_mixin import MainWindowNavigationMixin

    assert MainWindow._set_nav_visual_state is MainWindowNavigationMixin._set_nav_visual_state
    assert MainWindow._refresh_sidebar_texts is MainWindowNavigationMixin._refresh_sidebar_texts
    assert MainWindow._jump_to_tab is MainWindowNavigationMixin._jump_to_tab
    assert MainWindow._jump_to_sample_library is MainWindowNavigationMixin._jump_to_sample_library
    assert MainWindow._jump_to_joint_hub is MainWindowNavigationMixin._jump_to_joint_hub
    assert MainWindow._jump_to_results is MainWindowNavigationMixin._jump_to_results
    assert MainWindow._jump_to_history is MainWindowNavigationMixin._jump_to_history
    assert MainWindow._on_tech_saxs is MainWindowNavigationMixin._on_tech_saxs
    assert MainWindow._on_tech_waxs is MainWindowNavigationMixin._on_tech_waxs
    assert MainWindow._on_tech_dsc is MainWindowNavigationMixin._on_tech_dsc
    assert MainWindow._on_tech_ir is MainWindowNavigationMixin._on_tech_ir
    assert MainWindow._on_tech_nmr is MainWindowNavigationMixin._on_tech_nmr
    assert MainWindow._on_technique_selected is MainWindowNavigationMixin._on_technique_selected
    assert MainWindow._on_submodule_selected is MainWindowNavigationMixin._on_submodule_selected
