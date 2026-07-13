from __future__ import annotations

import copy
import importlib
import importlib.util
import json

import numpy as np
import pytest

from polynexus.gui import i18n
from polynexus.gui.i18n import get_language, set_language


@pytest.fixture(autouse=True)
def _restore_language() -> None:
    previous = get_language()
    try:
        yield
    finally:
        set_language(previous)


def _build(params, *, submodule: str = "saxs.static", language: str = "en"):
    module_name = "polynexus.gui.saxs_results_table_service"
    assert importlib.util.find_spec(module_name) is not None, "SAXS presentation adapter is missing"
    module = importlib.import_module(module_name)
    return module.build_saxs_results_presentation(
        params,
        submodule=submodule,
        language=language,
    )


def _service_module():
    return importlib.import_module("polynexus.gui.saxs_results_table_service")


def _column_index(section, key: str) -> int:
    return next(index for index, column in enumerate(section.columns) if column.key == key)


def _cell(section, row: int, key: str):
    return section.rows[row][_column_index(section, key)]


def test_temperature_primary_uses_effective_lc_source_status_and_unavailable_text() -> None:
    presentation = _build(
        {
            "_batch_data": [
                {
                    "temperature_C": 185.0,
                    "stage": "heating",
                    "L_nm": 11.234,
                    "lc_nm": 4.126,
                    "lc_nm_raw": 3.25,
                    "lc_nm_calibrated": 4.126,
                    "lc_method": "calibrated",
                    "melting_window_status": "near_onset",
                    "lc_reliability_status": "low_confidence",
                },
                {
                    "temperature_C": 205.0,
                    "L_nm": np.inf,
                    "lc_nm": 2.0,
                    "lc_method": "raw",
                    "melting_window_status": "post_end",
                    "lc_reliability_status": "diagnostic_only",
                },
            ]
        },
        submodule="saxs.temperature",
    )

    assert presentation.kind == "saxs.temperature"
    assert tuple(column.key for column in presentation.primary.columns) == (
        "temperature_C",
        "stage",
        "L_nm",
        "lc_nm",
        "lc_method",
        "melting_window_status",
        "lc_reliability_status",
    )
    assert presentation.primary.columns[0].label == "Temperature"
    assert presentation.primary.columns[0].unit == "\N{DEGREE SIGN}C"
    assert presentation.primary.columns[0].digits == 1
    assert presentation.primary.columns[0].alignment == "right"

    lc = _cell(presentation.primary, 0, "lc_nm")
    assert lc.raw == 4.126
    assert lc.display == "4.13"
    assert lc.provenance == "calibrated"
    assert lc.status == "review"
    assert _cell(presentation.primary, 0, "lc_method").display == "calibrated"
    assert _cell(presentation.primary, 0, "melting_window_status").display == "near onset"
    assert _cell(presentation.primary, 0, "lc_reliability_status").display == "low-confidence"
    assert _cell(presentation.primary, 1, "L_nm").display == "Unavailable"
    assert _cell(presentation.primary, 1, "melting_window_status").status == "blocked"


def test_static_primary_is_exact_and_detail_keeps_raw_calibrated_and_future_scalars() -> None:
    presentation = _build(
        {
            "file": "sample.dat",
            "L_nm": 12.0,
            "lc_nm_calibrated": 3.75,
            "lc_nm_raw": 3.25,
            "la_nm": 8.25,
            "Xc": 0.3125,
            "lc_method": "qstar_calibrated",
            "lc_reliability_status": "calibrated",
            "future_scalar": "kept",
            "_private": "hidden",
        }
    )

    assert tuple(column.key for column in presentation.primary.columns) == (
        "file",
        "L_nm",
        "lc_nm",
        "la_nm",
        "phi_c",
        "lc_method",
        "lc_reliability_status",
    )
    assert _cell(presentation.primary, 0, "lc_nm").raw == 3.75
    assert _cell(presentation.primary, 0, "phi_c").raw == 0.3125
    assert tuple(column.key for column in presentation.detail.columns) == (
        "file",
        "L_nm",
        "lc_nm_calibrated",
        "lc_nm_raw",
        "la_nm",
        "Xc",
        "lc_method",
        "lc_reliability_status",
        "future_scalar",
    )
    assert _cell(presentation.detail, 0, "lc_nm_raw").raw == 3.25
    assert _cell(presentation.detail, 0, "lc_nm_calibrated").raw == 3.75
    assert _cell(presentation.detail, 0, "future_scalar").display == "kept"


