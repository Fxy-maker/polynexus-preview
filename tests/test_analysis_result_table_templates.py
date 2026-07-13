from __future__ import annotations

import pytest

from polynexus.gui.analysis_result_table_templates import analysis_template
from polynexus.gui.i18n import tr_for_language


@pytest.mark.parametrize(
    ("technique", "submodule", "expected"),
    [
        ("dsc", "dsc.standard", ["scan", "Tg_C", "Tm_peak_C", "DHm_Jg", "Tc_C", "Xc_pct", "event_support_status", "status"]),
        ("dsc", "dsc.isothermal", ["time_s", "conversion_pct", "Avrami_n", "fit_quality"]),
        ("ir", "ir.standard", ["sample", "material_match", "match_score", "peak_count", "band_hit_count", "assignment_confidence", "crystallinity_index", "status"]),
        ("ir", "ir.temperature_2d", ["temperature_C", "time_s", "band_tracking_status", "transition_temperature_C", "synchronous_support", "asynchronous_support", "low_confidence_frame_ratio", "status"]),
        ("waxs", "waxs.static", ["sample", "condition", "Xc_pct", "D_Scherrer_nm", "dominant_crystal_type", "peak_count", "physical_support_score", "status"]),
        ("nmr", "nmr.liquid_h", ["spectrum", "nucleus", "sample_state", "peak_count", "dominant_peak_ppm", "median_SNR", "mean_FWHM_ppm", "fit_quality", "status"]),
    ],
)
def test_analysis_templates_expose_explicit_primary_columns(technique, submodule, expected):
    template = analysis_template(technique, submodule)
    assert template is not None
    assert [field.key for field in template.primary_fields] == expected


def test_analysis_templates_keep_kinetics_and_condition_modes_distinct():
    standard = analysis_template("dsc", "dsc.standard")
    isothermal = analysis_template("dsc", "dsc.isothermal")
    temperature = analysis_template("waxs", "waxs.temperature")
    strain = analysis_template("waxs", "waxs.strain")

    assert "Tm_peak_C" in [field.key for field in standard.primary_fields]
    assert "Avrami_n" in [field.key for field in isothermal.primary_fields]
    assert "temperature_C" in [field.key for field in temperature.primary_fields]
    assert "strain_pct" in [field.key for field in strain.primary_fields]
    assert "temperature_C" not in [field.key for field in strain.primary_fields]


def test_nmr_liquid_omits_solid_only_crystallinity_fields():
    liquid_h = analysis_template("nmr", "nmr.liquid_h")
    liquid_c = analysis_template("nmr", "nmr.liquid_c")
    solid_c = analysis_template("nmr", "nmr.solid_c")

    assert "Xc_pct" not in {field.key for field in liquid_h.primary_fields}
    assert "Xc_pct" not in {field.key for field in liquid_c.primary_fields}
    assert {"Xc_pct", "phase_composition", "assignment_coverage"} <= {
        field.key for field in solid_c.primary_fields
    }


def test_template_fields_have_units_precision_and_bilingual_labels():
    template = analysis_template("waxs", "waxs.static")
    xc = next(field for field in template.primary_fields if field.key == "Xc_pct")
    assert xc.unit == "%"
    assert xc.digits == 2
    assert xc.importance == "hero"
    assert tr_for_language(xc.label_key, "zh")
    assert tr_for_language(xc.label_key, "en")


def test_unknown_submodule_falls_back_but_unknown_technique_does_not():
    assert analysis_template("dsc", "dsc.unknown").key == "dsc.standard"
    assert analysis_template("waxs", "").key == "waxs.static"
    assert analysis_template("raman", "raman.standard") is None
