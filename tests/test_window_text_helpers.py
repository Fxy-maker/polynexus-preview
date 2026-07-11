from __future__ import annotations

from pathlib import Path

from polynexus.gui.i18n import get_language, set_language


def test_window_text_helpers_cover_language_and_import_copy() -> None:
    from polynexus.gui.window_text_helpers import (
        data_file_dialog_filter,
        format_import_suggestion_reason,
        import_mode_text,
        ir_conclusion_state_display,
        is_default_project_label,
        lang_text,
    )

    previous = get_language()
    try:
        set_language("en")
        assert lang_text({"zh": "中文", "en": "English"}) == "English"
        assert is_default_project_label("") is True
        assert is_default_project_label("No project") is True
        assert "*.edf" in data_file_dialog_filter()
        assert "All Files" in data_file_dialog_filter()
        assert import_mode_text("sequence") == "Sequence"
        assert ir_conclusion_state_display(True) == "usable as a conclusion candidate"
        assert format_import_suggestion_reason(
            "registry:saxs.temperature",
            registry_lookup=lambda submodule_id: {"zh": "温变 SAXS", "en": "Temperature SAXS"},
        ) == "Matched sub-module signature: Temperature SAXS"
        assert format_import_suggestion_reason("extension:.edf") == "Matched file extension: .edf"

        set_language("zh")
        assert lang_text({"zh": "中文", "en": "English"}) == "中文"
        assert import_mode_text("sequence") == "序列"
        assert ir_conclusion_state_display(False) == "待复核"
    finally:
        set_language(previous)


def test_read_warning_count_handles_success_missing_and_failure(tmp_path, monkeypatch):
    from polynexus.gui.window_text_helpers import read_warning_count

    log_path = tmp_path / "polynexus.log"
    log_path.write_text("[INFO] ok\n[WARNING] first\n[WARNING] second\n", encoding="utf-8")

    assert read_warning_count(log_path) == 2
    assert read_warning_count(tmp_path / "missing.log") == 0

    warnings = []

    def broken_open(self, *args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(Path, "open", broken_open)
    assert read_warning_count(log_path, warning_fn=warnings.append) == 0
    assert warnings == ["Failed to read warning count from log file."]