def test_strain_primary_contains_only_strain_template_columns() -> None:
    presentation = _build(
        {
            "_batch_data": [
                {
                    "condition_value": 8.0,
                    "Q_rel": 1.025,
                    "phi_void": 0.04,
                    "f_Herman": 0.2,
                    "strain_phase": "plastic_voiding",
                    "phase_support_score": 0.82,
                    "strain_reliability_status": "passed",
                    "temperature_C": 190.0,
                }
            ]
        },
        submodule="saxs.strain",
    )

    assert tuple(column.key for column in presentation.primary.columns) == (
        "strain_pct",
        "Q_star_rel",
        "phi_void",
        "f_Herman",
        "phase_name",
        "phase_support_score",
        "strain_reliability_status",
    )
    assert _cell(presentation.primary, 0, "strain_pct").raw == 8.0
    assert _cell(presentation.primary, 0, "Q_star_rel").raw == 1.025
    assert _cell(presentation.primary, 0, "phase_name").raw == "plastic_voiding"
    assert _cell(presentation.primary, 0, "strain_reliability_status").status == "reliable"
    assert "temperature_C" not in {column.key for column in presentation.primary.columns}


def test_empty_payload_builds_empty_sections_and_disabled_actions() -> None:
    presentation = _build({}, submodule="saxs.temperature")

    assert presentation.kind == "saxs.temperature"
    assert presentation.primary.rows == ()
    assert presentation.detail.rows == ()
    assert presentation.diagnostics.rows == ()
    assert presentation.hero_metrics == ()
    assert presentation.summary_count == 0
    assert presentation.sortable is False
    assert presentation.copy_enabled is False
    assert presentation.export_enabled is False


def test_detail_union_is_first_seen_and_nested_values_are_deterministic_diagnostics() -> None:
    nested = {"\u5907\u6ce8": [2, 1], "alpha": {"z": True}}
    presentation = _build(
        {
            "_batch_data": [
                {"file": "a.dat", "unknown_a": 1, "nested_future": nested},
                {"file": "b.dat", "unknown_b": 2, "tuple_future": ("x", 3)},
            ]
        }
    )

    assert tuple(column.key for column in presentation.detail.columns) == (
        "file",
        "unknown_a",
        "unknown_b",
    )
    assert _cell(presentation.detail, 1, "unknown_a").raw is None
    assert _cell(presentation.detail, 1, "unknown_b").raw == 2
    assert "nested_future" not in {column.key for column in presentation.detail.columns}
    assert "tuple_future" not in {column.key for column in presentation.detail.columns}

    nested_cell = _cell(presentation.diagnostics, 0, "nested_future")
    tuple_cell = _cell(presentation.diagnostics, 1, "tuple_future")
    assert nested_cell.raw == json.dumps(nested, ensure_ascii=False, sort_keys=True)
    assert tuple_cell.raw == json.dumps(["x", 3], ensure_ascii=False, sort_keys=True)
    assert isinstance(nested_cell.raw, str)
    assert isinstance(tuple_cell.raw, str)


def test_diagnostics_include_curated_saxs_semantic_families() -> None:
    presentation = _build(
        {
            "lc_reliability_reason": "limited_lc_confidence",
            "calibrated_fallback_reason": "temperature_batch_qstar_calibration",
            "melting_window_reason": "near_sequence_melting_onset",
            "condition_confidence": 0.72,
            "effective_q_min": 0.12,
            "phase_ambiguous": True,
            "strain_reliability_reason": "strain_axis_low_confidence",
            "ordinary_measurement": 9.5,
        }
    )

    diagnostic_keys = {column.key for column in presentation.diagnostics.columns}
    assert {
        "lc_reliability_reason",
        "calibrated_fallback_reason",
        "melting_window_reason",
        "condition_confidence",
        "effective_q_min",
        "phase_ambiguous",
        "strain_reliability_reason",
    } <= diagnostic_keys
    assert "ordinary_measurement" not in diagnostic_keys


