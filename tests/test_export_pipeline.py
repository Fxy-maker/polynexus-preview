from __future__ import annotations

import pandas as pd

from polynexus.export import ExportRow, sci_export


def test_sci_export_keeps_saxs_status_fields_in_csv(tmp_path) -> None:
    original_to_markdown = pd.DataFrame.to_markdown
    pd.DataFrame.to_markdown = lambda self, index=False: self.to_string(index=index)  # type: ignore[assignment]
    try:
        rows = [
            ExportRow(
                sample_id="PA6",
                technique="saxs",
                submodule="saxs.temperature",
                condition_type="temperature",
                condition_value=195.0,
                quality_flag=2,
                quality_label="review",
                parameters={
                    "lc_nm": 1.23,
                    "lc_method": "raw",
                    "lc_reliability_status": "diagnostic_only",
                    "lc_reliability_reason": "low_lc_confidence|within_melting_window",
                    "melting_window_status": "within_window",
                    "melting_window_reason": "near_sequence_melting_onset",
                    "calibration_skipped_reason": "missing_reference_crystallinity",
                },
            )
        ]

        sci_export("saxs", rows, tmp_path)

        csv_path = tmp_path / "parameters" / "SAXS_Results_All.csv"
        report_path = tmp_path / "report" / "analysis_report.md"

        assert csv_path.exists()
        assert report_path.exists()

        csv_text = csv_path.read_text(encoding="utf-8")
        assert "lc_method" in csv_text
        assert "lc_reliability_status" in csv_text
        assert "calibration_skipped_reason" in csv_text
        assert "diagnostic_only" in csv_text
    finally:
        pd.DataFrame.to_markdown = original_to_markdown  # type: ignore[assignment]
