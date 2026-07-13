from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from polynexus.gui.table_export_service import TableExportData, write_table_export, write_table_export_bundle


def test_write_table_export_defaults_to_tsv_and_honors_csv_filter(tmp_path):
    tsv = write_table_export(tmp_path / "results", ["Parameter", "Value"], [["L_nm", "12.0000"]])
    csv_path = write_table_export(
        tmp_path / "results_export", ["Parameter", "Value"], [["L_nm", "12.0000"]], selected_filter="CSV (*.csv)"
    )

    assert Path(tsv).read_text(encoding="utf-8").splitlines() == ["Parameter\tValue", "L_nm\t12.0000"]
    assert Path(csv_path).read_text(encoding="utf-8").splitlines() == ["Parameter,Value", "L_nm,12.0000"]


def test_table_export_bundle_writes_summary_full_and_optional_diagnostics(tmp_path):
    paths = write_table_export_bundle(
        tmp_path / "results.csv",
        summary=TableExportData(headers=("Metric", "Value"), rows=(("Mean", 12.5),)),
        full=TableExportData(headers=("Index", "Value"), rows=((1, 12.5),)),
        diagnostics=TableExportData(headers=("Level", "Message"), rows=(("warning", "Check input"),)),
    )

    assert [Path(path).name for path in paths] == ["results_summary.csv", "results_full.csv", "results_diagnostics.csv"]
    assert Path(paths[0]).read_text(encoding="utf-8").splitlines() == ["Metric,Value", "Mean,12.5"]


def test_table_export_data_is_immutable_and_invalid_bundle_does_not_overwrite(tmp_path):
    data = TableExportData(headers=("Metric",), rows=(("Mean", 1),))
    with pytest.raises(FrozenInstanceError):
        data.headers = ("Changed",)

    existing = tmp_path / "results_summary.csv"
    existing.write_text("keep", encoding="utf-8")
    paths = write_table_export_bundle(
        tmp_path / "results.csv",
        summary=TableExportData(headers=(), rows=()),
        full=TableExportData(headers=("Index",), rows=((1,),)),
        diagnostics=None,
    )

    assert paths == []
    assert existing.read_text(encoding="utf-8") == "keep"