def test_batch_summary_preserves_top_level_detail_and_diagnostics_with_clear_identity() -> None:
    phase_distribution = {"elastic": 1, "plastic_voiding": 1}
    params = {
        "batch_frames": 2,
        "condition_source": "filename",
        "condition_confidence": 0.81,
        "condition_missing_frames": 1,
        "condition_continuity_score": 0.94,
        "calibrated_fallback_reason": "temperature_batch_qstar_calibration",
        "dominant_melting_window_status": "near_onset",
        "dominant_lc_reliability_status": "low_confidence",
        "frame_low_conf_count": 1,
        "phase_distribution": phase_distribution,
        "future_batch_scalar": "preserved",
        "void_dominant_frame_count": 1,
        "_batch_data": [
            {
                "file": "frame_001.dat",
                "lc_nm": 3.2,
                "beam_stop_contaminated": True,
            },
            {
                "file": "frame_002.dat",
                "lc_nm": 3.3,
                "beam_stop_q_min": 0.12,
            },
        ],
    }
    before = copy.deepcopy(params)

    presentation = _build(params)

    assert presentation.summary_count == 2
    assert len(presentation.primary.rows) == 2
    assert _cell(presentation.detail, 0, "file").raw == "frame_001.dat"
    assert _cell(presentation.detail, 1, "file").raw == "frame_002.dat"
    assert _cell(presentation.detail, 0, "row_scope").raw == "frame"
    assert _cell(presentation.detail, 1, "row_scope").raw == "frame"

    detail_summary_row = next(
        index
        for index in range(len(presentation.detail.rows))
        if _cell(presentation.detail, index, "row_scope").raw == "batch_summary"
    )
    assert detail_summary_row == 2
    assert _cell(presentation.detail, detail_summary_row, "future_batch_scalar").raw == "preserved"
    assert _cell(presentation.detail, detail_summary_row, "condition_continuity_score").raw == 0.94

    diagnostic_keys = {column.key for column in presentation.diagnostics.columns}
    assert {
        "row_scope",
        "condition_source",
        "condition_confidence",
        "condition_missing_frames",
        "condition_continuity_score",
        "calibrated_fallback_reason",
        "dominant_melting_window_status",
        "dominant_lc_reliability_status",
        "frame_low_conf_count",
        "phase_distribution",
        "void_dominant_frame_count",
        "beam_stop_contaminated",
        "beam_stop_q_min",
    } <= diagnostic_keys
    assert _cell(presentation.diagnostics, 0, "beam_stop_contaminated").raw is True
    assert _cell(presentation.diagnostics, 1, "beam_stop_q_min").raw == 0.12
    diagnostic_summary_row = next(
        index
        for index in range(len(presentation.diagnostics.rows))
        if _cell(presentation.diagnostics, index, "row_scope").raw == "batch_summary"
    )
    assert diagnostic_summary_row == 2
    assert _cell(presentation.diagnostics, diagnostic_summary_row, "phase_distribution").raw == json.dumps(
        phase_distribution,
        ensure_ascii=False,
        sort_keys=True,
    )
    assert (
        _cell(presentation.diagnostics, diagnostic_summary_row, "dominant_melting_window_status").display
        == "near onset"
    )
    assert (
        _cell(presentation.diagnostics, diagnostic_summary_row, "dominant_lc_reliability_status").display
        == "low-confidence"
    )
    assert _cell(presentation.diagnostics, diagnostic_summary_row, "frame_low_conf_count").raw == 1
    assert _cell(presentation.diagnostics, diagnostic_summary_row, "void_dominant_frame_count").raw == 1
    assert params == before


