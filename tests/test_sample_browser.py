import os
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication, QLabel, QPushButton
from PySide6.QtWidgets import QDialogButtonBox

import pytest

from polynexus.data.sample_db import SampleDB
from polynexus.gui.i18n import get_language, set_language, tr
from polynexus.gui.widgets.sample_browser import (
    BatchDetailsDialog,
    CreateBatchDialog,
    CreateSampleDialog,
    EditBatchDialog,
    EditSampleDialog,
    SampleBrowser,
)


def test_create_sample_dialog_aliases_accepts_full_width_separators():
    app = QApplication.instance() or QApplication([])

    dialog = CreateSampleDialog()
    dialog._aliases_input.setText("PA6\uff1bNylon-6\uff0cLab Alias; Legacy")

    assert dialog.aliases() == ["PA6", "Nylon-6", "Lab Alias", "Legacy"]

    dialog.deleteLater()
    app.processEvents()


def test_create_sample_dialog_requires_name_before_confirm():
    app = QApplication.instance() or QApplication([])

    dialog = CreateSampleDialog()

    assert hasattr(dialog, "_ok_button")
    assert not dialog._ok_button.isEnabled()

    dialog._name_input.setText("PA6")
    assert dialog._ok_button.isEnabled()

    dialog._name_input.clear()
    assert not dialog._ok_button.isEnabled()

    dialog.deleteLater()
    app.processEvents()


def test_edit_sample_dialog_requires_nonempty_name_before_confirm():
    app = QApplication.instance() or QApplication([])

    dialog = EditSampleDialog(sample_name="PA6", aliases=["Nylon-6"])

    assert hasattr(dialog, "_ok_button")
    assert dialog._ok_button.isEnabled()

    dialog._name_input.clear()
    assert not dialog._ok_button.isEnabled()

    dialog._name_input.setText("PA66")
    assert dialog._ok_button.isEnabled()

    dialog.deleteLater()
    app.processEvents()


