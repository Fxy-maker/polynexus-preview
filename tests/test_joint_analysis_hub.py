import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTableWidgetItem

from polynexus.gui.i18n import get_language, set_language
from polynexus.gui.widgets.joint_analysis_hub import JointAnalysisHub
from polynexus.core.joint.dataset import JointBatchRow, JointRunRecord


def test_joint_analysis_hub_refresh_does_not_select_rows(monkeypatch):
    app = QApplication.instance() or QApplication([])
    rows = [
        JointBatchRow(
            sample_id="sample-1",
            sample_name="PA6",
            family="PA6",
            batch_id="batch-1",
            batch_label="batch-1",
            runs={"dsc": JointRunRecord(run_id="run-1", technique="dsc")},
        ),
        JointBatchRow(
            sample_id="sample-1",
            sample_name="PA6",
            family="PA6",
            batch_id="batch-2",
            batch_label="batch-2",
            runs={
                "dsc": JointRunRecord(run_id="run-2", technique="dsc"),
                "saxs": JointRunRecord(run_id="run-3", technique="saxs"),
            },
        ),
    ]
    monkeypatch.setattr(
        "polynexus.gui.widgets.joint_analysis_hub.collect_joint_dataset",
        lambda *_args, **_kwargs: rows,
    )

    hub = JointAnalysisHub()
    hub.set_db(object())

    assert hub.selected_rows() == []
    hub._select_recommended()
    assert hub.selected_batch_ids() == ["batch-2"]
    hub.deleteLater()
    app.processEvents()


def test_joint_analysis_hub_copy_button_copies_selected_row():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        hub = JointAnalysisHub()
        hub._table.setRowCount(1)
        hub._table.setItem(0, 1, QTableWidgetItem("PA6"))
        hub._table.setItem(0, 2, QTableWidgetItem("batch-01"))
        hub._table.setItem(0, 3, QTableWidgetItem("annealed"))
        hub._table.setItem(0, 4, QTableWidgetItem("yes"))
        hub._table.setItem(0, 5, QTableWidgetItem("no"))
        hub._table.setItem(0, 6, QTableWidgetItem("yes"))
        hub._table.setItem(0, 7, QTableWidgetItem("-"))
        hub._table.setItem(0, 8, QTableWidgetItem("no"))
        hub._table.setItem(0, 9, QTableWidgetItem("DSC; SAXS"))

        hub._table.selectRow(0)
        hub._update_summary()
        app.processEvents()
        assert hub._btn_copy.isEnabled()
        hub._btn_copy.click()

        lines = QApplication.clipboard().text().splitlines()
        assert lines[0] == "Sample\tBatch\tCondition\tDSC\tSAXS\tWAXS\tIR\tNMR\tAvailable joint analysis"
        assert lines[1] == "PA6\tbatch-01\tannealed\tyes\tno\tyes\t-\tno\tDSC; SAXS"
        assert len(lines) == 2

        hub.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)
