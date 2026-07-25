import numpy as np
import pytest

from polynexus.core.figures.validation import validate_figure_definition
from polynexus.core.figures.v2_capabilities import build_v2_definition_artifact
from polynexus.core.ir import IREngine
from polynexus.core.ir_engine.core import IRResult
from polynexus.core.ir_engine.figure_provider import (
    build_ir_figure_definitions,
    build_ir_temperature_2d_figure_definitions,
)
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


def test_ir_temperature_2d_definitions_preserve_frame_condition_metadata():
    result = IRTemp2DResult(
        frames=[
            IRTempFrame(
                label="H100",
                stage="heating",
                temperature_C=100.0,
                time_min=2.5,
                sequence_order_source="metadata",
            ),
            IRTempFrame(
                label="H110",
                stage="hold",
                temperature_C=110.0,
                time_min=5.0,
                sequence_order_source="metadata",
            ),
        ],
        wavenumber=np.array([1000.0, 1100.0]),
        absorbance_matrix=np.array([[0.1, 0.2], [0.2, 0.3]]),
        band_intensity_vs_frame={"amide": [0.1, 0.2]},
    )

    definitions = build_ir_temperature_2d_figure_definitions(result)
    heatmap = definitions[0]
    source = heatmap.data_sources[0]

    assert [column.name for column in source.columns] == [
        "wavenumber_cm1",
        "frame_index",
        "temperature_C",
        "time_min",
        "absorbance",
    ]
    assert source.values["temperature_C"] == (100.0, 100.0, 110.0, 110.0)
    assert heatmap.recipe["frame_metadata"] == [
        {
            "frame_index": 0,
            "label": "H100",
            "stage": "heating",
            "temperature_C": 100.0,
            "time_min": 2.5,
            "time_estimated": False,
            "sequence_order_source": "metadata",
        },
        {
            "frame_index": 1,
            "label": "H110",
            "stage": "hold",
            "temperature_C": 110.0,
            "time_min": 5.0,
            "time_estimated": False,
            "sequence_order_source": "metadata",
        },
    ]

    tracking = definitions[1]
    tracking_source = tracking.data_sources[0]
    assert [column.name for column in tracking_source.columns] == [
        "frame_index",
        "temperature_C",
        "time_min",
        "value",
    ]
    assert tracking_source.values["temperature_C"] == (100.0, 110.0)
