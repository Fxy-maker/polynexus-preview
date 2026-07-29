import numpy as np
import pytest
from types import SimpleNamespace

from polynexus.core.figures.validation import validate_figure_definition
from polynexus.core.figures.v2_capabilities import build_v2_definition_artifact
from polynexus.core.saxs import SAXSEngine
from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.figure_provider import (
    build_saxs_figure_definitions,
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
        assert definition.recipe["v2_adapter"] == "temperature_saxs"
        assert build_v2_definition_artifact(definition).capability["v2_runtime"] == "ready"


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


def test_saxs_engine_exposes_temperature_figure_definitions(
    saxs_temperature_inputs,
):
    result, q_values, intensities = saxs_temperature_inputs
    engine = SAXSEngine(config=SAXSConfig(experiment_type="temperature"))
    engine._temperature_result = result
    engine._q_list = list(q_values)
    engine._I_list = list(intensities)

    definitions = engine.build_figure_definitions()

    assert definitions
    assert all(item.technique == "saxs" for item in definitions)
    assert "saxs.series.temperature.heatmap" in {item.figure_id for item in definitions}


def test_saxs_completed_temperature_series_keeps_summary_fallback_when_evolution_gate_fails():
    """Partial evidence must not collapse the gallery to waterfall/evidence only."""

    engine = SAXSEngine(config=SAXSConfig(experiment_type="temperature"))
    q_values = [np.asarray([0.1, 0.2, 0.3]), np.asarray([0.1, 0.2, 0.3])]
    intensities = [np.asarray([10.0, 5.0, 2.0]), np.asarray([9.0, 4.0, 1.5])]
    engine._temperature_result = TempSeriesResult(
        temperatures=np.asarray([30.0, 60.0]),
        L_array=np.asarray([12.0, 11.5]),
        lc_array=np.asarray([4.0, 3.8]),
        lc_effective_array=np.asarray([4.1, 3.9]),
        Q_star_array=np.asarray([100.0, 90.0]),
        Xc_array=np.asarray([0.4, 0.42]),
    )
    engine._q_list = q_values
    engine._I_list = intensities
    engine._conditions = [30.0, 60.0]
    engine._batch_params = [{"file": "frame-30.edf"}, {"file": "frame-60.edf"}]
    engine._batch_results = [
        SimpleNamespace(
            label="frame-30",
            condition_value=30.0,
            q=q_values[0],
            I=intensities[0],
            final_parameters={},
        ),
        SimpleNamespace(
            label="frame-60",
            condition_value=60.0,
            q=q_values[1],
            I=intensities[1],
            final_parameters={},
        ),
    ]
    engine._results = [object(), object()]

    definitions = engine.build_figure_definitions()
    figure_ids = {item.figure_id for item in definitions}

    assert "saxs.series.temperature.parameters" in figure_ids
    assert "saxs.series.temperature.heatmap" in figure_ids


def _saxs_provider_state(**overrides):
    state = {
        "_analysis": None,
        "_batch_results": [],
        "_temperature_result": None,
        "_strain_result": None,
        "_q_list": [],
        "_I_list": [],
        "_conditions": [],
    }
    state.update(overrides)
    return SimpleNamespace(**state)


def _analyzed_saxs_frame(label, q, intensity, smooth=None, condition=np.nan):
    return SimpleNamespace(
        label=label,
        condition_value=condition,
        q=np.asarray(q, dtype=float),
        I=np.asarray(intensity, dtype=float),
        I_smooth=np.asarray(smooth, dtype=float) if smooth is not None else None,
    )


def test_saxs_provider_emits_static_single_profile_from_analyzed_arrays():
    result = _analyzed_saxs_frame(
        "sample-a",
        [0.1, 0.2, 0.3],
        [100.0, 60.0, 20.0],
        smooth=[95.0, 58.0, 19.0],
    )

    definitions = build_saxs_figure_definitions(
        _saxs_provider_state(_analysis=result, _batch_results=[result])
    )

    assert [item.figure_id for item in definitions] == ["saxs.frame.static.scattering.001"]
    profile = definitions[0]
    assert profile.category == "per_frame"
    assert profile.data_sources[0].values == {
        "q_nm1": (0.1, 0.2, 0.3),
        "intensity_au": (95.0, 58.0, 19.0),
    }
    assert profile.recipe["function"] == "build_saxs_figure_definitions"
    validate_figure_definition(profile)


def test_saxs_provider_emits_batch_profiles_and_static_waterfall():
    results = [
        _analyzed_saxs_frame("sample-a", [0.1, 0.2], [100.0, 50.0]),
        _analyzed_saxs_frame("sample-b", [0.1, 0.2], [80.0, 40.0]),
    ]

    definitions = build_saxs_figure_definitions(_saxs_provider_state(_batch_results=results))

    assert [item.figure_id for item in definitions] == [
        "saxs.frame.static.scattering.001",
        "saxs.frame.static.scattering.002",
        "saxs.series.static.waterfall",
    ]
    waterfall = definitions[-1]
    assert [obj["name"] for obj in waterfall.objects] == [
        "sample-a",
        "sample-b",
    ]
    assert len(waterfall.data_sources) == 2
    for definition in definitions:
        validate_figure_definition(definition)


def test_saxs_provider_emits_strain_profiles_and_waterfall_from_loaded_frames():
    strain_result = SimpleNamespace(strains=np.array([0.0, 25.0]))

    definitions = build_saxs_figure_definitions(
        _saxs_provider_state(
            _strain_result=strain_result,
            _q_list=[np.array([0.1, 0.2]), np.array([0.12, 0.22])],
            _I_list=[np.array([100.0, 50.0]), np.array([70.0, 35.0])],
            _conditions=[0.0, 25.0],
        )
    )

    assert [item.figure_id for item in definitions] == [
        "saxs.frame.strain.scattering.001",
        "saxs.frame.strain.scattering.002",
        "saxs.series.strain.waterfall",
    ]
    assert [obj["name"] for obj in definitions[-1].objects] == [
        "0% strain",
        "25% strain",
    ]
    assert all(
        definition.recipe["function"] == "build_saxs_figure_definitions"
        for definition in definitions
    )
    for definition in definitions:
        validate_figure_definition(definition)


def test_dirty_projection_legacy_temperature_frame_keeps_valid_pairs(
    saxs_temperature_inputs,
):
    result, q_values, intensities = saxs_temperature_inputs
    q_values = list(q_values)
    intensities = list(intensities)
    q_values[0] = np.asarray(
        ["0.1", "bad-q", "0.3", "0.4"],
        dtype=object,
    )
    intensities[0] = np.asarray(
        ["100.0", "80.0", "bad-intensity", "20.0"],
        dtype=object,
    )

    definitions = build_saxs_temperature_definitions(
        result,
        q_values,
        intensities,
    )
    source = definitions[0].data_sources[0]

    assert source.values["q_nm1"] == (0.1, 0.4)
    assert source.values["intensity_au"] == (100.0, 20.0)
