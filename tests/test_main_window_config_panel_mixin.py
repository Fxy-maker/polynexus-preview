from __future__ import annotations

from polynexus.gui.main_window import MainWindow
from polynexus.gui.main_window_config_panel_mixin import MainWindowConfigPanelMixin


def test_main_window_reuses_config_panel_and_preset_helpers_from_config_panel_mixin() -> None:
    assert MainWindow._update_config_panel is MainWindowConfigPanelMixin._update_config_panel
    assert MainWindow._add_config_field is MainWindowConfigPanelMixin._add_config_field
    assert (
        MainWindow._connect_config_widget_signals
        is MainWindowConfigPanelMixin._connect_config_widget_signals
    )
    assert (
        MainWindow._on_config_widget_changed
        is MainWindowConfigPanelMixin._on_config_widget_changed
    )
    assert (
        MainWindow._calibration_config_schema
        is MainWindowConfigPanelMixin._calibration_config_schema
    )
    assert MainWindow._mask_config_schema is MainWindowConfigPanelMixin._mask_config_schema
    assert MainWindow._calibration_hint_text is MainWindowConfigPanelMixin._calibration_hint_text
    assert MainWindow._mask_hint_text is MainWindowConfigPanelMixin._mask_hint_text
    assert MainWindow._build_run_config is MainWindowConfigPanelMixin._build_run_config
    assert (
        MainWindow._build_config_for_technique
        is MainWindowConfigPanelMixin._build_config_for_technique
    )
    assert MainWindow._current_config_widget_keys is MainWindowConfigPanelMixin._current_config_widget_keys
    assert MainWindow._config_widget_by_key is MainWindowConfigPanelMixin._config_widget_by_key
    assert MainWindow._config_hint_widget_by_key is MainWindowConfigPanelMixin._config_hint_widget_by_key
    assert MainWindow._current_config_preset_scope is MainWindowConfigPanelMixin._current_config_preset_scope
    assert MainWindow._current_config_preset_name is MainWindowConfigPanelMixin._current_config_preset_name
    assert MainWindow._set_config_preset_placeholder is MainWindowConfigPanelMixin._set_config_preset_placeholder
    assert MainWindow._on_config_preset_name_changed is MainWindowConfigPanelMixin._on_config_preset_name_changed
    assert MainWindow._update_config_preset_action_state is MainWindowConfigPanelMixin._update_config_preset_action_state
    assert MainWindow._refresh_config_preset_controls is MainWindowConfigPanelMixin._refresh_config_preset_controls
    assert MainWindow._on_save_config_preset is MainWindowConfigPanelMixin._on_save_config_preset
    assert MainWindow._on_load_config_preset is MainWindowConfigPanelMixin._on_load_config_preset
    assert MainWindow._on_delete_config_preset is MainWindowConfigPanelMixin._on_delete_config_preset
    assert MainWindow._collect_config_panel_values is MainWindowConfigPanelMixin._collect_config_panel_values
