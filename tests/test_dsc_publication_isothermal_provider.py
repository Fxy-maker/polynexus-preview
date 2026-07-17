from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from polynexus.core.dsc_engine.figure_isothermal import build_isothermal_dsc_figure_definitions


def _fit(*, r_squared: float = 0.97) -> SimpleNamespace:
    return SimpleNamespace(
        label="150 C",
        t_data=np.arange(6.0),
        Xt_data=np.array([0.02, 0.12, 0.35, 0.60, 0.82, 0.95]),
        Xt_fit=np.array([0.01, 0.13, 0.34, 0.59, 0.81, 0.94]),
        n=2.1,
        k=0.04,
        t_half_min=3.0,
        r_squared=r_squared,
        quality_flags=[],
    )


def _engine(*, r_squared: float = 0.97) -> SimpleNamespace:
    fit = _fit(r_squared=r_squared)
    return SimpleNamespace(_kinetics_data={"avrami": fit, "avrami_series": [fit]})


def test_valid_avrami_fit_creates_main_and_keeps_full_series_in_si() -> None:
    definitions = build_isothermal_dsc_figure_definitions(_engine())
    assert next(item for item in definitions if item.figure_id == "dsc.isothermal.avrami").publication_role == "main"
    assert next(item for item in definitions if item.figure_id == "dsc.isothermal.series").publication_role == "si"


def test_invalid_avrami_never_becomes_main() -> None:
    definitions = build_isothermal_dsc_figure_definitions(_engine(r_squared=0.42))
    assert all(item.figure_id != "dsc.isothermal.avrami" for item in definitions if item.publication_role == "main")
    assert any(item.figure_id == "dsc.isothermal.fit.diagnostic" for item in definitions)


def test_no_main_isothermal_pack_records_publication_fallback_reason() -> None:
    diagnostic = next(
        item
        for item in build_isothermal_dsc_figure_definitions(_engine(r_squared=0.42))
        if item.publication_role == "diagnostic"
    )
    parameters = diagnostic.recipe["parameters"]
    assert parameters["no_publication_ready_figure"] is True
    assert parameters["reason"] == "fit_quality_below_main_threshold"
