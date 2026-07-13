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