@pytest.mark.parametrize("missing_canonical", [None, "", {"nested": "not a scalar"}])
def test_primary_field_tries_later_aliases_when_canonical_value_is_missing(missing_canonical) -> None:
    presentation = _build(
        {
            "lc_nm": missing_canonical,
            "lc_nm_calibrated": 4.2,
            "lc_nm_raw": 3.8,
            "lc_method": "calibrated",
            "lc_reliability_status": "usable",
        }
    )

    lc_cell = _cell(presentation.primary, 0, "lc_nm")
    assert lc_cell.raw == 4.2
    assert lc_cell.display == "4.20"
    assert lc_cell.provenance == "calibrated"
    assert lc_cell.status == "reliable"


def test_lc_provenance_is_per_row_and_unknown_is_never_inferred_as_raw() -> None:
    presentation = _build(
        {
            "_batch_data": [
                {"file": "unknown.dat", "lc_nm": 2.0, "lc_reliability_status": "ok"},
                {
                    "file": "raw.dat",
                    "lc_nm": 2.1,
                    "lc_method": "raw",
                    "lc_reliability_status": "usable",
                },
                {
                    "file": "cal.dat",
                    "lc_nm": 2.2,
                    "lc_method": "calibrated",
                    "lc_reliability_status": "low_confidence",
                },
            ]
        }
    )

    assert _cell(presentation.primary, 0, "lc_nm").provenance == ""
    assert _cell(presentation.primary, 0, "lc_method").raw is None
    assert _cell(presentation.primary, 0, "lc_method").display == "\N{EM DASH}"
    assert _cell(presentation.primary, 1, "lc_nm").provenance == "raw"
    assert _cell(presentation.primary, 2, "lc_nm").provenance == "calibrated"
    assert _cell(presentation.primary, 1, "lc_method").display == "raw"
    assert _cell(presentation.primary, 2, "lc_method").display == "calibrated"


def test_numpy_scalars_are_normalized_without_mutating_input() -> None:
    params = {
        "_batch_data": [
            {
                "file": np.str_("sample.dat"),
                "L_nm": np.float32(12.5),
                "count": np.int64(3),
                "accepted": np.bool_(True),
                "lc_nm": np.float64(3.5),
            }
        ]
    }
    before = copy.deepcopy(params)

    presentation = _build(params)

    assert type(_cell(presentation.primary, 0, "L_nm").raw) is float
    assert type(_cell(presentation.detail, 0, "count").raw) is int
    assert type(_cell(presentation.detail, 0, "accepted").raw) is bool
    assert _cell(presentation.detail, 0, "accepted").display == "Yes"
    assert np.array_equal(params["_batch_data"][0]["L_nm"], before["_batch_data"][0]["L_nm"])
    assert params.keys() == before.keys()
    assert params["_batch_data"][0].keys() == before["_batch_data"][0].keys()


def test_heroes_prefer_top_level_summaries_then_first_row_and_skip_nonfinite() -> None:
    presentation = _build(
        {
            "L_nm": 20.0,
            "lc_nm": np.nan,
            "condition_confidence": np.float32(0.91),
            "_batch_data": [
                {
                    "L_nm": 10.0,
                    "lc_nm": 3.25,
                    "lc_method": "raw",
                    "lc_reliability_status": "usable",
                    "Tm_peak_C": np.inf,
                    "condition_confidence": 0.5,
                }
            ],
        },
        submodule="saxs.temperature",
    )

    assert tuple(metric.key for metric in presentation.hero_metrics) == (
        "L_nm",
        "lc_nm",
        "condition_confidence",
    )
    assert presentation.hero_metrics[0].raw == 20.0
    assert presentation.hero_metrics[1].raw == 3.25
    assert presentation.hero_metrics[1].provenance == "raw"
    assert presentation.hero_metrics[1].status == "reliable"
    assert presentation.hero_metrics[2].raw == pytest.approx(0.91)
    assert len(presentation.hero_metrics) <= 4


