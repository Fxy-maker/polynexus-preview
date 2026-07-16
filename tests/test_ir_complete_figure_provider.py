import numpy as np
import pytest

from polynexus.core.figures.validation import validate_figure_definition
from polynexus.core.figures.v2_capabilities import build_v2_definition_artifact
from polynexus.core.ir import IREngine
from polynexus.core.ir_engine.core import IRResult
from polynexus.core.ir_engine.figure_provider import build_ir_figure_definitions
from polynexus.core.ir_engine.io import IRSpectrum


@pytest.fixture
def ir_complete_results():
    return (
        IRResult(
            label="sample-a",
            wavenumber=np.array([1800.0, 1700.0, 1600.0]),
            absorbance=np.array([0.1, 0.4, 0.2]),
            absorbance_fit=np.array([0.12, 0.38, 0.21]),
            simulated_spectrum=IRSpectrum(
                label="computed-a",
                wavenumber=np.array([1820.0, 1710.0, 1590.0]),
                absorbance=np.array([0.08, 0.35, 0.18]),
                source="computation",
            ),
            peaks=[
                {
                    "wavenumber": 1700.0,
                    "height": 0.4,
                    "prominence": 0.3,
                    "assignment": "amide I",
                }
            ],
            Xc_pct=31.0,
        ),
        IRResult(
            label="sample-b",
            wavenumber=np.array([1800.0, 1700.0, 1600.0]),
            absorbance=np.array([0.09, 0.32, 0.17]),
            Xc_pct=46.5,
        ),
    )


def test_complete_ir_provider_emits_expected_semantic_figures(ir_complete_results):
    definitions = build_ir_figure_definitions(ir_complete_results)

    assert [item.figure_id for item in definitions] == [
        "ir.frame.spectrum.001",
        "ir.frame.peak-fit.001",
        "ir.frame.comparison.001",
        "ir.frame.spectrum.002",
        "ir.series.crystallinity",
    ]
    peak_fit = definitions[1]
    assert [
        obj["y_column"]
        for obj in peak_fit.objects
        if obj["type"] == "plot_series"
    ] == ["absorbance", "absorbance_fit"]
    comparison = definitions[2]
    assert len(comparison.data_sources) == 2
    crystallinity = definitions[-1]
    assert crystallinity.objects[0]["chart_kind"] == "bar"
    assert crystallinity.category == "series_overview"
    assert crystallinity.data_sources[0].columns[0].dtype == "str"

    for definition in definitions:
        validate_figure_definition(definition)
        assert definition.recipe["v2_adapter"] == "ir"
        assert build_v2_definition_artifact(definition).capability["v2_runtime"] == "ready"


def test_ir_engine_handoff_returns_complete_definitions(ir_complete_results):
    engine = IREngine()
    engine._results = list(ir_complete_results)

    definitions = engine.build_figure_definitions()

    assert {item.figure_id for item in definitions} >= {
        "ir.frame.peak-fit.001",
        "ir.frame.comparison.001",
        "ir.series.crystallinity",
    }
