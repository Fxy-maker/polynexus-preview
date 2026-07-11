from polynexus.gui.analysis_history_service import flatten_params as flatten_history_params
from polynexus.gui.i18n import get_language, set_language, tr
from polynexus.gui.results_table_service import build_batch_results_table_model, build_results_table_model


def test_build_results_table_model_handles_multi_sample_tables():
    previous = get_language()
    set_language("en")
    try:
        model = build_results_table_model(
            {
                "sample-a": {"L_nm": 12.0, "label": "A"},
                "sample-b": {"label": "B", "Xc": 0.31},
            },
            ordered_columns_fn=lambda columns: list(columns),
            flatten_params_fn=flatten_history_params,
        )

        assert model.kind == "multi_sample"
        assert model.columns == ["sample", "L_nm", "label", "Xc"]
        assert model.display_rows == [
            ["sample-a", "12.00", "A", ""],
            ["sample-b", "", "B", "0.31"],
        ]
        assert model.stored_rows == [
            ["sample-a", 12.0, "A", ""],
            ["sample-b", "", "B", 0.31],
        ]
        assert model.summary_count == 2
        assert model.copy_enabled is True
        assert model.export_enabled is True
        assert model.sortable is True
    finally:
        set_language(previous)


def test_build_results_table_model_handles_batch_tables():
    previous = get_language()
    set_language("en")
    try:
        model = build_results_table_model(
            {
                "batch_frames": 3,
                "_batch_data": [
                    {"file": "frame_001.edf", "L_nm": 2.5, "Xc": 0.31},
                    {"file": "frame_002.edf", "lc_nm": 3.0, "extra": "ok"},
                ],
            },
            ordered_columns_fn=lambda columns: list(columns),
            flatten_params_fn=flatten_history_params,
        )

        assert model.kind == "batch"
        assert model.columns == ["file", "L_nm", "Xc", "lc_nm", "extra"]
        assert model.display_rows == [
            ["frame_001.edf", "2.500", "0.310", "", ""],
            ["frame_002.edf", "", "", "3.000", "ok"],
        ]
        assert model.stored_rows == [
            ["frame_001.edf", 2.5, 0.31, "", ""],
            ["frame_002.edf", "", "", 3.0, "ok"],
        ]
        assert model.summary_count == 2
        assert model.copy_enabled is True
        assert model.export_enabled is True
        assert model.sortable is True
    finally:
        set_language(previous)


def test_build_results_table_model_handles_single_tables():
    previous = get_language()
    set_language("en")
    try:
        model = build_results_table_model(
            {"L_nm": 12.0, "Xc": 0.31, "batch_frames": 1, "_private": 9},
            ordered_columns_fn=lambda columns: list(columns),
            flatten_params_fn=flatten_history_params,
        )

        assert model.kind == "single"
        assert model.columns == [tr("RESULTS_PARAM"), tr("RESULTS_VALUE")]
        assert model.display_rows == [["L_nm", "12.0000"], ["Xc", "0.3100"]]
        assert model.stored_rows == [["L_nm", 12.0], ["Xc", 0.31]]
        assert model.summary_count == 2
        assert model.copy_enabled is True
        assert model.export_enabled is True
        assert model.sortable is False
    finally:
        set_language(previous)


def test_build_batch_results_table_model_flattens_nested_params_and_keeps_file_first():
    previous = get_language()
    set_language("en")
    try:
        model = build_batch_results_table_model(
            [
                {"file": "a.csv", "params": {"custom_note": "annealed", "Xc_pct": 43.5, "L_nm": 12.3}},
                {"file": "b.csv", "params": {"custom_note": "quenched", "Xc_pct": 39.2, "lc_nm": 10.8}},
            ],
            ordered_columns_fn=lambda columns: list(columns),
        )

        assert model.kind == "batch"
        assert model.columns == ["file", "custom_note", "Xc_pct", "L_nm", "lc_nm"]
        assert model.display_rows == [
            ["a.csv", "annealed", "43.5000", "12.3000", ""],
            ["b.csv", "quenched", "39.2000", "", "10.8000"],
        ]
        assert model.stored_rows == [
            ["a.csv", "annealed", 43.5, 12.3, ""],
            ["b.csv", "quenched", 39.2, "", 10.8],
        ]
        assert model.summary_count == 2
        assert model.copy_enabled is True
        assert model.export_enabled is True
        assert model.sortable is True
    finally:
        set_language(previous)