def test_flags_follow_actual_copied_row_count() -> None:
    one = _build({"_batch_data": [{"file": "one.dat"}]})
    many = _build({"_batch_data": [{"file": "one.dat"}, "ignored", {"file": "two.dat"}]})

    assert (one.summary_count, one.sortable, one.copy_enabled, one.export_enabled) == (1, False, True, True)
    assert (many.summary_count, many.sortable, many.copy_enabled, many.export_enabled) == (2, True, True, True)


def test_representative_labels_and_status_values_are_bilingual() -> None:
    previous = get_language()
    params = {
        "temperature_C": 195.0,
        "lc_nm": 3.0,
        "lc_method": "qstar_calibrated",
        "melting_window_status": "within_window",
        "lc_reliability_status": "diagnostic_only",
    }

    english = _build(params, submodule="saxs.temperature", language="en")
    chinese = _build(params, submodule="saxs.temperature", language="zh")

    assert english.primary.columns[0].label == "Temperature"
    assert _cell(english.primary, 0, "lc_method").display == "Q* calibrated"
    assert _cell(english.primary, 0, "melting_window_status").display == "within window"
    assert _cell(english.primary, 0, "lc_reliability_status").display == "diagnostic-only"

    assert chinese.primary.columns[0].label == "\u6e29\u5ea6"
    assert _cell(chinese.primary, 0, "lc_method").display == "Q* \u6821\u51c6"
    assert _cell(chinese.primary, 0, "melting_window_status").display == "\u7a97\u53e3\u5185"
    assert _cell(chinese.primary, 0, "lc_reliability_status").display == "\u4ec5\u4f5c\u8bca\u65ad"
    assert get_language() == previous


def test_language_explicit_translation_does_not_change_global_language() -> None:
    previous = get_language()

    assert i18n.tr_for_language("TABLE_FIELD_TEMPERATURE", "en") == "Temperature"
    assert i18n.tr_for_language("TABLE_FIELD_TEMPERATURE", "zh") == "\u6e29\u5ea6"
    assert i18n.tr_for_language("SIDEBAR_SUBMODULE_COUNT", "en", 3) == "3 sub-modules"
    assert get_language() == previous


