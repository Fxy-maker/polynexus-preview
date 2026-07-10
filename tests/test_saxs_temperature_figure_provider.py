import numpy as np
import pytest

from polynexus.core.figures.validation import validate_figure_definition
from polynexus.core.saxs_engine.figure_provider import (
    build_saxs_temperature_definitions,
)
from polynexus.core.saxs_engine.saxs_temperature import TempSeriesResult


@pytest.fixture
def saxs_temperature_inputs():
    result = TempSeriesResult(
        temperatures=np.array([30.0, 80.0]),
        L_array=np.array([12.0, 11.2]),
        lc_array=np.array([4.0, 3.4]),
        lc_effective_array=np.array([4.1, 3.6]),
        Q_star_array=np.array([100.0, 82.0]),
        Xc_array=np.array([1.0, 0.82]),
    )
    q_values = (
        np.array([0.1, 0.2, 0.3, 0.4]),
        np.array([0.12, 0.22, 0.32, 0.42, 0.52]),
    )
    intensities = (
        np.array([100.0, 80.0, 45.0, 20.0]),
        np.array([90.0, 70.0, 38.0, 18.0, 9.0]),
    )
    return result, q_values, intensities


def test_saxs_temperature_provider_emits_per_frame_and_waterfall_definitions(
    saxs_temperature_inputs,
):
    result, q_values, intensities = saxs_temperature_inputs

    definitions = build_saxs_temperature_definitions(result, q_values, intensities)

    assert [item.figure_id for item in definitions[:3]] == [
        "saxs.frame.temperature.scattering.001",
        "saxs.frame.temperature.scattering.002",
        "saxs.series.temperature.waterfall",
    ]
    assert definitions[0].category == "per_frame"
    waterfall = definitions[2]
    assert waterfall.category == "series_overview"
    assert len(waterfall.data_sources) == 2
    assert all(obj["type"] == "plot_series" for obj in waterfall.objects)
    assert waterfall.layout.panels[0].show_legend is True

    for definition in definitions:
        validate_figure_definition(definition)


def test_saxs_temperature_provider_rejects_mismatched_frame_counts(
    saxs_temperature_inputs,
):
    result, q_values, intensities = saxs_temperature_inputs

    with pytest.raises(ValueError, match="temperature frame counts differ"):
        build_saxs_temperature_definitions(result, q_values[:1], intensities)


def test_saxs_temperature_provider_emits_multi_panel_and_heatmap(
    saxs_temperature_inputs,
):
    result, q_values, intensities = saxs_temperature_inputs

    definitions = build_saxs_temperature_definitions(result, q_values, intensities)
    by_id = {item.figure_id: item for item in definitions}

    parameters = by_id["saxs.series.temperature.parameters"]
    assert parameters.layout.rows == 2
    assert parameters.layout.columns == 2
    assert {obj["panel_id"] for obj in parameters.objects} == {
        "long-period",
        "thickness",
        "invariant",
        "crystallinity",
    }
    heatmap = by_id["saxs.series.temperature.heatmap"]
    assert heatmap.objects[0]["type"] == "heatmap"
    assert {column.name for column in heatmap.data_sources[0].columns} == {
        "q_nm1",
        "temperature_C",
        "intensity",
    }

    validate_figure_definition(parameters)
    validate_figure_definition(heatmap)
