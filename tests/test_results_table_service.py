import copy
import logging

import pytest

from polynexus.gui.analysis_history_service import flatten_params as flatten_history_params
from polynexus.gui.i18n import get_language, set_language, tr
from polynexus.gui import results_table_service
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


def test_structured_results_model_carries_scientific_review_from_live_result():
    model = _build(
        {"map_shape": [2, 2], "valid_pixel_ratio": 1.0},
        technique="ir",
        submodule="ir.mapping",
        review_source={
            "analysis_evidence": {
                "feature_evidence": {
                    "mapping_evidence": {
                        "scientific_review": {
                            "allowed": True,
                            "reason": "review_accepted",
                            "record_id": "review-ir-map-1",
                            "scope": "ir.mapping",
                            "source_ref": "map-a.json",
                        }
                    }
                }
            }
        },
    )

    assert model.scientific_review.status == "accepted"
    assert "review-ir-map-1" in model.scientific_review.text


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


def _build(params, **context):
    return build_results_table_model(
        params,
        ordered_columns_fn=lambda columns: list(columns),
        flatten_params_fn=flatten_history_params,
        **context,
    )


def test_saxs_static_dispatch_preserves_structured_sections_and_raw_values():
    model = _build(
        {
            "file": "sample.dat",
            "L_nm": 12.345,
            "lc_nm": 3.25,
            "la_nm": 9.095,
            "Xc": 0.3125,
            "lc_method": "raw",
            "lc_reliability_status": "usable",
            "future_scalar": 7.5,
            "condition_confidence": 0.84,
        },
        technique="saxs",
        language="en",
    )

    assert model.kind == "saxs.static"
    assert model.summary_kind == "single"
    assert model.columns == [
        "File",
        "Long period / nm",
        "Effective lc / nm",
        "Amorphous layer / nm",
        "Crystal fraction",
        "Value source",
        "Reliability",
    ]
    assert model.display_rows == [
        ["sample.dat", "12.35", "3.25", "9.10", "0.312", "raw", "usable"]
    ]
    assert model.stored_rows == [
        ["sample.dat", 12.345, 3.25, 9.095, 0.3125, "raw", "usable"]
    ]
    assert tuple(metric.key for metric in model.hero_metrics) == ("L_nm", "lc_nm", "la_nm", "phi_c")
    assert model.primary_section.rows[0][1].raw == 12.345
    assert tuple(column.key for column in model.detail_section.columns)[-1] == "condition_confidence"
    assert model.detail_section.rows[0][-2].raw == 7.5
    assert "condition_confidence" in {column.key for column in model.diagnostic_section.columns}
    assert model.risk_text == ""
    assert model.next_text == ""
    assert (model.summary_count, model.copy_enabled, model.export_enabled, model.sortable) == (1, True, True, False)


def test_saxs_temperature_dispatch_qualifies_submodule_and_classifies_sequence_as_batch():
    model = _build(
        {
            "batch_frames": 2,
            "condition_confidence": 0.91,
            "_batch_data": [
                {
                    "temperature_C": 180.0,
                    "stage": "heating",
                    "L_nm": 12.2,
                    "lc_nm": 3.1,
                    "lc_method": "calibrated",
                    "melting_window_status": "near_onset",
                    "lc_reliability_status": "low_confidence",
                },
                {
                    "temperature_C": 190.0,
                    "stage": "heating",
                    "L_nm": 11.8,
                    "lc_nm": 3.0,
                    "lc_method": "raw",
                    "melting_window_status": "within_window",
                    "lc_reliability_status": "usable",
                },
            ],
        },
        technique="  SAXS  ",
        submodule="temperature",
        language="en",
    )

    assert model.kind == "saxs.temperature"
    assert model.summary_kind == "batch"
    assert model.columns == [
        "Temperature / \N{DEGREE SIGN}C",
        "Stage",
        "Long period / nm",
        "Effective lc / nm",
        "Value source",
        "Melting window",
        "Reliability",
    ]
    assert model.stored_rows[0] == [
        180.0,
        "heating",
        12.2,
        3.1,
        "calibrated",
        "near_onset",
        "low_confidence",
    ]
    assert len(model.detail_section.rows) == 3
    assert "row_scope" in {column.key for column in model.diagnostic_section.columns}
    assert tuple(metric.key for metric in model.hero_metrics) == ("L_nm", "lc_nm", "condition_confidence")
    assert (model.summary_count, model.sortable) == (2, True)


