from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pytest

from polynexus.gui.analysis_results_table_service import (
    build_analysis_results_presentation,
    try_build_analysis_results_presentation,
)


def _cell(section, row: int, key: str):
    index = next(i for i, column in enumerate(section.columns) if column.key == key)
    return section.rows[row][index]


@pytest.mark.parametrize(
    ("technique", "submodule", "payload", "expected"),
    [
        (
            "dsc",
            "dsc.standard",
            {
                "scan": "scan-01",
                "Tg_C": 72.345,
                "Tm_peak_C": 168.91,
                "DHm_Jg": 41.2,
                "Tc_C": 131.0,
                "Xc_pct": 0.45,
                "event_support_status": "usable",
                "baseline_stability": "good",
                "peak_components": [{"peak": 1, "area": 2.0}],
                "unknown_scalar": "kept",
            },
            ["scan", "Tg_C", "Tm_peak_C", "DHm_Jg", "Tc_C", "Xc_pct", "event_support_status", "status"],
        ),
        (
            "ir",
            "ir.standard",
            {
                "sample": "P1",
                "material_match": "PE",
                "match_score": 0.923,
                "peak_count": 8,
                "band_hit_count": 5,
                "assignment_confidence": 0.81,
                "crystallinity_index": 0.42,
                "status": "review",
                "peaks": [{"wavenumber": 1_100.2, "assignment": "C-O"}],
            },
            ["sample", "material_match", "match_score", "peak_count", "band_hit_count", "assignment_confidence", "crystallinity_index", "status"],
        ),
        (
            "waxs",
            "waxs.static",
            {
                "sample": "P2",
                "condition": "ambient",
                "Xc_pct": 0.31,
                "D_Scherrer_nm": 13.4,
                "dominant_crystal_type": "alpha",
                "peak_count": 4,
                "physical_support_score": 0.77,
                "status": "usable",
                "future_scalar": 7,
            },
            ["sample", "condition", "Xc_pct", "D_Scherrer_nm", "dominant_crystal_type", "peak_count", "physical_support_score", "status"],
        ),
        (
            "nmr",
            "nmr.solid_c",
            {
                "spectrum": "s1",
                "nucleus": "13C",
                "sample_state": "solid",
                "peak_count": 12,
                "dominant_peak_ppm": 31.24,
                "median_SNR": 18.2,
                "mean_FWHM_ppm": 2.1,
                "fit_quality": 0.91,
                "status": "usable",
                "Xc_pct": 0.52,
                "phase_composition": "PE crystal",
                "assignment_coverage": 0.84,
            },
            ["spectrum", "nucleus", "sample_state", "peak_count", "dominant_peak_ppm", "median_SNR", "mean_FWHM_ppm", "fit_quality", "status", "Xc_pct", "phase_composition", "assignment_coverage"],
        ),
    ],
)
def test_supported_analysis_payloads_build_explicit_primary_rows(technique, submodule, payload, expected):
    presentation = build_analysis_results_presentation(
        payload,
        technique=technique,
        submodule=submodule,
        language="en",
    )

    assert presentation.kind == submodule
    assert [column.key for column in presentation.primary.columns] == expected
    assert [cell.raw for cell in presentation.primary.rows[0]] == [payload.get(key) for key in expected]
    assert presentation.export_enabled is True
    assert presentation.copy_enabled is True


def test_adapter_keeps_unknown_scalars_in_detail_and_nested_values_in_diagnostics():
    payload = {
        "sample": "P1",
        "match_score": np.float64(0.8),
        "unknown_scalar": 17,
        "future_nested": {"b": [2, 1], "a": True},
        "peaks": [{"ppm": 4.2, "area": 1.0}],
        "quality_flag": "WARN",
    }

    presentation = build_analysis_results_presentation(
        payload,
        technique="ir",
        submodule="ir.standard",
        language="en",
    )

    assert _cell(presentation.detail, 0, "unknown_scalar").raw == 17
    assert "future_nested" not in {column.key for column in presentation.detail.columns}
    assert _cell(presentation.diagnostics, 0, "future_nested").raw == json.dumps(
        payload["future_nested"], ensure_ascii=False, sort_keys=True
    )
    assert _cell(presentation.diagnostics, 0, "peaks").raw == json.dumps(
        payload["peaks"], ensure_ascii=False, sort_keys=True
    )
    assert _cell(presentation.diagnostics, 0, "quality_flag").raw == "WARN"


def test_batch_rows_keep_summary_only_in_detail_and_diagnostics():
    payload = {
        "batch_frames": 2,
        "Tm_peak_C": 170.0,
        "batch_quality": {"spread": 0.1},
        "_batch_data": [
            {"scan": "a", "Tm_peak_C": 168.0, "status": "usable"},
            {"scan": "b", "Tm_peak_C": 172.0, "status": "review"},
        ],
    }

    presentation = build_analysis_results_presentation(
        payload,
        technique="dsc",
        submodule="dsc.standard",
        language="en",
    )

    assert presentation.summary_count == 2
    assert len(presentation.primary.rows) == 2
    assert [
        _cell(presentation.detail, row, "row_scope").raw
        for row in range(len(presentation.detail.rows))
    ] == ["frame", "frame", "batch_summary"]
    assert _cell(presentation.detail, 2, "Tm_peak_C").raw == 170.0
    assert _cell(presentation.diagnostics, 2, "batch_quality").raw == json.dumps(
        payload["batch_quality"], ensure_ascii=False, sort_keys=True
    )


