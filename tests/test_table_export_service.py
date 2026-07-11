from pathlib import Path

from polynexus.gui.table_export_service import write_table_export


def test_write_table_export_defaults_to_tsv(tmp_path):
    output_path = write_table_export(
        tmp_path / "results_table",
        ["Parameter", "Value"],
        [["L_nm", "12.0000"]],
    )

    assert output_path == str(tmp_path / "results_table.tsv")
    assert Path(output_path).read_text(encoding="utf-8").splitlines() == [
        "Parameter\tValue",
        "L_nm\t12.0000",
    ]


def test_write_table_export_uses_csv_when_filter_mentions_csv(tmp_path):
    output_path = write_table_export(
        tmp_path / "results_table_export",
        ["Parameter", "Value"],
        [["L_nm", "12.0000"]],
        selected_filter="CSV (*.csv)",
    )

    assert output_path == str(tmp_path / "results_table_export.csv")
    assert Path(output_path).read_text(encoding="utf-8").splitlines() == [
        "Parameter,Value",
        "L_nm,12.0000",
    ]
