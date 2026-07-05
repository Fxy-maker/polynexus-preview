import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QDialogButtonBox

from polynexus.gui.import_suggestions import ImportSuggestion, suggest_import
from polynexus.gui.i18n import tr
from polynexus.gui.main_window import ImportSuggestionDialog, MainWindow


def test_suggest_import_detects_dsc_single_file(tmp_path):
    data_file = tmp_path / "run.001"
    data_file.write_text("dummy", encoding="utf-8")

    suggestion = suggest_import(str(data_file))

    assert suggestion is not None
    assert suggestion.technique == "dsc"
    assert suggestion.submodule == "dsc.standard"
    assert suggestion.input_mode == "single"


def test_suggest_import_detects_saxs_strain_directory(tmp_path):
    series_dir = tmp_path / "saxs_strain"
    series_dir.mkdir()
    for name in ["sample-10-S_0001.edf", "sample-20-S_0002.edf", "notes.txt"]:
        (series_dir / name).write_text("dummy", encoding="utf-8")

    suggestion = suggest_import(str(series_dir), is_dir=True)

    assert suggestion is not None
    assert suggestion.technique == "saxs"
    assert suggestion.submodule == "saxs.strain"
    assert suggestion.input_mode == "sequence"


def test_suggest_import_detects_saxs_temperature_directory(tmp_path):
    series_dir = tmp_path / "pa6变温"
    series_dir.mkdir()
    for name in [
        "PA6-250-170-S_0_00000.edf",
        "PA6-250-185-S_0_00000.edf",
        "PA6-250-195-S_0_00000.edf",
    ]:
        (series_dir / name).write_text("dummy", encoding="utf-8")

    suggestion = suggest_import(str(series_dir), is_dir=True)

    assert suggestion is not None
    assert suggestion.technique == "saxs"
    assert suggestion.submodule == "saxs.temperature"
    assert suggestion.input_mode == "sequence"


def test_suggest_import_detects_waxs_directory(tmp_path):
    raw_dir = tmp_path / "waxs_runs"
    raw_dir.mkdir()
    for name in ["run_a.raw", "run_b.raw", "run_c.txt"]:
        (raw_dir / name).write_text("dummy", encoding="utf-8")

    suggestion = suggest_import(str(raw_dir), is_dir=True)

    assert suggestion is not None
    assert suggestion.technique == "waxs"
    assert suggestion.submodule == ""
    assert suggestion.input_mode == "directory"


def test_suggest_import_detects_ir_temperature_directory(tmp_path):
    series_dir = tmp_path / "ir_temp"
    series_dir.mkdir()
    for name in ["PA6-sw-30.spa", "PA6-sw-60.spa", "PA6-jw-90.spa"]:
        (series_dir / name).write_text("dummy", encoding="utf-8")

    suggestion = suggest_import(str(series_dir), is_dir=True)

    assert suggestion is not None
    assert suggestion.technique == "ir"
    assert suggestion.submodule == "ir.temperature_2d"
    assert suggestion.input_mode == "sequence"


def test_suggest_import_detects_nmr_fid(tmp_path):
    data_dir = tmp_path / "sample_liquid"
    data_dir.mkdir()
    fid = data_dir / "fid"
    fid.write_bytes((1).to_bytes(4, byteorder="little", signed=True) * 8)

    suggestion = suggest_import(str(fid))

    assert suggestion is not None
    assert suggestion.technique == "nmr"
    assert suggestion.submodule == "nmr.liquid_h"
    assert suggestion.input_mode == "single"


