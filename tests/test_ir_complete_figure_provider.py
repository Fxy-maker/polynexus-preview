import numpy as np
import pytest

from polynexus.core.figures.validation import validate_figure_definition
from polynexus.core.figures.v2_capabilities import build_v2_definition_artifact
from polynexus.core.ir import IREngine
from polynexus.core.ir_engine.core import IRResult
from polynexus.core.ir_engine.figure_provider import build_ir_figure_definitions
from polynexus.core.ir_engine.io import IRSpectrum
from polynexus.core.ir_engine.ir_temperature import IRTemp2DResult, IRTempFrame


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


def test_complete_ir_provider_assigns_conservative_standard_publication_roles(ir_complete_results):
    definitions = build_ir_figure_definitions(ir_complete_results)

    assert [item.publication_role for item in definitions] == [
        "main",
        "si",
        "diagnostic",
        "si",
        "main",
    ]


def test_ir_engine_handoff_returns_complete_definitions(ir_complete_results):
    engine = IREngine()
    engine._results = list(ir_complete_results)

    definitions = engine.build_figure_definitions()

    assert {item.figure_id for item in definitions} >= {
        "ir.frame.peak-fit.001",
        "ir.frame.comparison.001",
        "ir.series.crystallinity",
    }


def test_ir_engine_handoff_includes_temperature_2d_definitions():
    engine = IREngine()
    engine._temperature_2d_result = IRTemp2DResult(
        frames=[IRTempFrame(label="H100", temperature_C=100)],
        wavenumber=np.array([1000.0, 1100.0]),
        absorbance_matrix=np.array([[0.1, 0.2]]),
    )

    definitions = engine.build_figure_definitions()

    assert [item.figure_id for item in definitions] == [
        "ir.temperature_2d.heatmap",
    ]


def test_ir_temperature_2d_provider_assigns_main_support_and_diagnostic_roles():
    engine = IREngine()
    engine._temperature_2d_result = IRTemp2DResult(
        frames=[
            IRTempFrame(label="H100", temperature_C=100),
            IRTempFrame(label="H110", temperature_C=110),
        ],
        wavenumber=np.array([1000.0, 1100.0]),
        absorbance_matrix=np.array([[0.1, 0.2], [0.2, 0.3]]),
        band_intensity_vs_frame={"amide": [0.1, 0.2]},
        band_indices_vs_frame={"ratio": [1.0, 1.1]},
        sync_corr=np.eye(2),
        async_corr=np.eye(2),
    )

    definitions = engine.build_figure_definitions()

    assert [item.publication_role for item in definitions] == [
        "main",
        "si",
        "si",
        "diagnostic",
        "diagnostic",
    ]
