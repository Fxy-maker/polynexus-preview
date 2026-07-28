from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from polynexus.core.dsc_engine.figure_nonisothermal import build_nonisothermal_dsc_figure_definitions


def _engine(*, kissinger_r2: float = 0.56) -> SimpleNamespace:
    curves = [
        SimpleNamespace(label="1 K/min", rate_K_per_min=1.0, T_xt_C=np.arange(5.0), Xt=np.linspace(0.1, 0.9, 5)),
        SimpleNamespace(label="2 K/min", rate_K_per_min=2.0, T_xt_C=np.arange(5.0) + 2, Xt=np.linspace(0.1, 0.9, 5)),
    ]
    series = SimpleNamespace(curves=curves)
    kissinger = SimpleNamespace(
        rates=[1.0, 2.0, 5.0],
        x=[1.0, 2.0, 5.0],
        y=[121.0, 120.0, 119.0],
        r_squared=kissinger_r2,
        kissinger_Ea_kJmol=120.0,
        quality_flags=[],
    )
    return SimpleNamespace(_kinetics_data={"non_isothermal": series, "kissinger": kissinger})


def test_conversion_curves_are_main_and_unqualified_kinetics_are_not() -> None:
    definitions = build_nonisothermal_dsc_figure_definitions(_engine(kissinger_r2=0.56))
    conversion = next(item for item in definitions if item.figure_id == "dsc.nonisothermal.conversion")
    assert conversion.publication_role == "main"
    assert all(item.figure_id != "dsc.nonisothermal.kissinger" for item in definitions if item.publication_role == "main")
    assert any(item.figure_id == "dsc.nonisothermal.kissinger" and item.publication_role != "main" for item in definitions)


def test_qualified_kinetics_creates_one_second_main_candidate() -> None:
    definitions = build_nonisothermal_dsc_figure_definitions(_engine(kissinger_r2=0.96))
    assert next(item for item in definitions if item.figure_id == "dsc.nonisothermal.kissinger").publication_role == "main"


def test_qualified_rates_only_method_is_diagnostic_without_fabricated_curve() -> None:
    source = _engine(kissinger_r2=0.96)
    rates_only = SimpleNamespace(
        rates=[1.0, 2.0, 5.0],
        r_squared=0.96,
        kissinger_Ea_kJmol=120.0,
        quality_flags=[],
    )
    engine = SimpleNamespace(
        _kinetics_data={
            "non_isothermal": source._kinetics_data["non_isothermal"],
            "kissinger": rates_only,
        }
    )

    definitions = build_nonisothermal_dsc_figure_definitions(engine)
    method = next(item for item in definitions if item.figure_id == "dsc.nonisothermal.kissinger")
    parameters = method.recipe["parameters"]

    assert method.publication_role == "diagnostic"
    assert method.objects == ()
    assert parameters["reason"] == "missing_method_plot_data"
    assert parameters["plot_point_count"] == 0
    assert parameters["reported_parameters"]["kissinger_Ea_kJmol"] == 120.0
    assert all(not source.values.get("response") for source in method.data_sources)


def test_missing_nonisothermal_series_records_publication_fallback_reason() -> None:
    diagnostic = next(
        item
        for item in build_nonisothermal_dsc_figure_definitions(
            SimpleNamespace(_kinetics_data={})
        )
        if item.publication_role == "diagnostic"
    )
    parameters = diagnostic.recipe["parameters"]
    assert parameters["no_publication_ready_figure"] is True
    assert parameters["reason"] == "missing_non_isothermal_series"