def test_apply_import_suggestion_updates_main_window_context(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "sample.001"
    data_file.write_text("dummy", encoding="utf-8")

    window = MainWindow()
    monkeypatch.setattr(window, "_confirm_import_suggestion", lambda suggestion: suggestion)
    window._handle_import_candidate(str(data_file), is_dir=False, source="browse")

    assert window._current_filepath == str(data_file)
    assert window._current_technique == "dsc"
    assert window._current_submodule_id == "dsc.standard"
    assert window._current_input_mode == "single"
    assert window._path_input.text() == str(data_file)

    window.deleteLater()
    app.processEvents()


def test_apply_import_suggestion_uses_dialog_selection(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "sample.001"
    data_file.write_text("dummy", encoding="utf-8")

    window = MainWindow()
    monkeypatch.setattr(
        window,
        "_confirm_import_suggestion",
        lambda suggestion: SimpleNamespace(
            path=suggestion.path,
            is_dir=suggestion.is_dir,
            technique="ir",
            submodule="ir.standard",
            input_mode=suggestion.input_mode,
            reason=suggestion.reason,
        ),
    )

    window._handle_import_candidate(str(data_file), is_dir=False, source="browse")

    assert window._current_technique == "ir"
    assert window._current_submodule_id == "ir.standard"

    window.deleteLater()
    app.processEvents()


def test_apply_import_suggestion_cancel_falls_back_to_plain_import(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "sample.001"
    data_file.write_text("dummy", encoding="utf-8")

    window = MainWindow()
    monkeypatch.setattr(window, "_confirm_import_suggestion", lambda suggestion: None)
    window._handle_import_candidate(str(data_file), is_dir=False, source="browse")

    assert window._current_filepath == str(data_file)
    assert window._current_technique == ""

    window.deleteLater()
    app.processEvents()


def test_import_suggestion_dialog_allows_manual_mode_override(tmp_path):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "sample.001"
    data_file.write_text("dummy", encoding="utf-8")

    suggestion = ImportSuggestion(
        path=str(data_file),
        is_dir=False,
        technique="dsc",
        submodule="dsc.standard",
        input_mode="single",
        reason="extension:.001",
    )
    dialog = ImportSuggestionDialog(
        str(data_file),
        False,
        suggestion,
        {
            "dsc": [
                ("dsc.standard", "Standard DSC", "single"),
                ("dsc.isothermal", "Isothermal kinetics", "sequence"),
            ]
        },
    )

    dialog._mode_combo.setCurrentIndex(dialog._mode_combo.findData("directory"))

    assert dialog.selected_mode() == "directory"

    dialog.deleteLater()
    app.processEvents()


def test_import_suggestion_dialog_shows_detection_reason(tmp_path):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "sample.001"
    data_file.write_text("dummy", encoding="utf-8")

    suggestion = ImportSuggestion(
        path=str(data_file),
        is_dir=False,
        technique="dsc",
        submodule="dsc.standard",
        input_mode="single",
        reason="extension:.001",
    )
    dialog = ImportSuggestionDialog(
        str(data_file),
        False,
        suggestion,
        {},
    )

    assert "001" in dialog._reason_label.text()

    dialog.deleteLater()
    app.processEvents()


def test_import_suggestion_dialog_shows_apply_prompt(tmp_path):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "sample.001"
    data_file.write_text("dummy", encoding="utf-8")

    suggestion = ImportSuggestion(
        path=str(data_file),
        is_dir=False,
        technique="dsc",
        submodule="dsc.standard",
        input_mode="single",
        reason="extension:.001",
    )
    dialog = ImportSuggestionDialog(
        str(data_file),
        False,
        suggestion,
        {},
    )

    assert dialog._apply_label.text()

    dialog.deleteLater()
    app.processEvents()


def test_manual_import_dialog_uses_neutral_copy(tmp_path):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "unknown.foo"
    data_file.write_text("dummy", encoding="utf-8")

    suggestion = ImportSuggestion(
        path=str(data_file),
        is_dir=False,
        technique="",
        submodule="",
        input_mode="single",
        reason="manual",
    )
    dialog = ImportSuggestionDialog(
        str(data_file),
        False,
        suggestion,
        {},
    )

    cancel_button = dialog._button_box.button(QDialogButtonBox.Cancel)

    assert dialog.windowTitle() == tr("IMPORT_SETUP_TITLE")
    assert dialog._intro_label.text() == tr("IMPORT_SETUP_MESSAGE")
    assert dialog._apply_label.text() == tr("IMPORT_SETUP_APPLY")
    assert dialog.selected_technique() == ""
    assert dialog._technique_combo.currentText() == tr("IMPORT_SUGGESTION_TECHNIQUE_EMPTY")
    assert dialog._copy_path_button.text() == tr("COMMON_COPY")
    assert dialog._ok_button is not None
    assert not dialog._ok_button.isEnabled()
    assert not dialog._technique_hint.isHidden()
    assert cancel_button is not None
    assert cancel_button.text() == tr("COMMON_CANCEL")

    dialog.deleteLater()
    app.processEvents()


def test_manual_import_dialog_enables_apply_after_choosing_technique(tmp_path):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "unknown.foo"
    data_file.write_text("dummy", encoding="utf-8")

    suggestion = ImportSuggestion(
        path=str(data_file),
        is_dir=False,
        technique="",
        submodule="",
        input_mode="single",
        reason="manual",
    )
    dialog = ImportSuggestionDialog(
        str(data_file),
        False,
        suggestion,
        {},
    )

    dialog._technique_combo.setCurrentIndex(dialog._technique_combo.findData("dsc"))

    assert dialog._ok_button is not None
    assert dialog._ok_button.isEnabled()
    assert not dialog._technique_hint.isVisible()

    dialog.deleteLater()
    app.processEvents()


def test_import_suggestion_dialog_copies_path_to_clipboard(tmp_path):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "sample.001"
    data_file.write_text("dummy", encoding="utf-8")

    suggestion = ImportSuggestion(
        path=str(data_file),
        is_dir=False,
        technique="dsc",
        submodule="dsc.standard",
        input_mode="single",
        reason="extension:.001",
    )
    dialog = ImportSuggestionDialog(
        str(data_file),
        False,
        suggestion,
        {},
    )

    app.clipboard().clear()
    dialog._copy_path_to_clipboard()

    assert app.clipboard().text() == str(data_file)

    dialog.deleteLater()
    app.processEvents()


def test_import_suggestion_dialog_copies_summary_to_clipboard(tmp_path):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "sample.001"
    data_file.write_text("dummy", encoding="utf-8")

    suggestion = ImportSuggestion(
        path=str(data_file),
        is_dir=False,
        technique="dsc",
        submodule="dsc.standard",
        input_mode="single",
        reason="extension:.001",
    )
    dialog = ImportSuggestionDialog(
        str(data_file),
        False,
        suggestion,
        {},
    )

    app.clipboard().clear()
    dialog._copy_summary_to_clipboard()

    text = app.clipboard().text()
    assert tr("IMPORT_SUGGESTION_TITLE") in text
    assert str(data_file) in text
    assert tr("IMPORT_SUGGESTION_REASON") in text

    dialog.deleteLater()
    app.processEvents()


def test_import_suggestion_dialog_opens_containing_folder(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "sample.001"
    data_file.write_text("dummy", encoding="utf-8")

    suggestion = ImportSuggestion(
        path=str(data_file),
        is_dir=False,
        technique="dsc",
        submodule="dsc.standard",
        input_mode="single",
        reason="extension:.001",
    )
    dialog = ImportSuggestionDialog(
        str(data_file),
        False,
        suggestion,
        {},
    )

    opened = []
    monkeypatch.setattr("polynexus.gui.main_window.os.startfile", lambda path: opened.append(path))
    dialog._open_path_folder()

    assert opened == [str(tmp_path)]

    dialog.deleteLater()
    app.processEvents()


def test_import_suggestion_dialog_hides_empty_submodule_choices(tmp_path):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "sample.001"
    data_file.write_text("dummy", encoding="utf-8")

    suggestion = ImportSuggestion(
        path=str(data_file),
        is_dir=False,
        technique="dsc",
        submodule="",
        input_mode="single",
        reason="extension:.001",
    )
    dialog = ImportSuggestionDialog(
        str(data_file),
        False,
        suggestion,
        {},
    )

    assert not dialog._submodule_combo.isEnabled()
    assert not dialog._submodule_hint.isHidden()

    dialog.deleteLater()
    app.processEvents()


def test_confirm_import_suggestion_returns_selected_mode(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "sample.001"
    data_file.write_text("dummy", encoding="utf-8")

    window = MainWindow()
    monkeypatch.setattr(
        window,
        "_import_submodule_options",
        lambda: {
            "dsc": [
                ("dsc.standard", "Standard DSC", "single"),
                ("dsc.isothermal", "Isothermal kinetics", "sequence"),
            ]
        },
    )

    original_exec = ImportSuggestionDialog.exec

    def fake_exec(dialog):
        target_index = 0
        for idx in range(dialog._submodule_combo.count()):
            if dialog._submodule_combo.itemData(idx) == ("dsc.isothermal", "sequence"):
                target_index = idx
                break
        dialog._submodule_combo.setCurrentIndex(target_index)
        dialog._mode_combo.setCurrentIndex(dialog._mode_combo.findData("directory"))
        return ImportSuggestionDialog.Accepted

    monkeypatch.setattr(ImportSuggestionDialog, "exec", fake_exec)
    try:
        confirmed = window._confirm_import_suggestion(
            ImportSuggestion(
                path=str(data_file),
                is_dir=False,
                technique="dsc",
                submodule="dsc.standard",
                input_mode="single",
                reason="extension:.001",
            )
        )
    finally:
        monkeypatch.setattr(ImportSuggestionDialog, "exec", original_exec)

    assert confirmed is not None
    assert confirmed.submodule == "dsc.isothermal"
    assert confirmed.input_mode == "directory"

    window.deleteLater()
    app.processEvents()


def test_apply_import_suggestion_logs_detection_reason(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "sample.001"
    data_file.write_text("dummy", encoding="utf-8")

    window = MainWindow()
    monkeypatch.setattr(window, "_apply_import_selection", lambda *args, **kwargs: None)
    messages = []
    monkeypatch.setattr(window, "log", lambda msg: messages.append(msg))

    window._apply_import_suggestion(
        ImportSuggestion(
            path=str(data_file),
            is_dir=False,
            technique="dsc",
            submodule="dsc.standard",
            input_mode="single",
            reason="extension:.001",
        )
    )

    assert messages
    assert "001" in messages[-1]

    window.deleteLater()
    app.processEvents()


def test_apply_import_suggestion_logs_manual_setup_message(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "unknown.foo"
    data_file.write_text("dummy", encoding="utf-8")

    window = MainWindow()
    monkeypatch.setattr(window, "_apply_import_selection", lambda *args, **kwargs: None)
    messages = []
    monkeypatch.setattr(window, "log", lambda msg: messages.append(msg))

    window._apply_import_suggestion(
        ImportSuggestion(
            path=str(data_file),
            is_dir=False,
            technique="waxs",
            submodule="waxs.static",
            input_mode="single",
            reason="manual",
        )
    )

    assert messages
    assert messages[-1].startswith(tr("LOG_IMPORT_SETUP_APPLIED", ""))
    assert "WAXS" in messages[-1]
    assert tr("IMPORT_MODE_SINGLE") in messages[-1]
    assert tr("IMPORT_SUGGESTION_REASON_MANUAL") in messages[-1]

    window.deleteLater()
    app.processEvents()


def test_handle_import_candidate_uses_manual_chooser_when_no_suggestion(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "unknown.foo"
    data_file.write_text("dummy", encoding="utf-8")

    window = MainWindow()
    monkeypatch.setattr(
        window,
        "_choose_import_manually",
        lambda path, is_dir=False: SimpleNamespace(
            path=path,
            is_dir=is_dir,
            technique="waxs",
            submodule="waxs.static",
            input_mode="single",
            reason="manual",
        ),
    )

    window._handle_import_candidate(str(data_file), is_dir=False, source="browse")

    assert window._current_filepath == str(data_file)
    assert window._current_technique == "waxs"
    assert window._current_submodule_id == "waxs.static"
    assert window._current_input_mode == "single"

    window.deleteLater()
    app.processEvents()


def test_handle_import_candidate_manual_cancel_falls_back_to_plain_import(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "unknown.foo"
    data_file.write_text("dummy", encoding="utf-8")

    window = MainWindow()
    messages = []
    monkeypatch.setattr(window, "_choose_import_manually", lambda path, is_dir=False: None)
    monkeypatch.setattr(window, "log", lambda msg: messages.append(msg))

    window._handle_import_candidate(str(data_file), is_dir=False, source="browse")

    assert window._current_filepath == str(data_file)
    assert window._current_technique == ""
    assert window._current_input_mode == "single"
    assert messages[-1] == tr(
        "LOG_IMPORT_BASIC_APPLIED",
        f"{tr('IMPORT_MODE_SINGLE')} | {data_file.name}",
    )

    window.deleteLater()
    app.processEvents()


def test_apply_import_suggestion_cancel_falls_back_to_basic_import_log(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "sample.001"
    data_file.write_text("dummy", encoding="utf-8")

    window = MainWindow()
    messages = []
    monkeypatch.setattr(window, "_confirm_import_suggestion", lambda suggestion: None)
    monkeypatch.setattr(window, "log", lambda msg: messages.append(msg))

    window._handle_import_candidate(str(data_file), is_dir=False, source="browse")

    assert window._current_filepath == str(data_file)
    assert window._current_technique == ""
    assert window._current_input_mode == "single"
    assert messages[-1] == tr(
        "LOG_IMPORT_BASIC_APPLIED",
        f"{tr('IMPORT_MODE_SINGLE')} | {data_file.name}",
    )

    window.deleteLater()
    app.processEvents()


def test_directory_import_updates_workspace_with_sequence_mode(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    series_dir = tmp_path / "ir_temp"
    series_dir.mkdir()
    for name in ["PA6-sw-30.spa", "PA6-sw-60.spa", "PA6-jw-90.spa"]:
        (series_dir / name).write_text("dummy", encoding="utf-8")

    window = MainWindow()
    monkeypatch.setattr(window, "_confirm_import_suggestion", lambda suggestion: suggestion)

    window._handle_import_candidate(str(series_dir), is_dir=True, source="browse")

    assert window._current_input_mode == "sequence"
    sequence_prefix = f"{tr('IMPORT_MODE_SEQUENCE')} | "
    assert window._workflow_metric_data.text().startswith(sequence_prefix)
    assert sequence_prefix in window._workspace_subtitle.text()
    assert window._workflow_metric_state.text() == tr("WORKFLOW_SEQUENCE_READY")

    window.deleteLater()
    app.processEvents()