def test_adapter_never_calls_persisting_language_apis(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _service_module()
    set_language("en")

    def fail(*_args, **_kwargs):
        raise AssertionError("presentation localization must not persist language")

    monkeypatch.setattr(i18n, "set_language", fail)
    monkeypatch.setattr(i18n, "_save_lang", fail)
    monkeypatch.setattr(service, "set_language", fail, raising=False)

    chinese = service.build_saxs_results_presentation(
        {
            "temperature_C": 195.0,
            "lc_reliability_status": "diagnostic_only",
        },
        submodule="saxs.temperature",
        language="zh",
    )
    english = service.build_saxs_results_presentation(
        {
            "temperature_C": 195.0,
            "lc_reliability_status": "diagnostic_only",
        },
        submodule="saxs.temperature",
        language="en",
    )

    assert chinese.primary.columns[0].label == "\u6e29\u5ea6"
    assert _cell(chinese.primary, 0, "lc_reliability_status").display == "\u4ec5\u4f5c\u8bca\u65ad"
    assert english.primary.columns[0].label == "Temperature"
    assert _cell(english.primary, 0, "lc_reliability_status").display == "diagnostic-only"
    assert get_language() == "en"


def test_adapter_exception_path_never_touches_global_language(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service_module()
    set_language("en")

    def fail_language(*_args, **_kwargs):
        raise AssertionError("language persistence called on exception path")

    def fail_primary(*_args, **_kwargs):
        raise RuntimeError("sentinel presentation failure")

    monkeypatch.setattr(i18n, "set_language", fail_language)
    monkeypatch.setattr(i18n, "_save_lang", fail_language)
    monkeypatch.setattr(service, "set_language", fail_language, raising=False)
    monkeypatch.setattr(service, "_primary_section", fail_primary)

    with pytest.raises(RuntimeError, match="sentinel presentation failure"):
        service.build_saxs_results_presentation(
            {"L_nm": 12.0},
            submodule="saxs.static",
            language="zh",
        )
    assert get_language() == "en"


@pytest.mark.parametrize(
    (
        "params",
        "expected_value",
        "expected_source",
        "expected_status",
        "tooltip_fragment",
    ),
    [
        (
            {
                "lc_nm": 5.0,
                "lc_nm_raw": 3.8,
                "lc_nm_calibrated": 4.2,
                "lc_method": "raw",
            },
            5.0,
            "raw",
            "reliable",
            "",
        ),
        (
            {
                "lc_nm": None,
                "lc_nm_raw": 3.8,
                "lc_nm_calibrated": 4.2,
                "lc_method": "raw",
            },
            3.8,
            "raw",
            "reliable",
            "",
        ),
        (
            {
                "lc_nm": None,
                "lc_nm_raw": 3.8,
                "lc_nm_calibrated": 4.2,
                "lc_method": "calibrated",
            },
            4.2,
            "calibrated",
            "reliable",
            "",
        ),
        (
            {"lc_nm": None, "lc_nm_raw": 3.8, "lc_nm_calibrated": 4.2},
            3.8,
            "raw",
            "review",
            "missing",
        ),
        (
            {
                "lc_nm": None,
                "lc_nm_raw": 3.8,
                "lc_nm_calibrated": 4.2,
                "lc_method": "custom_method",
            },
            3.8,
            "raw",
            "review",
            "unknown",
        ),
        (
            {
                "lc_nm": None,
                "lc_nm_raw": None,
                "lc_nm_calibrated": 4.2,
                "lc_method": "raw",
            },
            4.2,
            "calibrated",
            "review",
            "contradicts",
        ),
    ],
)
def test_lc_value_and_selected_source_stay_coherent(
    params,
    expected_value,
    expected_source,
    expected_status,
    tooltip_fragment,
) -> None:
    params["lc_reliability_status"] = "usable"

    presentation = _build(params)

    lc_cell = _cell(presentation.primary, 0, "lc_nm")
    source_cell = _cell(presentation.primary, 0, "lc_method")
    assert lc_cell.raw == expected_value
    assert lc_cell.provenance == expected_source
    assert lc_cell.status == expected_status
    assert source_cell.raw == expected_source
    assert source_cell.display in {"raw", "calibrated"}
    assert tooltip_fragment in lc_cell.tooltip
    assert tooltip_fragment in source_cell.tooltip


@pytest.mark.parametrize(
    ("reliability", "expected_status"),
    [
        ("usable", "review"),
        ("low_confidence", "review"),
        ("diagnostic_only", "blocked"),
    ],
)
@pytest.mark.parametrize("declared_method", ["raw", None, "custom_method"])
def test_all_missing_lc_values_have_no_selected_source_or_provenance(
    declared_method,
    reliability,
    expected_status,
) -> None:
    presentation = _build(
        {
            "file": "missing-lc.dat",
            "lc_nm": None,
            "lc_nm_raw": None,
            "lc_nm_calibrated": None,
            "lc_method": declared_method,
            "lc_reliability_status": reliability,
        }
    )

    lc_cell = _cell(presentation.primary, 0, "lc_nm")
    source_cell = _cell(presentation.primary, 0, "lc_method")
    assert lc_cell.raw is None
    assert source_cell.raw is None
    assert lc_cell.provenance == ""
    assert source_cell.provenance == ""
    assert lc_cell.status == expected_status
    assert source_cell.status == expected_status
    assert lc_cell.tooltip == "No usable lc value is available"
    assert source_cell.tooltip == "No usable lc value is available"
    assert source_cell.display == "\N{EM DASH}"


@pytest.mark.parametrize(
    "missing_values",
    [
        {},
        {"lc_nm": None, "lc_nm_raw": None, "lc_nm_calibrated": None},
        {"lc_nm": "", "lc_nm_raw": "", "lc_nm_calibrated": ""},
        {"lc_nm": {}, "lc_nm_raw": [], "lc_nm_calibrated": ()},
    ],
)
def test_all_unavailable_lc_value_shapes_are_ambiguous(missing_values) -> None:
    presentation = _build(
        {
            "file": "missing-lc.dat",
            "lc_method": "calibrated",
            "lc_reliability_status": "usable",
            **missing_values,
        }
    )

    lc_cell = _cell(presentation.primary, 0, "lc_nm")
    assert lc_cell.raw is None
    assert lc_cell.provenance == ""
    assert lc_cell.status == "review"
    assert lc_cell.tooltip == "No usable lc value is available"


def test_missing_lc_tooltip_is_language_explicit_without_global_writes() -> None:
    params = {
        "file": "missing-lc.dat",
        "lc_method": "raw",
        "lc_reliability_status": "usable",
    }
    previous = get_language()

    english = _build(params, language="en")
    chinese = _build(params, language="zh")

    assert _cell(english.primary, 0, "lc_nm").tooltip == "No usable lc value is available"
    assert _cell(chinese.primary, 0, "lc_nm").tooltip == "\u6ca1\u6709\u53ef\u7528\u7684 lc \u6570\u503c"
    assert "No usable" not in _cell(chinese.primary, 0, "lc_nm").tooltip
    assert get_language() == previous


def test_nested_nonfinite_values_are_serialized_as_standard_json_null() -> None:
    presentation = _build(
        {
            "nested_nonfinite": {
                "nan": float("nan"),
                "positive": float("inf"),
                "negative": float("-inf"),
            }
        }
    )

    serialized = _cell(presentation.diagnostics, 0, "nested_nonfinite").raw
    assert serialized == '{"nan": null, "negative": null, "positive": null}'
    assert "NaN" not in serialized
    assert "Infinity" not in serialized


def test_cyclic_and_deep_nested_values_degrade_deterministically() -> None:
    cyclic: list[object] = []
    cyclic.append(cyclic)
    deep: object = "leaf"
    for _ in range(80):
        deep = [deep]

    presentation = _build({"cyclic": cyclic, "deep": deep})

    assert _cell(presentation.diagnostics, 0, "cyclic").raw == '["<cycle>"]'
    deep_text = _cell(presentation.diagnostics, 0, "deep").raw
    assert "<max-depth>" in deep_text
    assert _build({"cyclic": cyclic}).diagnostics.rows[0][0].raw == '["<cycle>"]'


@pytest.mark.parametrize("value", [complex(float("nan"), 1.0), complex(1.0, float("inf"))])
def test_nonfinite_complex_values_display_as_unavailable(value: complex) -> None:
    english = _build({"future_complex": value}, language="en")
    chinese = _build({"future_complex": value}, language="zh")

    assert type(_cell(english.detail, 0, "future_complex").raw) is complex
    assert _cell(english.detail, 0, "future_complex").display == "Unavailable"
    assert _cell(chinese.detail, 0, "future_complex").display == "\u4e0d\u53ef\u7528"


def test_diagnostics_exclude_axis_fields_but_keep_quality_evidence() -> None:
    presentation = _build(
        {
            "condition_label": "Strain",
            "condition_value": 8.0,
            "condition_unit": "%",
            "strain_pct": 8.0,
            "condition_source": "filename",
            "condition_confidence": 0.72,
            "condition_missing_frames": 1,
            "condition_continuity_score": 0.91,
            "strain_axis_confidence": 0.72,
            "strain_reliability_status": "low_confidence",
            "strain_reliability_reason": "strain_axis_low_confidence",
        },
        submodule="saxs.strain",
    )

    diagnostic_keys = {column.key for column in presentation.diagnostics.columns}
    assert {
        "condition_source",
        "condition_confidence",
        "condition_missing_frames",
        "condition_continuity_score",
        "strain_axis_confidence",
        "strain_reliability_status",
        "strain_reliability_reason",
    } <= diagnostic_keys
    assert {
        "condition_label",
        "condition_value",
        "condition_unit",
        "strain_pct",
    }.isdisjoint(diagnostic_keys)