def test_object_payload_merges_parameters_and_analysis_evidence_without_mutation():
    result = SimpleNamespace(
        parameters={"spectrum": "s1", "nucleus": "1H", "peak_count": 3},
        analysis_evidence={
            "fit_quality": 0.93,
            "peak_rows": [{"ppm": 1.2}],
            "assignment_coverage": 0.5,
        },
    )

    presentation = build_analysis_results_presentation(
        result,
        technique="nmr",
        submodule="nmr.liquid_h",
        language="en",
    )

    assert _cell(presentation.primary, 0, "spectrum").raw == "s1"
    assert _cell(presentation.primary, 0, "fit_quality").raw == 0.93
    assert _cell(presentation.detail, 0, "assignment_coverage").raw == 0.5
    assert _cell(presentation.diagnostics, 0, "peak_rows").raw == json.dumps(
        [{"ppm": 1.2}], ensure_ascii=False, sort_keys=True
    )
    assert result.parameters == {"spectrum": "s1", "nucleus": "1H", "peak_count": 3}


def test_analysis_result_object_includes_top_level_validation_evidence():
    result = SimpleNamespace(
        parameters={"scan": "s1", "Tg_C": 70.0},
        analysis_evidence={},
        validation_passed=False,
        quality_flags={"scan/Tg": "WARN"},
        validation_warnings=["scan/Tg"],
        validation_summary="validation incomplete",
    )

    presentation = build_analysis_results_presentation(
        result,
        technique="dsc",
        submodule="dsc.standard",
        language="en",
    )

    assert _cell(presentation.detail, 0, "validation_passed").raw is False
    assert _cell(presentation.diagnostics, 0, "quality_flags").raw == json.dumps(
        {"scan/Tg": "WARN"}, ensure_ascii=False, sort_keys=True
    )
    assert _cell(presentation.diagnostics, 0, "validation_warnings").raw == json.dumps(
        ["scan/Tg"], ensure_ascii=False, sort_keys=True
    )


def test_complex_nonfinite_values_are_unavailable_not_python_literals():
    presentation = build_analysis_results_presentation(
        {"match_score": complex(float("nan"), 1.0)},
        technique="ir",
        submodule="ir.standard",
        language="en",
    )

    cell = _cell(presentation.primary, 0, "match_score")
    assert cell.display == "Unavailable"
    assert "nan" not in cell.display.lower()


def test_nested_extended_numpy_scalars_are_json_safe():
    presentation = build_analysis_results_presentation(
        {"peaks": {"value": np.longdouble("nan")}},
        technique="nmr",
        submodule="nmr.liquid_h",
        language="en",
    )

    cell = _cell(presentation.diagnostics, 0, "peaks")
    assert cell.raw == '{"value": null}'


def test_dynamic_sections_keep_status_and_provenance_links():
    presentation = build_analysis_results_presentation(
        {
            "match_score": 0.9,
            "match_score_status": "low_confidence",
            "match_score_source": "reference-library",
            "future_metric": 1.2,
            "future_metric_status": "usable",
            "future_metric_provenance": "instrument-fit",
        },
        technique="ir",
        submodule="ir.standard",
        language="en",
    )

    match = _cell(presentation.detail, 0, "match_score")
    future = _cell(presentation.detail, 0, "future_metric")
    assert match.status == "review"
    assert match.provenance == "reference-library"
    assert future.status == "reliable"
    assert future.provenance == "instrument-fit"


def test_nonfinite_values_preserve_raw_and_use_unavailable_display():
    presentation = build_analysis_results_presentation(
        {"match_score": np.nan, "assignment_confidence": np.inf},
        technique="ir",
        submodule="ir.standard",
        language="en",
    )

    assert _cell(presentation.primary, 0, "match_score").raw != _cell(presentation.primary, 0, "match_score").raw
    assert _cell(presentation.primary, 0, "match_score").display == "Unavailable"
    assert _cell(presentation.primary, 0, "assignment_confidence").display == "Unavailable"


def test_language_switch_changes_labels_and_status_display_without_global_state():
    payload = {"Xc_pct": 0.42, "status": "usable"}
    english = build_analysis_results_presentation(payload, technique="waxs", submodule="waxs.static", language="en")
    chinese = build_analysis_results_presentation(payload, technique="waxs", submodule="waxs.static", language="zh")

    assert english.primary.columns[0].label == "Sample"
    assert chinese.primary.columns[0].label == "样品"
    assert _cell(english.primary, 0, "status").display == "Reliable"
    assert _cell(chinese.primary, 0, "status").display == "可靠"
    assert _cell(chinese.primary, 0, "Xc_pct").raw == 0.42


def test_empty_unknown_and_exception_safe_fallback():
    empty = build_analysis_results_presentation(None, technique="dsc", submodule="dsc.standard", language="en")
    assert empty.kind == "dsc.standard"
    assert empty.primary.rows == ()
    assert empty.export_enabled is False
    assert build_analysis_results_presentation({}, technique="raman", submodule="raman.standard", language="en") is None
    assert try_build_analysis_results_presentation({"sample": "x"}, technique="raman", submodule="raman.standard", language="en") is None
