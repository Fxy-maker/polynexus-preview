from dataclasses import FrozenInstanceError

import pytest

from polynexus.gui.i18n import get_language, set_language, tr
from polynexus.gui.result_table_templates import ResultFieldSpec, saxs_template


def _field_keys(fields: tuple[ResultFieldSpec, ...]) -> tuple[str, ...]:
    return tuple(field.key for field in fields)


def test_result_field_specs_are_immutable_and_expose_aliases_as_source_keys() -> None:
    field = ResultFieldSpec("lc_nm", "TABLE_FIELD_EFFECTIVE_LC", aliases=("raw_lc",))

    assert field.source_keys == ("lc_nm", "raw_lc")
    with pytest.raises(FrozenInstanceError):
        field.key = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("submodule", "template_key", "hero_keys", "primary_keys"),
    [
        (
            "saxs.static",
            "saxs.static",
            ("L_nm", "lc_nm", "la_nm", "phi_c"),
            ("file", "L_nm", "lc_nm", "la_nm", "phi_c", "lc_method", "lc_reliability_status"),
        ),
        (
            "saxs.temperature",
            "saxs.temperature",
            ("L_nm", "lc_nm", "Tm_peak_C", "condition_confidence"),
            (
                "temperature_C",
                "stage",
                "L_nm",
                "lc_nm",
                "lc_method",
                "melting_window_status",
                "lc_reliability_status",
            ),
        ),
        (
            "saxs.strain",
            "saxs.strain",
                (
                    "Q_star_rel_mean",
                    "phi_void_mean",
                    "f_Herman_mean",
                    "f_Herman_raw_mean",
                    "phase_support_mean",
                ),
            (
                "strain_pct",
                    "Q_star_rel",
                    "phi_void",
                    "f_Herman",
                    "f_Herman_raw",
                    "phase_name",
                "phase_support_score",
                "strain_reliability_status",
            ),
        ),
    ],
)
def test_saxs_templates_define_exact_fields_for_each_mode(
    submodule: str,
    template_key: str,
    hero_keys: tuple[str, ...],
    primary_keys: tuple[str, ...],
) -> None:
    template = saxs_template(submodule)

    assert template.key == template_key
    assert _field_keys(template.hero_fields) == hero_keys
    assert _field_keys(template.primary_fields) == primary_keys


def test_saxs_lc_field_binds_aliases_provenance_and_status() -> None:
    for submodule in ("saxs.static", "saxs.temperature"):
        lc_field = next(field for field in saxs_template(submodule).primary_fields if field.key == "lc_nm")

        assert lc_field.source_keys == ("lc_nm", "lc_nm_calibrated", "lc_nm_raw")
        assert lc_field.provenance_key == "lc_method"
        assert lc_field.status_key == "lc_reliability_status"


def test_saxs_mode_specific_aliases_are_kept_separate() -> None:
    static = {field.key: field for field in saxs_template("saxs.static").primary_fields}
    temperature = {field.key: field for field in saxs_template("saxs.temperature").primary_fields}
    strain = {field.key: field for field in saxs_template("saxs.strain").primary_fields}

    assert static["phi_c"].source_keys == ("phi_c", "Xc")
    assert temperature["temperature_C"].source_keys == ("temperature_C", "condition_value")
    assert strain["strain_pct"].source_keys == ("strain_pct", "condition_value")
    assert strain["Q_star_rel"].source_keys == ("Q_star_rel", "Q_rel")
    assert strain["phase_name"].source_keys == ("phase_name", "strain_phase")
    assert "temperature_C" not in static
    assert "strain_pct" not in temperature
    assert "file" not in strain


@pytest.mark.parametrize("submodule", ["", "unknown", None])
def test_saxs_template_falls_back_to_static(submodule: str | None) -> None:
    assert saxs_template(submodule) == saxs_template("saxs.static")


def test_new_table_field_labels_are_available_in_english_and_chinese() -> None:
    previous = get_language()
    try:
        set_language("en")
        assert tr("TABLE_FIELD_LONG_PERIOD") == "Long period"
        assert tr("TABLE_FIELD_Q_STAR_REL") == "Relative Q*"

        set_language("zh")
        assert tr("TABLE_FIELD_LONG_PERIOD") == "长周期"
        assert tr("TABLE_FIELD_Q_STAR_REL") == "Q* 相对值"
    finally:
        set_language(previous)

    assert get_language() == previous
