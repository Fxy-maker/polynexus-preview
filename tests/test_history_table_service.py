from pathlib import Path

from polynexus.gui.history_table_service import build_history_table_rows
from polynexus.gui.history_table_service import write_history_export_table


def test_build_history_table_rows_populates_display_values_and_tooltips():
    rows = build_history_table_rows(
        [
            {
                "created_at": "2026-07-09 01:02:03",
                "technique": "saxs",
                "submodule": "saxs.static",
                "results_summary": {"r2": 0.9123},
                "status": "completed",
            }
        ],
        metrics_tooltip_fn=lambda run: "file=foo | L_nm=12.3",
        technique_text_fn=lambda technique: technique.upper(),
        submodule_text_fn=lambda submodule: submodule.replace(".", " / "),
        status_text_fn=lambda run: "Completed | AI rerun",
        validation_summary_fn=lambda run: "All checks passed",
        confirmation_label_fn=lambda run: "Confirmed",
        has_source_fn=lambda run: False,
    )

    assert len(rows) == 1
    row = rows[0]
    assert row.values == [
        "2026-07-09 01:02",
        "SAXS",
        "saxs / static",
        "0.9123",
        "Completed | AI rerun",
        "Scientific review: Not applicable | reason=not_applicable",
        "All checks passed",
        "Confirmed",
    ]
    assert row.tooltips == [
        "file=foo | L_nm=12.3",
        "saxs",
        "saxs.static",
        "file=foo | L_nm=12.3",
        "Completed | AI rerun | file=foo | L_nm=12.3",
        "Scientific review: Not applicable | reason=not_applicable",
        "All checks passed",
        "Confirmed",
    ]


def test_build_history_table_rows_shows_review_state_for_solid_c():
    rows = build_history_table_rows(
        [
            {
                "technique": "nmr",
                "submodule": "nmr.solid_c",
                "results_summary": {
                    "result": {
                        "analysis_evidence": {
                            "scientific_review": {
                                "allowed": False,
                                "reason": "review_missing",
                                "record_id": "",
                                "scope": "nmr.solid_c",
                            }
                        }
                    }
                },
            }
        ],
        metrics_tooltip_fn=lambda run: "",
        technique_text_fn=lambda technique: technique.upper(),
        submodule_text_fn=lambda submodule: submodule,
        status_text_fn=lambda run: "Completed",
        validation_summary_fn=lambda run: "",
        confirmation_label_fn=lambda run: "Pending",
        has_source_fn=lambda run: True,
    )

    assert rows[0].values[5].startswith("Scientific review:")
    assert "review_missing" in rows[0].tooltips[5]


def test_write_history_export_table_defaults_to_tsv(tmp_path):
    output_path = write_history_export_table(
        tmp_path / "history",
        ["Time", "Technique"],
        [["2026-07-09 01:02", "SAXS"]],
    )

    assert output_path == str(tmp_path / "history.tsv")
    assert Path(output_path).read_text(encoding="utf-8").splitlines() == [
        "Time\tTechnique",
        "2026-07-09 01:02\tSAXS",
    ]


def test_write_history_export_table_uses_csv_when_filter_mentions_csv(tmp_path):
    output_path = write_history_export_table(
        tmp_path / "history_export",
        ["Time", "Technique"],
        [["2026-07-09 01:02", "SAXS"]],
        selected_filter="CSV (*.csv)",
    )

    assert output_path == str(tmp_path / "history_export.csv")
    assert Path(output_path).read_text(encoding="utf-8").splitlines() == [
        "Time,Technique",
        "2026-07-09 01:02,SAXS",
    ]
