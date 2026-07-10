import numpy as np
import pytest

from polynexus.core.figures.validation import validate_figure_definition
from polynexus.core.nmr import NMREngine
from polynexus.core.nmr_engine.core import NMRResult
from polynexus.core.nmr_engine.figure_provider import build_nmr_figure_definitions


@pytest.fixture
def nmr_results():
    ppm = np.array([180.0, 140.0, 100.0, 60.0, 20.0])
    return (
        NMRResult(
            label="nmr-a",
            nucleus="13C",
            ppm=ppm,
            intensity=np.array([0.1, 0.4, 0.25, 0.6, 0.15]),
            intensity_fit=np.array([0.11, 0.38, 0.26, 0.57, 0.16]),
            peaks=[
                {
                    "ppm": 60.0,
                    "height": 0.6,
                    "prominence": 0.5,
                    "assignment": "crystalline C",
                }
            ],
            matches=[
                {"exp_ppm": 60.0, "calc_ppm": 62.0},
                {"exp_ppm": 140.0, "calc_ppm": 138.0},
            ],
            region_integrals={"aliphatic": 63.0, "aromatic": 37.0},
            Xc_pct=41.0,
        ),
        NMRResult(
            label="nmr-b",
            nucleus="13C",
            ppm=ppm,
            intensity=np.array([0.08, 0.3, 0.2, 0.5, 0.12]),
            Xc_pct=33.0,
        ),
    )


def test_nmr_provider_emits_complete_semantic_figures(nmr_results):
    definitions = build_nmr_figure_definitions(nmr_results)

    assert [item.figure_id for item in definitions] == [
        "nmr.frame.spectrum.001",
        "nmr.frame.deconvolution.001",
        "nmr.frame.comparison.001",
        "nmr.frame.region-integrals.001",
        "nmr.frame.spectrum.002",
        "nmr.series.crystallinity",
    ]
    assert definitions[0].layout.panels[0].x_axis.reversed is True
    assert definitions[1].layout.panels[0].x_axis.reversed is True
    assert definitions[2].objects[0]["chart_kind"] == "scatter"
    assert definitions[3].objects[0]["chart_kind"] == "bar"
    assert definitions[-1].objects[0]["chart_kind"] == "bar"

    for definition in definitions:
        validate_figure_definition(definition)


def test_nmr_engine_exposes_complete_definitions(nmr_results):
    engine = NMREngine()
    engine._results = list(nmr_results)

    definitions = engine.build_figure_definitions()

    assert {item.figure_id for item in definitions} >= {
        "nmr.frame.spectrum.001",
        "nmr.series.crystallinity",
    }
