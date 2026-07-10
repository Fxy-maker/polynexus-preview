from __future__ import annotations

from polynexus.gui.main_window import MainWindow


def test_main_window_reuses_retranslate_helpers_from_retranslate_mixin() -> None:
    from polynexus.gui.main_window_retranslate_mixin import MainWindowRetranslateMixin

    assert MainWindow._retranslate_ui is MainWindowRetranslateMixin._retranslate_ui
    assert MainWindow._toggle_language is MainWindowRetranslateMixin._toggle_language
