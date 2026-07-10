import numpy as np
import pytest

from polynexus.core.dsc import DSCEngine
from polynexus.core.dsc_engine.core import DSCResult
from polynexus.core.dsc_engine.figure_provider import build_dsc_figure_definitions
from polynexus.core.figures.validation import validate_figure_definition


@pytest.fixture
def dsc_results():
    temperature = np.array([20.0, 40.0, 60.0, 80.0, 100.0])
    return (
        DSCResult(
            label="dsc-a",
            T=temperature,
            HF=np.array([0.1, 0.2, 0.35, 0.8, 0.25]),
            HF_fit=np.array([0.11, 0.19, 0.34, 0.77, 0.27]),
            Tg_C=60.0,
            DTg_C=18.0,
            Tm_peak_C=82.0,
            Tc_peak_C=42.0,
            Xc_pct=38.0,
            peak_components=[
                {
                    "type": "deconv_melting",
                    "mu_C": 75.0,
                    "sigma_C": 5.0,
                    "amp": 0.4,
                    "fraction": 0.55,
                },
                {
                    "type": "deconv_melting",
                    "mu_C": 86.0,
                    "sigma_C": 4.0,
                    "amp": 0.3,
                    "fraction": 0.45,
                },
            ],
        ),
        DSCResult(
            label="dsc-b",
            T=temperature,
            HF=np.array([0.08, 0.18, 0.3, 0.7, 0.2]),
            Xc_pct=29.0,
        ),
    )


def test_dsc_provider_emits_thermogram_tg_deconvolution_and_overview(dsc_results):
    definitions = build_dsc_figure_definitions(dsc_results)

    assert [item.figure_id for item in definitions] == [
        "dsc.frame.thermogram.001",
        "dsc.frame.tg.001",
        "dsc.frame.deconvolution.001",
        "dsc.frame.thermogram.002",
        "dsc.series.crystallinity",
    ]
    assert sum(obj["type"] == "line" for obj in definitions[0].objects) == 3
    assert definitions[1].recipe["parameters"]["figure_kind"] == "tg"
    assert sum(
        obj["type"] == "plot_series" for obj in definitions[2].objects
    ) == 3
    assert definitions[-1].objects[0]["chart_kind"] == "bar"

    for definition in definitions:
        validate_figure_definition(definition)


def test_dsc_engine_exposes_complete_definitions(dsc_results):
    engine = DSCEngine()
    engine._results = list(dsc_results)

    definitions = engine.build_figure_definitions()

    assert {item.figure_id for item in definitions} >= {
        "dsc.frame.thermogram.001",
        "dsc.series.crystallinity",
    }