def test_saxs_strain_dispatch_uses_exact_qualified_template_columns():
    model = _build(
        {
            "Q_star_rel_mean": 1.02,
            "phi_void_mean": 0.04,
            "f_Herman_mean": 0.2,
            "f_Herman_raw_mean": 0.3,
            "phase_support_mean": 0.82,
            "_batch_data": [
                {
                    "condition_value": 8.0,
                    "Q_rel": 1.025,
                    "phi_void": 0.04,
                    "f_Herman": 0.2,
                    "f_Herman_raw": 0.3,
                    "strain_phase": "plastic_voiding",
                    "phase_support_score": 0.82,
                    "strain_reliability_status": "passed",
                }
            ],
        },
        technique="saxs",
        submodule="saxs.strain",
        language="en",
    )

    assert model.kind == "saxs.strain"
    assert model.summary_kind == "batch"
    assert model.columns == [
        "Strain / %",
        "Herman orientation",
        "Herman orientation (diagnostic)",
        "Herman delta from zero",
        "Herman delta stability lower",
        "Herman delta stability upper",
        "Orientation q minimum / nm^-1",
        "Orientation q maximum / nm^-1",
        "Orientation track",
        "Orientation reliability",
        "Orientation reasons",
        "Structure stage",
        "Phase support",
        "Reliability",
    ]
    assert model.stored_rows == [
        [8.0, 0.2, 0.3, None, None, None, None, None, None, None, None, "plastic_voiding", 0.82, "passed"]
    ]
    assert tuple(metric.raw for metric in model.hero_metrics) == (0.2, 0.3, 0.82)


def test_saxs_batch_frame_count_preserves_batch_summary_shape_without_sequence_rows():
    model = _build(
        {"batch_frames": 3, "L_nm": 12.0},
        technique="saxs",
        submodule="static",
    )

    assert model.kind == "saxs.static"
    assert model.summary_kind == "batch"
    assert model.summary_count == 1


@pytest.mark.parametrize("params", [{}, None])
def test_saxs_empty_params_build_empty_static_presentation(params):
    model = _build(params, technique="saxs")

    assert model.kind == "saxs.static"
    assert model.summary_kind == "single"
    assert model.columns == []
    assert model.display_rows == []
    assert model.stored_rows == []
    assert model.primary_section.rows == ()
    assert model.detail_section.rows == ()
    assert model.diagnostic_section.rows == ()
    assert model.hero_metrics == ()
    assert (model.summary_count, model.copy_enabled, model.export_enabled, model.sortable) == (0, False, False, False)


def test_saxs_multi_sample_payload_keeps_generic_compatibility_path():
    model = _build(
        {
            "sample-a": {"L_nm": 12.0, "label": "A"},
            "sample-b": {"label": "B", "Xc": 0.31},
        },
        technique="saxs",
        submodule="saxs.static",
    )

    assert model.kind == "multi_sample"
    assert model.summary_kind == "multi_sample"
    assert model.columns == ["sample", "L_nm", "label", "Xc"]
    assert model.display_rows == [
        ["sample-a", "12.00", "A", ""],
        ["sample-b", "", "B", "0.31"],
    ]
    assert model.stored_rows == [
        ["sample-a", 12.0, "A", ""],
        ["sample-b", "", "B", 0.31],
    ]
    assert model.hero_metrics == ()


def test_non_saxs_context_is_equivalent_to_legacy_generic_model():
    params = {"L_nm": 12.0, "Xc": 0.31, "batch_frames": 1, "_private": 9}

    legacy = _build(params)
    contextual = _build(params, technique="waxs", submodule="waxs.peak_fit", language="zh")

    assert contextual == legacy
    assert contextual.kind == "single"
    assert contextual.summary_kind == "single"


def test_generic_batch_builders_set_batch_summary_kind():
    embedded = _build(
        {
            "batch_frames": 2,
            "_batch_data": [{"file": "a.dat"}, {"file": "b.dat"}],
        }
    )
    explicit = build_batch_results_table_model(
        [{"file": "a.dat", "params": {}}, {"file": "b.dat", "params": {}}],
        ordered_columns_fn=lambda columns: list(columns),
    )

    assert embedded.summary_kind == "batch"
    assert explicit.summary_kind == "batch"