def test_create_batch_dialog_reuses_current_file_directory_for_browse(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    current_file = tmp_path / "data" / "sample.csv"
    current_file.parent.mkdir()
    current_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    dialog = CreateBatchDialog()
    dialog._file_input.setText(str(current_file))

    seen = {}

    def fake_get_open_file_name(parent, title, start_dir, file_filter):
        seen["start_dir"] = start_dir
        return "", ""

    monkeypatch.setattr("polynexus.gui.widgets.sample_browser.QFileDialog.getOpenFileName", fake_get_open_file_name)
    dialog._browse_file()

    assert seen["start_dir"] == str(current_file.parent)

    dialog.deleteLater()
    app.processEvents()


def test_create_batch_dialog_uses_file_stem_as_default_batch_label(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    selected_file = tmp_path / "data" / "annealed-01.csv"
    selected_file.parent.mkdir()
    selected_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    dialog = CreateBatchDialog()

    monkeypatch.setattr(
        "polynexus.gui.widgets.sample_browser.QFileDialog.getOpenFileName",
        lambda parent, title, start_dir, file_filter: (str(selected_file), ""),
    )
    dialog._browse_file()

    assert dialog.file_path() == str(selected_file)
    assert dialog.batch_label() == "annealed-01"

    dialog.deleteLater()
    app.processEvents()


def test_create_batch_dialog_keeps_manual_batch_label_when_browsing(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    selected_file = tmp_path / "data" / "annealed-01.csv"
    selected_file.parent.mkdir()
    selected_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    dialog = CreateBatchDialog()
    dialog._label_input.setText("custom-batch")

    monkeypatch.setattr(
        "polynexus.gui.widgets.sample_browser.QFileDialog.getOpenFileName",
        lambda parent, title, start_dir, file_filter: (str(selected_file), ""),
    )
    dialog._browse_file()

    assert dialog.batch_label() == "custom-batch"

    dialog.deleteLater()
    app.processEvents()


def test_create_batch_dialog_auto_detects_technique_from_selected_file(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    selected_file = tmp_path / "data" / "annealed-01.raw"
    selected_file.parent.mkdir()
    selected_file.write_text("2theta,I\n10,1.0\n", encoding="utf-8")

    dialog = CreateBatchDialog()

    monkeypatch.setattr(
        "polynexus.gui.widgets.sample_browser.QFileDialog.getOpenFileName",
        lambda parent, title, start_dir, file_filter: (str(selected_file), ""),
    )
    dialog._browse_file()

    assert dialog.technique() == "waxs"

    dialog.deleteLater()
    app.processEvents()


def test_create_batch_dialog_requires_label_and_file_before_confirm(tmp_path):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "data" / "annealed-01.csv"
    data_file.parent.mkdir()
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    dialog = CreateBatchDialog()

    assert hasattr(dialog, "_ok_button")
    assert not dialog._ok_button.isEnabled()

    dialog._label_input.setText("annealed-01")
    assert not dialog._ok_button.isEnabled()

    dialog._file_input.setText(str(data_file))
    dialog._update_accept_state()
    assert dialog._ok_button.isEnabled()

    dialog.deleteLater()
    app.processEvents()


def test_create_batch_dialog_keeps_manual_technique_override_when_browsing(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    selected_file = tmp_path / "data" / "annealed-01.raw"
    selected_file.parent.mkdir()
    selected_file.write_text("2theta,I\n10,1.0\n", encoding="utf-8")

    dialog = CreateBatchDialog()
    dialog._technique_combo.setCurrentIndex(dialog._technique_combo.findData("ir"))

    monkeypatch.setattr(
        "polynexus.gui.widgets.sample_browser.QFileDialog.getOpenFileName",
        lambda parent, title, start_dir, file_filter: (str(selected_file), ""),
    )
    dialog._browse_file()

    assert dialog.technique() == "ir"

    dialog.deleteLater()
    app.processEvents()


def test_edit_batch_dialog_browse_defaults_to_selected_file_directory(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    first_file = tmp_path / "data_a" / "sample_a.csv"
    second_file = tmp_path / "data_b" / "sample_b.csv"
    first_file.parent.mkdir()
    second_file.parent.mkdir()
    first_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")
    second_file.write_text("q,I\n0.2,2.0\n", encoding="utf-8")

    dialog = EditBatchDialog(
        {"label": "annealed-01", "condition_values": {"technique": "saxs"}},
        [
            {"id": "file-1", "file_path": str(first_file), "technique": "saxs"},
            {"id": "file-2", "file_path": str(second_file), "technique": "saxs"},
        ],
    )
    dialog._file_combo.setCurrentIndex(1)

    seen = {}

    def fake_get_open_file_name(parent, title, start_dir, file_filter):
        seen["start_dir"] = start_dir
        return "", ""

    monkeypatch.setattr("polynexus.gui.widgets.sample_browser.QFileDialog.getOpenFileName", fake_get_open_file_name)
    dialog._browse_file()

    assert seen["start_dir"] == str(second_file.parent)

    dialog.deleteLater()
    app.processEvents()


def test_edit_batch_dialog_auto_detects_technique_from_replacement_file(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    original_file = tmp_path / "data_a" / "sample_a.csv"
    replacement_file = tmp_path / "data_b" / "sample_b.raw"
    original_file.parent.mkdir()
    replacement_file.parent.mkdir()
    original_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")
    replacement_file.write_text("2theta,I\n10,1.0\n", encoding="utf-8")

    dialog = EditBatchDialog(
        {"label": "annealed-01", "condition_values": {"technique": "saxs"}},
        [
            {"id": "file-1", "file_path": str(original_file), "technique": "saxs"},
        ],
    )

    monkeypatch.setattr(
        "polynexus.gui.widgets.sample_browser.QFileDialog.getOpenFileName",
        lambda parent, title, start_dir, file_filter: (str(replacement_file), ""),
    )
    dialog._browse_file()

    assert dialog.technique() == "waxs"

    dialog.deleteLater()
    app.processEvents()


def test_edit_batch_dialog_requires_nonempty_label_before_confirm(tmp_path):
    app = QApplication.instance() or QApplication([])

    original_file = tmp_path / "data_a" / "sample_a.csv"
    original_file.parent.mkdir()
    original_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    dialog = EditBatchDialog(
        {"label": "annealed-01", "condition_values": {"technique": "saxs"}},
        [
            {"id": "file-1", "file_path": str(original_file), "technique": "saxs"},
        ],
    )

    assert hasattr(dialog, "_ok_button")
    assert dialog._ok_button.isEnabled()

    dialog._label_input.clear()
    assert not dialog._ok_button.isEnabled()

    dialog._label_input.setText("annealed-02")
    assert dialog._ok_button.isEnabled()

    dialog.deleteLater()
    app.processEvents()


def test_edit_batch_dialog_keeps_manual_technique_override_when_replacing_file(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    original_file = tmp_path / "data_a" / "sample_a.csv"
    replacement_file = tmp_path / "data_b" / "sample_b.raw"
    original_file.parent.mkdir()
    replacement_file.parent.mkdir()
    original_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")
    replacement_file.write_text("2theta,I\n10,1.0\n", encoding="utf-8")

    dialog = EditBatchDialog(
        {"label": "annealed-01", "condition_values": {"technique": "saxs"}},
        [
            {"id": "file-1", "file_path": str(original_file), "technique": "saxs"},
        ],
    )
    dialog._technique_combo.setCurrentIndex(dialog._technique_combo.findData("ir"))

    monkeypatch.setattr(
        "polynexus.gui.widgets.sample_browser.QFileDialog.getOpenFileName",
        lambda parent, title, start_dir, file_filter: (str(replacement_file), ""),
    )
    dialog._browse_file()

    assert dialog.technique() == "ir"

    dialog.deleteLater()
    app.processEvents()


def test_sample_browser_create_batch_with_file_persists_batch_and_file(tmp_path):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    data_file = tmp_path / "sample.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    browser = SampleBrowser()
    browser.set_db(db)

    batch_id, stored_path = browser.create_batch_with_file(
        sample_id,
        "annealed-01",
        "saxs",
        str(data_file),
    )

    batches = db.get_batches(sample_id)
    files = db.get_data_files(batch_id)

    assert any(batch["id"] == batch_id and batch["label"] == "annealed-01" for batch in batches)
    assert len(files) == 1
    assert files[0]["technique"] == "saxs"
    assert files[0]["file_path"] == stored_path

    db.close()
    browser.deleteLater()
    app.processEvents()


def test_sample_browser_batch_row_shows_source_and_analysis_status(tmp_path):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    data_file = tmp_path / "sample.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    browser = SampleBrowser()
    browser.set_db(db)
    batch_id, _ = browser.create_batch_with_file(
        sample_id,
        "annealed-01",
        "saxs",
        str(data_file),
    )
    db.create_analysis_run(
        batch_id,
        "saxs",
        submodule="saxs.static",
        results_summary={"L_nm": 12.0},
    )

    browser.refresh()
    assert browser.select_sample(sample_id)

    item = browser._batch_list.item(0)
    widget = browser._batch_list.itemWidget(item)
    labels = [child.text() for child in widget.findChildren(QLabel)]

    assert any("annealed-01" in text for text in labels)
    assert any("sample.csv" in text for text in labels)
    assert any(tr("SAMPLE_BATCH_STATUS_ANALYZED", 1) in text for text in labels)
    assert any("saxs.static" in text for text in labels)

    db.close()
    browser.deleteLater()
    app.processEvents()



def test_sample_browser_batch_row_uses_pending_status_for_latest_run(tmp_path):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    data_file = tmp_path / "sample.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    browser = SampleBrowser()
    browser.set_db(db)
    batch_id, _ = browser.create_batch_with_file(
        sample_id,
        "annealed-01",
        "saxs",
        str(data_file),
    )
    run_id = db.create_analysis_run(
        batch_id,
        "saxs",
        submodule="saxs.static",
        results_summary={"L_nm": 12.0},
    )
    db.update_analysis_status(run_id, "pending")

    browser.refresh()
    assert browser.select_sample(sample_id)

    item = browser._batch_list.item(0)
    widget = browser._batch_list.itemWidget(item)
    labels = [child.text() for child in widget.findChildren(QLabel)]

    assert tr("SAMPLE_RUN_STATUS_PENDING") in labels
    assert any(tr("SAMPLE_BATCH_RECENT", "SAXS / saxs.static", tr("SAMPLE_RUN_STATUS_PENDING"), str(run_id and db.get_analysis_runs(batch_id)[0].get("created_at", ""))[:10] or "-")[:6] in text for text in labels)

    db.close()
    browser.deleteLater()
    app.processEvents()


def test_sample_browser_batch_row_uses_failed_status_for_latest_run(tmp_path):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    data_file = tmp_path / "sample.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    browser = SampleBrowser()
    browser.set_db(db)
    batch_id, _ = browser.create_batch_with_file(
        sample_id,
        "annealed-01",
        "saxs",
        str(data_file),
    )
    run_id = db.create_analysis_run(
        batch_id,
        "saxs",
        submodule="saxs.static",
        results_summary={"L_nm": 12.0},
    )
    db.update_analysis_status(run_id, "failed")

    browser.refresh()
    assert browser.select_sample(sample_id)

    item = browser._batch_list.item(0)
    widget = browser._batch_list.itemWidget(item)
    labels = [child.text() for child in widget.findChildren(QLabel)]

    assert tr("SAMPLE_RUN_STATUS_FAILED") in labels
    assert any(tr("SAMPLE_RUN_STATUS_FAILED") in text for text in labels)

    db.close()
    browser.deleteLater()
    app.processEvents()
def test_sample_browser_rejects_duplicate_file_attachment_within_sample(tmp_path):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    data_file = tmp_path / "sample.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    browser = SampleBrowser()
    browser.set_db(db)
    browser.create_batch_with_file(
        sample_id,
        "annealed-01",
        "saxs",
        str(data_file),
    )

    with pytest.raises(ValueError) as exc_info:
        browser.create_batch_with_file(
            sample_id,
            "annealed-02",
            "saxs",
            str(data_file),
        )

    assert "annealed-01" in str(exc_info.value)

    db.close()
    browser.deleteLater()
    app.processEvents()


def test_sample_browser_rejects_duplicate_file_attachment_even_if_technique_differs(tmp_path):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    data_file = tmp_path / "sample.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    browser = SampleBrowser()
    browser.set_db(db)
    browser.create_batch_with_file(
        sample_id,
        "annealed-01",
        "saxs",
        str(data_file),
    )

    with pytest.raises(ValueError) as exc_info:
        browser.create_batch_with_file(
            sample_id,
            "annealed-02",
            "waxs",
            str(data_file),
        )

    assert "annealed-01" in str(exc_info.value)

    db.close()
    browser.deleteLater()
    app.processEvents()


def test_sample_browser_update_sample_entry_updates_name_and_aliases(tmp_path):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6", aliases=["Nylon-6"])

    browser = SampleBrowser()
    browser.set_db(db)

    updated_name = browser.update_sample_entry(
        sample_id,
        "PA66",
        ["Nylon-66", "Zytel"],
    )

    sample = db.get_sample(sample_id)

    assert updated_name == "PA66"
    assert sample["polymer_name"] == "PA66"
    assert sample["aliases"] == ["Nylon-66", "Zytel"]

    db.close()
    browser.deleteLater()
    app.processEvents()


def test_sample_browser_update_sample_entry_rejects_duplicate_name(tmp_path):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    db.create_sample("PET")

    browser = SampleBrowser()
    browser.set_db(db)

    with pytest.raises(ValueError) as exc_info:
        browser.update_sample_entry(sample_id, "PET", [])

    assert tr("SAMPLE_EDIT_DUPLICATE") == str(exc_info.value)

    db.close()
    browser.deleteLater()
    app.processEvents()


def test_sample_browser_update_batch_entry_updates_label_technique_and_file(tmp_path):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    first_file = tmp_path / "sample_a.csv"
    replacement_file = tmp_path / "sample_b.raw"
    first_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")
    replacement_file.write_text("q,I\n0.2,2.0\n", encoding="utf-8")

    browser = SampleBrowser()
    browser.set_db(db)
    batch_id, _ = browser.create_batch_with_file(
        sample_id,
        "annealed-01",
        "saxs",
        str(first_file),
    )
    file_id = db.get_data_files(batch_id)[0]["id"]

    updated_label = browser.update_batch_entry(
        batch_id,
        "annealed-02",
        "waxs",
        target_file_id=file_id,
        replacement_file_path=str(replacement_file),
    )

    batch = db.get_batch(batch_id)
    files = db.get_data_files(batch_id)

    assert updated_label == "annealed-02"
    assert batch["label"] == "annealed-02"
    assert batch["instrument"] == "WAXS"
    assert batch["condition_values"]["technique"] == "waxs"
    assert len(files) == 1
    assert files[0]["technique"] == "waxs"
    assert files[0]["file_path"] == str(replacement_file.resolve())
    assert files[0]["file_type"] == "raw"

    db.close()
    browser.deleteLater()
    app.processEvents()


def test_sample_browser_update_batch_entry_can_remove_attached_file(tmp_path):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    data_file = tmp_path / "sample.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    browser = SampleBrowser()
    browser.set_db(db)
    batch_id, _ = browser.create_batch_with_file(
        sample_id,
        "annealed-01",
        "saxs",
        str(data_file),
    )
    file_id = db.get_data_files(batch_id)[0]["id"]

    browser.update_batch_entry(
        batch_id,
        "annealed-01",
        "saxs",
        target_file_id=file_id,
        remove_file=True,
    )

    files = db.get_data_files(batch_id)

    assert files == []

    db.close()
    browser.deleteLater()
    app.processEvents()


def test_batch_details_dialog_shows_attached_files_and_runs(tmp_path):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    first_file = tmp_path / "sample_a.csv"
    second_file = tmp_path / "sample_b.csv"
    first_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")
    second_file.write_text("q,I\n0.2,2.0\n", encoding="utf-8")

    browser = SampleBrowser()
    browser.set_db(db)
    batch_id, _ = browser.create_batch_with_file(
        sample_id,
        "annealed-01",
        "saxs",
        str(first_file),
    )
    db.add_data_file(batch_id, str(second_file.resolve()), "saxs", file_type="csv", import_order=1)
    db.create_analysis_run(
        batch_id,
        "saxs",
        submodule="saxs.static",
        output_dir=str(tmp_path / "output"),
        results_summary={"L_nm": 12.0},
    )

    snapshot = browser._batch_details_snapshot(batch_id)
    assert snapshot is not None

    dialog = BatchDetailsDialog(
        snapshot["batch"]["label"],
        snapshot["files"],
        snapshot["runs"],
        browser,
    )

    assert dialog._files_table.rowCount() == 2
    assert dialog._runs_table.rowCount() == 1
    assert dialog._files_table.item(0, 0).text() == "sample_a.csv"
    assert dialog._runs_table.item(0, 2).text() == "saxs.static"

    dialog.deleteLater()
    db.close()
    browser.deleteLater()
    app.processEvents()


def test_sample_browser_batch_row_exposes_analysis_action(tmp_path):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    data_file = tmp_path / "sample.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    browser = SampleBrowser()
    browser.set_db(db)
    browser.create_batch_with_file(
        sample_id,
        "annealed-01",
        "saxs",
        str(data_file),
    )
    browser.refresh()
    assert browser.select_sample(sample_id)

    item = browser._batch_list.item(0)
    widget = browser._batch_list.itemWidget(item)
    texts = [child.text() for child in widget.findChildren(QPushButton)]

    assert tr("SAMPLE_BATCH_ANALYZE") in texts
    assert tr("SAMPLE_BATCH_EDIT") in texts

    db.close()
    browser.deleteLater()
    app.processEvents()


def test_sample_browser_refresh_auto_selects_only_visible_sample_after_filter_change(tmp_path):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    first_id = db.create_sample("PA6")
    second_id = db.create_sample("PET")

    browser = SampleBrowser()
    browser.set_db(db)
    assert browser.select_sample(first_id)

    browser._search_input.setText("PET")

    assert browser._selected_sample_id == second_id
    assert browser._table.currentRow() == 0

    db.close()
    browser.deleteLater()
    app.processEvents()


def test_sample_browser_refresh_clears_selection_when_multiple_filtered_results_remain(tmp_path):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    first_id = db.create_sample("PA6")
    db.create_sample("PET")
    db.create_sample("PEEK")

    browser = SampleBrowser()
    browser.set_db(db)
    assert browser.select_sample(first_id)

    browser._search_input.setText("PE")

    assert browser._selected_sample_id is None
    assert browser._table.currentRow() in {-1, 0}
    assert browser._batch_list.count() == 0

    db.close()
    browser.deleteLater()
    app.processEvents()


def test_sample_browser_shows_empty_state_when_filter_returns_no_results(tmp_path):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    db.create_sample("PA6")
    db.create_sample("PET")

    browser = SampleBrowser()
    browser.set_db(db)
    browser._search_input.setText("XYZ")

    assert browser._table.rowCount() == 0
    assert not browser._empty_state.isHidden()
    assert tr("SAMPLE_EMPTY_RESULTS") == browser._empty_state.text()

    browser._search_input.clear()
    assert browser._empty_state.isHidden()

    db.close()
    browser.deleteLater()
    app.processEvents()


def test_sample_browser_search_escape_clears_filter(tmp_path):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    db.create_sample("PA6")
    db.create_sample("PET")

    browser = SampleBrowser()
    browser.set_db(db)
    browser._search_input.setText("PET")
    assert browser._table.rowCount() == 1

    event = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
    browser.eventFilter(browser._search_input, event)

    assert browser._search_input.text() == ""
    assert browser._table.rowCount() == 2

    db.close()
    browser.deleteLater()
    app.processEvents()


def test_sample_browser_main_table_copy_shortcut_copies_selected_row(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        db = SampleDB(tmp_path / "samples.db")
        first_id = db.create_sample("PA6", aliases=["Nylon-6"])
        db.create_sample("PET")

        browser = SampleBrowser()
        browser.set_db(db)
        assert browser.select_sample(first_id)

        browser._table.selectRow(0)
        app.processEvents()
        browser._table_copy_shortcut.activated.emit()

        headers = [browser._table.horizontalHeaderItem(i).text() for i in range(browser._table.columnCount())]
        lines = QApplication.clipboard().text().splitlines()
        assert lines[0] == "\t".join(headers)
        assert lines[1].startswith("PA6\t")
        assert "Nylon-6" in lines[1]
        assert len(lines) == 2

        browser._db = None
        browser.deleteLater()
        app.processEvents()
        db.close()
    finally:
        set_language(previous)


def test_sample_browser_focus_search_selects_existing_text(tmp_path):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    db.create_sample("PA6")
    db.create_sample("PET")

    browser = SampleBrowser()
    browser.set_db(db)
    browser._search_input.setText("PET")

    browser._focus_search_input()

    assert browser._search_input.hasSelectedText()
    assert browser._search_input.selectedText() == "PET"

    db.close()
    browser.deleteLater()
    app.processEvents()


def test_batch_details_dialog_exposes_copy_and_open_actions(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    first_file = tmp_path / "sample_a.csv"
    second_dir = tmp_path / "nested"
    second_dir.mkdir()
    second_file = second_dir / "sample_b.csv"
    first_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")
    second_file.write_text("q,I\n0.2,2.0\n", encoding="utf-8")

    browser = SampleBrowser()
    browser.set_db(db)
    batch_id, _ = browser.create_batch_with_file(
        sample_id,
        "annealed-01",
        "saxs",
        str(first_file),
    )
    db.add_data_file(batch_id, str(second_file.resolve()), "saxs", file_type="csv", import_order=1)

    snapshot = browser._batch_details_snapshot(batch_id)
    dialog = BatchDetailsDialog(
        snapshot["batch"]["label"],
        snapshot["files"],
        snapshot["runs"],
        browser,
    )

    opened = []
    monkeypatch.setattr("polynexus.gui.widgets.sample_browser.os.startfile", lambda path: opened.append(path))
    dialog._copy_file_paths()
    dialog._open_first_file_folder()

    assert dialog._copy_paths_button.text() == tr("SAMPLE_BATCH_DETAILS_COPY_PATHS")
    assert dialog._open_folder_button.text() == tr("SAMPLE_BATCH_DETAILS_OPEN_FOLDER")
    assert tr("SAMPLE_BATCH_DETAILS_COPY_PATHS_SELECTION_HINT") in dialog._copy_paths_button.toolTip()
    assert app.clipboard().text().splitlines() == [
        str(first_file.resolve()),
        str(second_file.resolve()),
    ]
    assert opened == [str(tmp_path)]

    dialog.deleteLater()
    db.close()
    browser.deleteLater()
    app.processEvents()


def test_batch_details_dialog_file_actions_follow_selected_row(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_dir.mkdir()
    second_dir.mkdir()
    first_file = first_dir / "sample_a.csv"
    second_file = second_dir / "sample_b.csv"
    first_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")
    second_file.write_text("q,I\n0.2,2.0\n", encoding="utf-8")

    browser = SampleBrowser()
    browser.set_db(db)
    batch_id, _ = browser.create_batch_with_file(
        sample_id,
        "annealed-01",
        "saxs",
        str(first_file),
    )
    db.add_data_file(batch_id, str(second_file.resolve()), "saxs", file_type="csv", import_order=1)

    snapshot = browser._batch_details_snapshot(batch_id)
    dialog = BatchDetailsDialog(
        snapshot["batch"]["label"],
        snapshot["files"],
        snapshot["runs"],
        browser,
    )

    dialog._files_table.selectRow(1)
    opened = []
    monkeypatch.setattr("polynexus.gui.widgets.sample_browser.os.startfile", lambda path: opened.append(path))
    dialog._copy_file_paths()
    dialog._open_first_file_folder()

    assert app.clipboard().text().splitlines() == [str(second_file.resolve())]
    assert opened == [str(second_dir)]

    dialog.deleteLater()
    db.close()
    browser.deleteLater()
    app.processEvents()


def test_batch_details_dialog_file_copy_shortcut_uses_selected_row(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_dir.mkdir()
    second_dir.mkdir()
    first_file = first_dir / "sample_a.csv"
    second_file = second_dir / "sample_b.csv"
    first_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")
    second_file.write_text("q,I\n0.2,2.0\n", encoding="utf-8")

    browser = SampleBrowser()
    browser.set_db(db)
    batch_id, _ = browser.create_batch_with_file(sample_id, "annealed-01", "saxs", str(first_file))
    db.add_data_file(batch_id, str(second_file.resolve()), "saxs", file_type="csv", import_order=1)

    snapshot = browser._batch_details_snapshot(batch_id)
    dialog = BatchDetailsDialog(snapshot["batch"]["label"], snapshot["files"], snapshot["runs"], browser)

    dialog._files_table.selectRow(1)
    dialog._copy_files_shortcut.activated.emit()

    assert app.clipboard().text().splitlines() == [str(second_file.resolve())]

    dialog.deleteLater()
    db.close()
    browser.deleteLater()
    app.processEvents()


def test_batch_details_dialog_file_row_double_click_opens_folder(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    file_dir = tmp_path / "files"
    file_dir.mkdir()
    data_file = file_dir / "sample_a.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    browser = SampleBrowser()
    browser.set_db(db)
    batch_id, _ = browser.create_batch_with_file(sample_id, "annealed-01", "saxs", str(data_file))

    snapshot = browser._batch_details_snapshot(batch_id)
    dialog = BatchDetailsDialog(snapshot["batch"]["label"], snapshot["files"], snapshot["runs"], browser)

    opened = []
    monkeypatch.setattr("polynexus.gui.widgets.sample_browser.os.startfile", lambda path: opened.append(path))
    dialog._on_files_table_double_clicked(dialog._files_table.item(0, 0))

    assert opened == [str(file_dir)]

    dialog.deleteLater()
    db.close()
    browser.deleteLater()
    app.processEvents()


def test_batch_details_dialog_file_row_activated_opens_folder(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    file_dir = tmp_path / "files"
    file_dir.mkdir()
    data_file = file_dir / "sample_a.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    browser = SampleBrowser()
    browser.set_db(db)
    batch_id, _ = browser.create_batch_with_file(sample_id, "annealed-01", "saxs", str(data_file))

    snapshot = browser._batch_details_snapshot(batch_id)
    dialog = BatchDetailsDialog(snapshot["batch"]["label"], snapshot["files"], snapshot["runs"], browser)

    opened = []
    monkeypatch.setattr("polynexus.gui.widgets.sample_browser.os.startfile", lambda path: opened.append(path))
    dialog._files_table.itemActivated.emit(dialog._files_table.item(0, 0))

    assert opened == [str(file_dir)]

    dialog.deleteLater()
    db.close()
    browser.deleteLater()
    app.processEvents()


def test_batch_details_dialog_exposes_output_directory_actions(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    data_file = tmp_path / "sample.csv"
    output_a = tmp_path / "output_a"
    output_b = tmp_path / "output_b"
    output_a.mkdir()
    output_b.mkdir()
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    browser = SampleBrowser()
    browser.set_db(db)
    batch_id, _ = browser.create_batch_with_file(
        sample_id,
        "annealed-01",
        "saxs",
        str(data_file),
    )
    db.create_analysis_run(
        batch_id,
        "saxs",
        submodule="saxs.static",
        output_dir=str(output_a),
        results_summary={"L_nm": 12.0},
    )
    db.create_analysis_run(
        batch_id,
        "saxs",
        submodule="saxs.static",
        output_dir=str(output_b),
        results_summary={"L_nm": 13.0},
    )

    snapshot = browser._batch_details_snapshot(batch_id)
    dialog = BatchDetailsDialog(
        snapshot["batch"]["label"],
        snapshot["files"],
        snapshot["runs"],
        browser,
    )

    opened = []
    monkeypatch.setattr("polynexus.gui.widgets.sample_browser.os.startfile", lambda path: opened.append(path))
    dialog._copy_output_dirs()
    dialog._open_selected_output_dir()

    expected_outputs = [
        str(run.get("output_dir", "") or "").strip()
        for run in snapshot["runs"]
        if str(run.get("output_dir", "") or "").strip()
    ]

    assert dialog._copy_outputs_button.text() == tr("SAMPLE_BATCH_DETAILS_COPY_OUTPUTS")
    assert dialog._open_output_button.text() == tr("SAMPLE_BATCH_DETAILS_OPEN_OUTPUT")
    assert tr("SAMPLE_BATCH_DETAILS_COPY_OUTPUTS_SELECTION_HINT") in dialog._copy_outputs_button.toolTip()
    assert app.clipboard().text().splitlines() == expected_outputs
    assert opened == [expected_outputs[0]]

    dialog.deleteLater()
    db.close()
    browser.deleteLater()
    app.processEvents()


def test_batch_details_dialog_output_actions_follow_selected_run(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    data_file = tmp_path / "sample.csv"
    output_a = tmp_path / "output_a"
    output_b = tmp_path / "output_b"
    output_a.mkdir()
    output_b.mkdir()
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    browser = SampleBrowser()
    browser.set_db(db)
    batch_id, _ = browser.create_batch_with_file(
        sample_id,
        "annealed-01",
        "saxs",
        str(data_file),
    )
    db.create_analysis_run(
        batch_id,
        "saxs",
        submodule="saxs.static",
        output_dir=str(output_a),
        results_summary={"L_nm": 12.0},
    )
    db.create_analysis_run(
        batch_id,
        "saxs",
        submodule="saxs.static",
        output_dir=str(output_b),
        results_summary={"L_nm": 13.0},
    )

    snapshot = browser._batch_details_snapshot(batch_id)
    dialog = BatchDetailsDialog(
        snapshot["batch"]["label"],
        snapshot["files"],
        snapshot["runs"],
        browser,
    )

    dialog._runs_table.selectRow(1)
    opened = []
    monkeypatch.setattr("polynexus.gui.widgets.sample_browser.os.startfile", lambda path: opened.append(path))
    dialog._copy_output_dirs()
    dialog._open_selected_output_dir()

    expected_output = str(snapshot["runs"][1].get("output_dir", "") or "").strip()
    assert app.clipboard().text().splitlines() == [expected_output]
    assert opened == [expected_output]

    dialog.deleteLater()
    db.close()
    browser.deleteLater()
    app.processEvents()


def test_batch_details_dialog_run_copy_shortcut_uses_selected_row(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    data_file = tmp_path / "sample.csv"
    output_a = tmp_path / "output_a"
    output_b = tmp_path / "output_b"
    output_a.mkdir()
    output_b.mkdir()
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    browser = SampleBrowser()
    browser.set_db(db)
    batch_id, _ = browser.create_batch_with_file(sample_id, "annealed-01", "saxs", str(data_file))
    db.create_analysis_run(batch_id, "saxs", submodule="saxs.static", output_dir=str(output_a), results_summary={"L_nm": 12.0})
    db.create_analysis_run(batch_id, "saxs", submodule="saxs.static", output_dir=str(output_b), results_summary={"L_nm": 13.0})

    snapshot = browser._batch_details_snapshot(batch_id)
    dialog = BatchDetailsDialog(snapshot["batch"]["label"], snapshot["files"], snapshot["runs"], browser)

    dialog._runs_table.selectRow(1)
    dialog._copy_runs_shortcut.activated.emit()

    assert app.clipboard().text().splitlines() == [str(output_b)]

    dialog.deleteLater()
    db.close()
    browser.deleteLater()
    app.processEvents()


def test_batch_details_dialog_run_row_double_click_opens_output_dir(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    data_file = tmp_path / "sample.csv"
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    browser = SampleBrowser()
    browser.set_db(db)
    batch_id, _ = browser.create_batch_with_file(sample_id, "annealed-01", "saxs", str(data_file))
    db.create_analysis_run(
        batch_id,
        "saxs",
        submodule="saxs.static",
        output_dir=str(output_dir),
        results_summary={"L_nm": 12.0},
    )

    snapshot = browser._batch_details_snapshot(batch_id)
    dialog = BatchDetailsDialog(snapshot["batch"]["label"], snapshot["files"], snapshot["runs"], browser)

    opened = []
    monkeypatch.setattr("polynexus.gui.widgets.sample_browser.os.startfile", lambda path: opened.append(path))
    dialog._on_runs_table_double_clicked(dialog._runs_table.item(0, 0))

    assert opened == [str(output_dir)]

    dialog.deleteLater()
    db.close()
    browser.deleteLater()
    app.processEvents()


def test_batch_details_dialog_run_row_activated_opens_output_dir(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    data_file = tmp_path / "sample.csv"
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    browser = SampleBrowser()
    browser.set_db(db)
    batch_id, _ = browser.create_batch_with_file(sample_id, "annealed-01", "saxs", str(data_file))
    db.create_analysis_run(
        batch_id,
        "saxs",
        submodule="saxs.static",
        output_dir=str(output_dir),
        results_summary={"L_nm": 12.0},
    )

    snapshot = browser._batch_details_snapshot(batch_id)
    dialog = BatchDetailsDialog(snapshot["batch"]["label"], snapshot["files"], snapshot["runs"], browser)

    opened = []
    monkeypatch.setattr("polynexus.gui.widgets.sample_browser.os.startfile", lambda path: opened.append(path))
    dialog._runs_table.itemActivated.emit(dialog._runs_table.item(0, 0))

    assert opened == [str(output_dir)]

    dialog.deleteLater()
    db.close()
    browser.deleteLater()
    app.processEvents()


def test_sample_browser_edit_batch_warning_uses_translated_detail(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        db = SampleDB(tmp_path / "samples.db")
        sample_id = db.create_sample("PA6")

        browser = SampleBrowser()
        browser.set_db(db)
        browser._selected_sample_id = sample_id
        browser._selected_batch_id = "batch-1"

        class AcceptedDialog:
            def exec(self):
                return 1

            def batch_label(self):
                return "annealed-01"

            def technique(self):
                return "saxs"

            def target_file_id(self):
                return None

            def replacement_file_path(self):
                return ""

            def should_remove_file(self):
                return False

        with patch("polynexus.gui.widgets.sample_browser.EditBatchDialog", return_value=AcceptedDialog()):
            with patch.object(
                browser,
                "_batch_details_snapshot",
                return_value={"batch": {"id": "batch-1", "label": "annealed-01"}, "files": [], "runs": []},
            ):
                with patch.object(browser, "update_batch_entry", side_effect=FileNotFoundError("missing.raw")):
                    with patch("polynexus.gui.widgets.sample_browser.QMessageBox.warning") as warning:
                        browser._on_edit_batch("batch-1")

        warning.assert_called_once_with(
            browser,
            tr("SAMPLE_BATCH_EDIT_TITLE"),
            tr("SAMPLE_BATCH_EDIT_FILE_MISSING", "missing.raw"),
        )

        db.close()
        browser.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_sample_browser_edit_sample_warning_uses_translated_detail(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        db = SampleDB(tmp_path / "samples.db")
        sample_id = db.create_sample("PA6")

        browser = SampleBrowser()
        browser.set_db(db)
        browser._selected_sample_id = sample_id

        class AcceptedDialog:
            def exec(self):
                return 1

            def sample_name(self):
                return "PA66"

            def aliases(self):
                return []

        with patch("polynexus.gui.widgets.sample_browser.EditSampleDialog", return_value=AcceptedDialog()):
            with patch.object(browser, "update_sample_entry", side_effect=ValueError("duplicate")):
                with patch("polynexus.gui.widgets.sample_browser.QMessageBox.warning") as warning:
                    browser._on_edit_sample()

        warning.assert_called_once_with(
            browser,
            tr("SAMPLE_EDIT_TITLE"),
            tr("SAMPLE_EDIT_INVALID", "duplicate"),
        )

        db.close()
        browser.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_sample_browser_new_sample_duplicate_clears_filters_before_selecting_existing(tmp_path):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    existing_id = db.create_sample("PA6")
    db.create_sample("PET")

    browser = SampleBrowser()
    browser.set_db(db)
    browser._search_input.setText("PET")
    assert browser._table.currentRow() == 0

    class AcceptedDialog:
        def exec(self):
            return 1

        def sample_name(self):
            return "PA6"

        def aliases(self):
            return []

    with patch("polynexus.gui.widgets.sample_browser.CreateSampleDialog", return_value=AcceptedDialog()):
        with patch("polynexus.gui.widgets.sample_browser.QMessageBox.warning"):
            browser._on_new_sample()

    assert browser._search_input.text() == ""
    assert browser._family_combo.currentIndex() == 0
    assert browser._selected_sample_id == existing_id
    assert browser._table.currentRow() in {0, 1}

    db.close()
    browser.deleteLater()
    app.processEvents()


def test_sample_browser_edit_batch_highlights_edited_entry(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    data_file = tmp_path / "sample.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    browser = SampleBrowser()
    browser.set_db(db)
    batch_id, _ = browser.create_batch_with_file(sample_id, "annealed-01", "saxs", str(data_file))
    assert browser.select_sample(sample_id)

    class AcceptedDialog:
        def exec(self):
            return 1

        def batch_label(self):
            return "annealed-02"

        def technique(self):
            return "saxs"

        def target_file_id(self):
            return None

        def replacement_file_path(self):
            return ""

        def should_remove_file(self):
            return False

    with patch("polynexus.gui.widgets.sample_browser.EditBatchDialog", return_value=AcceptedDialog()):
        browser._on_edit_batch(batch_id)

    assert browser._batch_list.count() == 1
    assert browser._batch_list.currentRow() == 0
    assert browser.get_selected_batch_ids() == [batch_id]
    assert db.get_batch(batch_id)["label"] == "annealed-02"

    db.close()
    browser.deleteLater()
    app.processEvents()


def test_sample_browser_batch_row_double_click_opens_details(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    data_file = tmp_path / "sample.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    browser = SampleBrowser()
    browser.set_db(db)
    batch_id, _ = browser.create_batch_with_file(sample_id, "annealed-01", "saxs", str(data_file))
    assert browser.select_sample(sample_id)

    opened = []
    monkeypatch.setattr(browser, "_on_view_batch_details", lambda current_batch_id: opened.append(current_batch_id))

    item = browser._batch_list.item(0)
    browser._on_batch_item_double_clicked(item)

    assert opened == [batch_id]

    db.close()
    browser.deleteLater()
    app.processEvents()


def test_sample_browser_batch_row_activated_opens_details(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    data_file = tmp_path / "sample.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    browser = SampleBrowser()
    browser.set_db(db)
    batch_id, _ = browser.create_batch_with_file(sample_id, "annealed-01", "saxs", str(data_file))
    assert browser.select_sample(sample_id)

    opened = []
    monkeypatch.setattr(browser, "_on_view_batch_details", lambda current_batch_id: opened.append(current_batch_id))

    item = browser._batch_list.item(0)
    browser._batch_list.itemActivated.emit(item)

    assert opened == [batch_id]

    db.close()
    browser.deleteLater()
    app.processEvents()


def test_sample_browser_sample_row_double_click_opens_edit_dialog(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")

    browser = SampleBrowser()
    browser.set_db(db)
    assert browser.select_sample(sample_id)

    edited = []
    monkeypatch.setattr(browser, "_on_edit_sample", lambda: edited.append("edit"))

    item = browser._table.item(0, 0)
    browser._on_table_item_double_clicked(item)

    assert edited == ["edit"]

    db.close()
    browser.deleteLater()
    app.processEvents()


def test_sample_browser_sample_row_activated_opens_edit_dialog(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")

    browser = SampleBrowser()
    browser.set_db(db)
    assert browser.select_sample(sample_id)

    edited = []
    monkeypatch.setattr(browser, "_on_edit_sample", lambda: edited.append("edit"))

    item = browser._table.item(0, 0)
    browser._table.itemActivated.emit(item)

    assert edited == ["edit"]

    db.close()
    browser.deleteLater()
    app.processEvents()


def test_sample_browser_new_batch_warning_uses_translated_detail(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        db = SampleDB(tmp_path / "samples.db")
        sample_id = db.create_sample("PA6")

        browser = SampleBrowser()
        browser.set_db(db)
        browser._selected_sample_id = sample_id

        class AcceptedDialog:
            def exec(self):
                return 1

            def batch_label(self):
                return "annealed-01"

            def technique(self):
                return "saxs"

            def file_path(self):
                return "missing.raw"

        with patch("polynexus.gui.widgets.sample_browser.CreateBatchDialog", return_value=AcceptedDialog()):
            with patch.object(browser, "create_batch_with_file", side_effect=FileNotFoundError("missing.raw")):
                with patch("polynexus.gui.widgets.sample_browser.QMessageBox.warning") as warning:
                    browser._on_new_batch()

        warning.assert_called_once_with(
            browser,
            tr("SAMPLE_BATCH_CREATE_TITLE"),
            tr("SAMPLE_BATCH_CREATE_FILE_MISSING_DETAIL", "missing.raw"),
        )

        db.close()
        browser.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_sample_browser_new_sample_propagates_unexpected_runtime_errors(tmp_path):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    browser = SampleBrowser()
    browser.set_db(db)

    class AcceptedDialog:
        def exec(self):
            return 1

        def sample_name(self):
            return "PA6"

        def aliases(self):
            return []

    try:
        with patch("polynexus.gui.widgets.sample_browser.CreateSampleDialog", return_value=AcceptedDialog()):
            with patch.object(browser._db, "create_sample", side_effect=RuntimeError("boom")):
                with patch("polynexus.gui.widgets.sample_browser.QMessageBox.critical"):
                    with pytest.raises(RuntimeError, match="boom"):
                        browser._on_new_sample()
    finally:
        db.close()
        browser.deleteLater()
        app.processEvents()


def test_sample_browser_hides_unfinished_export_entry():
    app = QApplication.instance() or QApplication([])

    browser = SampleBrowser()

    assert browser._btn_export.text() == tr("SAMPLE_EXPORT_MANIFEST")
    assert not browser._btn_export.isEnabled()

    browser.deleteLater()
    app.processEvents()


def test_sample_browser_select_all_button_switches_to_deselect_when_all_batches_checked(tmp_path):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    first_file = tmp_path / "sample_a.csv"
    second_file = tmp_path / "sample_b.csv"
    first_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")
    second_file.write_text("q,I\n0.2,2.0\n", encoding="utf-8")

    browser = SampleBrowser()
    browser.set_db(db)
    browser.create_batch_with_file(sample_id, "annealed-01", "saxs", str(first_file))
    browser.create_batch_with_file(sample_id, "annealed-02", "saxs", str(second_file))
    assert browser.select_sample(sample_id)

    assert browser._btn_select_all.text() == tr("SAMPLE_SELECT_ALL")

    browser._select_all_batches()

    assert browser._btn_select_all.text() == tr("SAMPLE_DESELECT_ALL")

    db.close()
    browser.deleteLater()
    app.processEvents()


def test_sample_browser_select_all_button_returns_to_select_all_when_any_batch_unchecked(tmp_path):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    first_file = tmp_path / "sample_a.csv"
    second_file = tmp_path / "sample_b.csv"
    first_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")
    second_file.write_text("q,I\n0.2,2.0\n", encoding="utf-8")

    browser = SampleBrowser()
    browser.set_db(db)
    browser.create_batch_with_file(sample_id, "annealed-01", "saxs", str(first_file))
    browser.create_batch_with_file(sample_id, "annealed-02", "saxs", str(second_file))
    assert browser.select_sample(sample_id)

    browser._select_all_batches()
    first_checkbox = next(iter(browser._batch_checkboxes.values()))
    first_checkbox.setChecked(False)

    assert browser._btn_select_all.text() == tr("SAMPLE_SELECT_ALL")

    db.close()
    browser.deleteLater()
    app.processEvents()


def test_sample_browser_export_writes_selected_sample_batches(tmp_path):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    data_file = tmp_path / "sample.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    browser = SampleBrowser()
    browser.set_db(db)
    batch_id, _ = browser.create_batch_with_file(
        sample_id,
        "annealed-01",
        "saxs",
        str(data_file),
    )
    db.create_analysis_run(
        batch_id,
        "saxs",
        submodule="saxs.static",
        results_summary={"L_nm": 12.0},
    )

    browser.refresh()
    assert browser.select_sample(sample_id)
    assert browser._btn_export.isEnabled()

    export_path = tmp_path / "sample_batches.tsv"
    with patch("polynexus.gui.widgets.sample_browser.QFileDialog.getSaveFileName", return_value=(str(export_path), "TSV (*.tsv)")):
        with patch("polynexus.gui.widgets.sample_browser.QMessageBox.information") as info:
            browser._on_export()

        text = export_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        assert lines[0] == "sample\tbatch\ttechnique\tfiles\truns\tstatus\tsource\tlatest"
        assert f"PA6\tannealed-01\tSAXS\t1\t1\t{tr('SAMPLE_BATCH_STATUS_ANALYZED', 1)}" in lines[1]
        assert tr("SAMPLE_BATCH_RECENT", "SAXS / saxs.static", tr("SAMPLE_RUN_STATUS_COMPLETED"), str(db.get_analysis_runs(batch_id)[0].get("created_at", ""))[:10] or "-") in lines[1]
        info.assert_called()

    db.close()
    browser.deleteLater()
    app.processEvents()


def test_sample_browser_export_remembers_last_export_directory(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    class FakeSettings:
        def __init__(self):
            self.data = {}

        def value(self, key, default=None, type=None):
            value = self.data.get(key, default)
            if type is str and value is not None:
                return str(value)
            return value

        def setValue(self, key, value):
            self.data[key] = value

    settings = FakeSettings()
    monkeypatch.setattr("polynexus.gui.widgets.sample_browser.QSettings", lambda org, app_name: settings)

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    data_file = tmp_path / "sample.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    first_export_dir = tmp_path / "exports_a"
    second_export_dir = tmp_path / "exports_b"
    first_export_dir.mkdir()
    second_export_dir.mkdir()

    browser = SampleBrowser()
    browser.set_db(db)
    browser.create_batch_with_file(sample_id, "annealed-01", "saxs", str(data_file))
    assert browser.select_sample(sample_id)

    seen = {}
    export_path = first_export_dir / "report.tsv"

    def first_save_dialog(parent, title, start_path, file_filter):
        seen["first_start_path"] = start_path
        return str(export_path), "TSV (*.tsv)"

    monkeypatch.setattr("polynexus.gui.widgets.sample_browser.QFileDialog.getSaveFileName", first_save_dialog)
    with patch("polynexus.gui.widgets.sample_browser.QMessageBox.information"):
        browser._on_export()

    assert Path(seen["first_start_path"]).parent == Path.home()
    assert settings.data["sample_browser/export_dir"] == str(first_export_dir.resolve())

    def second_save_dialog(parent, title, start_path, file_filter):
        seen["second_start_path"] = start_path
        return "", ""

    monkeypatch.setattr("polynexus.gui.widgets.sample_browser.QFileDialog.getSaveFileName", second_save_dialog)
    browser._save_last_export_dir(str(second_export_dir / "manual.tsv"))
    browser._on_export()

    assert Path(seen["second_start_path"]).parent == second_export_dir.resolve()

    db.close()
    browser.deleteLater()
    app.processEvents()


def test_sample_browser_export_uses_safe_default_filename_for_sample_name(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample('PA/6:Trial*Set? "A"')
    data_file = tmp_path / "sample.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    browser = SampleBrowser()
    browser.set_db(db)
    browser.create_batch_with_file(sample_id, "annealed-01", "saxs", str(data_file))
    assert browser.select_sample(sample_id)

    seen = {}

    def fake_save_dialog(parent, title, start_path, file_filter):
        seen["start_path"] = start_path
        return "", ""

    monkeypatch.setattr("polynexus.gui.widgets.sample_browser.QFileDialog.getSaveFileName", fake_save_dialog)
    browser._on_export()

    assert Path(seen["start_path"]).name == "PA_6_Trial_Set_A_batches.tsv"

    db.close()
    browser.deleteLater()
    app.processEvents()


def test_sample_browser_new_batch_highlights_created_entry(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    data_file = tmp_path / "sample.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    browser = SampleBrowser()
    browser.set_db(db)
    assert browser.select_sample(sample_id)

    class AcceptedDialog:
        def exec(self):
            return 1

        def batch_label(self):
            return "annealed-01"

        def technique(self):
            return "saxs"

        def file_path(self):
            return str(data_file)

    monkeypatch.setattr("polynexus.gui.widgets.sample_browser.CreateBatchDialog", lambda parent=None: AcceptedDialog())

    browser._on_new_batch()

    assert browser._batch_list.count() == 1
    assert browser._batch_list.currentRow() == 0
    assert browser._btn_joint.isEnabled()
    assert browser.get_selected_batch_ids() == [next(iter(browser._batch_checkboxes))]

    db.close()
    browser.deleteLater()
    app.processEvents()


def test_sample_browser_export_requires_selected_sample(tmp_path):
    app = QApplication.instance() or QApplication([])

    db = SampleDB(tmp_path / "samples.db")
    browser = SampleBrowser()
    browser.set_db(db)

    with patch("polynexus.gui.widgets.sample_browser.QMessageBox.warning") as warning:
        browser._on_export()

    warning.assert_called_once()
    assert tr("SAMPLE_EXPORT_NO_SAMPLE") == str(warning.call_args.args[2])

    db.close()
    browser.deleteLater()
    app.processEvents()