def test_saxs_adapter_failure_logs_warning_and_falls_back_without_mutation(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    params = {"L_nm": 12.0, "Xc": 0.31, "batch_frames": 1, "_private": 9}
    before = copy.deepcopy(params)

    def fail(*_args, **_kwargs):
        raise RuntimeError("sentinel structured adapter failure")

    monkeypatch.setattr(results_table_service, "build_saxs_results_presentation", fail)
    with caplog.at_level(logging.WARNING, logger=results_table_service.__name__):
        model = _build(params, technique="saxs", submodule="saxs.static")

    assert model.kind == "single"
    assert model.summary_kind == "single"
    assert model.columns == [tr("RESULTS_PARAM"), tr("RESULTS_VALUE")]
    assert model.display_rows == [["L_nm", "12.0000"], ["Xc", "0.3100"]]
    assert model.stored_rows == [["L_nm", 12.0], ["Xc", 0.31]]
    assert params == before
    assert "SAXS structured results presentation failed" in caplog.text
    assert "sentinel structured adapter failure" in caplog.text


@pytest.mark.parametrize(
    ("technique", "submodule", "params", "kind", "first_key"),
    [
        ("dsc", "dsc.standard", {"scan": "s1", "Tg_C": 70.0}, "dsc.standard", "scan"),
        ("ir", "ir.standard", {"sample": "p1", "match_score": 0.9}, "ir.standard", "sample"),
        ("waxs", "waxs.static", {"sample": "p1", "Xc_pct": 0.4}, "waxs.static", "sample"),
        ("nmr", "nmr.liquid_h", {"spectrum": "s1", "nucleus": "1H"}, "nmr.liquid_h", "spectrum"),
    ],
)
def test_supported_non_saxs_dispatch_builds_structured_model(
    technique, submodule, params, kind, first_key
):
    model = _build(params, technique=technique, submodule=submodule, language="en")

    assert model.kind == kind
    assert model.primary_section is not None
    assert model.detail_section is not None
    assert model.diagnostic_section is not None
    assert model.columns[0] == model.primary_section.columns[0].header
    assert model.primary_section.columns[0].key == first_key
    assert model.stored_rows[0][0] == params[first_key]
    assert model.summary_kind == "single"


def test_non_saxs_batch_dispatch_preserves_batch_summary_kind_and_raw_values():
    model = _build(
        {
            "batch_frames": 2,
            "Tm_peak_C": 171.0,
            "_batch_data": [
                {"scan": "a", "Tm_peak_C": 169.0},
                {"scan": "b", "Tm_peak_C": 173.0},
            ],
        },
        technique="dsc",
        submodule="dsc.standard",
    )

    assert model.kind == "dsc.standard"
    assert model.summary_kind == "batch"
    assert model.summary_count == 2
    assert model.stored_rows == [
        ["a", None, 169.0, None, None, None, None, None],
        ["b", None, 173.0, None, None, None, None, None],
    ]
    assert len(model.detail_section.rows) == 3


def test_dict_of_dicts_stays_on_existing_multi_sample_path_for_non_saxs():
    model = _build(
        {"sample-a": {"sample": "a"}, "sample-b": {"sample": "b"}},
        technique="nmr",
        submodule="nmr.solid_c",
    )

    assert model.kind == "multi_sample"
    assert model.primary_section is None
    assert model.summary_kind == "multi_sample"


def test_unknown_non_saxs_submodule_keeps_generic_compatibility_path():
    params = {"L_nm": 12.0, "Xc": 0.31, "batch_frames": 1, "_private": 9}
    model = _build(params, technique="waxs", submodule="waxs.peak_fit", language="zh")

    assert model.kind == "single"
    assert model.primary_section is None
    assert model.columns == [tr("RESULTS_PARAM"), tr("RESULTS_VALUE")]
    assert model.stored_rows == [["L_nm", 12.0], ["Xc", 0.31]]


def test_non_saxs_adapter_failure_logs_warning_and_falls_back(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    def fail(*_args, **_kwargs):
        raise RuntimeError("sentinel analysis adapter failure")

    monkeypatch.setattr(results_table_service, "build_analysis_results_presentation", fail)
    with caplog.at_level(logging.WARNING, logger=results_table_service.__name__):
        model = _build(
            {"sample": "p1", "match_score": 0.9},
            technique="ir",
            submodule="ir.standard",
        )

    assert model.kind == "single"
    assert model.primary_section is None
    assert model.stored_rows == [["sample", "p1"], ["match_score", 0.9]]
    assert "analysis results presentation failed" in caplog.text.lower()
    assert "sentinel analysis adapter failure" in caplog.text
