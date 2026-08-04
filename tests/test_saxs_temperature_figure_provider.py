import json

import numpy as np
import pytest
from types import SimpleNamespace

from polynexus.core.figures.pipeline import FigurePipeline
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


def test_saxs_temperature_guinier_diagnostic_figure_preserves_frame_evidence():
    result = TempSeriesResult(
        temperatures=np.asarray([30.0, 60.0, 90.0]),
        L_array=np.asarray([12.0, 11.5, 10.8]),
        lc_array=np.asarray([4.0, 3.8, 3.2]),
        lc_effective_array=np.asarray([4.1, 3.9, 3.3]),
        Q_star_array=np.asarray([100.0, 92.0, 81.0]),
        Xc_array=np.asarray([0.4, 0.38, 0.3]),
        Rg_array=np.asarray([4.2, np.nan, 5.1]),
        guinier_level_array=["Quantitative", "Unusable", "Diagnostic"],
        guinier_sequence_evidence={
            "level": "Diagnostic",
            "reason_codes": ["guinier_sequence_missing_frames"],
        },
        temp_points=[
            SimpleNamespace(
                source_index=7,
                guinier_level="Quantitative",
                guinier_reason_codes=["fit_ok"],
            ),
            SimpleNamespace(
                source_index=3,
                guinier_level="Unusable",
                guinier_reason_codes=["guinier_fit_failed"],
            ),
            SimpleNamespace(
                source_index=5,
                guinier_level="Diagnostic",
                guinier_reason_codes=["qrg_gate_failed"],
            ),
        ],
    )
    before_rg = result.Rg_array.copy()
    definitions = build_saxs_temperature_definitions(
        result,
        (np.asarray([0.1, 0.2, 0.3]),) * 3,
        (np.asarray([10.0, 5.0, 2.0]),) * 3,
    )

    figure = next(
        item
        for item in definitions
        if item.figure_id == "saxs.series.temperature.guinier"
    )
    source = figure.data_sources[0]
    assert figure.publication_role == "diagnostic"
    assert source.values["temperature_C"] == (30.0, 60.0, 90.0)
    assert source.values["Rg_nm"] == (4.2, None, 5.1)
    assert source.values["source_index"] == (7, 3, 5)
    assert source.values["frame_level"] == (
        "Quantitative",
        "Unusable",
        "Diagnostic",
    )
    assert source.values["frame_reason_codes"] == (
        "fit_ok",
        "guinier_fit_failed",
        "qrg_gate_failed",
    )
    assert figure.recipe["parameters"]["missing_values_preserved"] is True
    assert figure.recipe["parameters"]["interpolation"] is False
    json.dumps(dict(source.values), allow_nan=False)
    validate_figure_definition(figure)
    assert build_v2_definition_artifact(figure).capability["v2_runtime"] == "ready"
    assert np.array_equal(result.Rg_array, before_rg, equal_nan=True)


def test_saxs_temperature_method_evidence_diagnostic_figure_preserves_frames():
    result = TempSeriesResult(
        temperatures=np.asarray([30.0, 60.0, 90.0]),
        L_array=np.asarray([12.0, 11.5, 10.8]),
        lc_array=np.asarray([4.0, 3.8, 3.2]),
        lc_effective_array=np.asarray([4.1, 3.9, 3.3]),
        Q_star_array=np.asarray([100.0, 92.0, 81.0]),
        Xc_array=np.asarray([0.4, 0.38, 0.3]),
        temp_points=[
            SimpleNamespace(
                source_index=7,
                metric_evidence={
                    "porod": {
                        "value": 1.2,
                        "level": "Trend",
                        "reason_codes": ["porod_slope_deviation_observed"],
                    },
                    "kratky": {
                        "value": 0.3,
                        "level": "Trend",
                        "reason_codes": [],
                    },
                    "invariant": {
                        "value": 100.0,
                        "level": "Trend",
                        "reason_codes": [],
                    },
                    "lamellar": {
                        "value": 12.0,
                        "level": "Diagnostic",
                        "reason_codes": ["lamellar_phi_c_invalid"],
                    },
                },
            ),
            SimpleNamespace(
                source_index=3,
                metric_evidence={
                    "porod": {
                        "value": None,
                        "level": "Unusable",
                        "reason_codes": ["porod_payload_missing"],
                    },
                    "kratky": None,
                    "invariant": {
                        "value": 92.0,
                        "level": "Trend",
                        "reason_codes": [],
                    },
                    "lamellar": {
                        "value": 11.5,
                        "level": "Trend",
                        "reason_codes": [],
                    },
                },
            ),
            SimpleNamespace(
                source_index=5,
                metric_evidence={
                    "porod": {
                        "value": 0.9,
                        "level": "Trend",
                        "reason_codes": [],
                    },
                    "kratky": {
                        "value": 0.2,
                        "level": "Diagnostic",
                        "reason_codes": ["kratky_peak_missing"],
                    },
                    "invariant": {
                        "value": 81.0,
                        "level": "Trend",
                        "reason_codes": [],
                    },
                    "lamellar": {
                        "value": 10.8,
                        "level": "Trend",
                        "reason_codes": [],
                    },
                },
            ),
        ],
    )
    definitions = build_saxs_temperature_definitions(
        result,
        (np.asarray([0.1, 0.2, 0.3]),) * 3,
        (np.asarray([10.0, 5.0, 2.0]),) * 3,
    )

    figure = next(
        item
        for item in definitions
        if item.figure_id == "saxs.series.temperature.method_evidence"
    )
    assert figure.publication_role == "diagnostic"
    audit_sources = {
        source.source_id: source
        for source in figure.data_sources
        if source.role == "method_evidence_audit"
    }
    assert set(audit_sources) == {
        "temperature-method-evidence-porod",
        "temperature-method-evidence-kratky",
        "temperature-method-evidence-invariant",
        "temperature-method-evidence-lamellar",
    }
    porod = audit_sources["temperature-method-evidence-porod"]
    assert porod.values["temperature_C"] == (30.0, 60.0, 90.0)
    assert porod.values["value"] == (1.2, None, 0.9)
    assert porod.values["source_index"] == (7, 3, 5)
    assert porod.values["frame_level"] == ("Trend", "Unusable", "Trend")
    assert porod.values["frame_reason_codes"] == (
        "porod_slope_deviation_observed",
        "porod_payload_missing",
        None,
    )
    plot_sources = {
        source.source_id: source
        for source in figure.data_sources
        if source.role == "method_evidence_plot"
    }
    assert plot_sources["temperature-method-evidence-porod-plot"].values == {
        "temperature_C": (30.0, 90.0),
        "value": (1.2, 0.9),
    }
    assert plot_sources["temperature-method-evidence-kratky-plot"].values == {
        "temperature_C": (30.0, 90.0),
        "value": (0.3, 0.2),
    }
    assert figure.recipe["parameters"]["missing_values_preserved"] is True
    assert figure.recipe["parameters"]["interpolation"] is False
    assert figure.recipe["parameters"]["reclassification"] is False
    json.dumps(
        {
            source.source_id: dict(source.values)
            for source in figure.data_sources
        },
        allow_nan=False,
    )
    result.temp_points[0].metric_evidence["porod"]["value"] = 99.0
    assert porod.values["value"] == (1.2, None, 0.9)
    validate_figure_definition(figure)
    assert build_v2_definition_artifact(figure).capability["v2_runtime"] == "ready"


def test_saxs_temperature_provider_omits_empty_method_evidence_figure(
    saxs_temperature_inputs,
):
    result, q_values, intensities = saxs_temperature_inputs
    result.temp_points = [SimpleNamespace(source_index=0, metric_evidence=None)]

    definitions = build_saxs_temperature_definitions(result, q_values, intensities)

    assert "saxs.series.temperature.method_evidence" not in {
        item.figure_id for item in definitions
    }


def test_saxs_temperature_provider_keeps_legacy_results_without_rg_figure(
    saxs_temperature_inputs,
):
    result, q_values, intensities = saxs_temperature_inputs
    definitions = build_saxs_temperature_definitions(result, q_values, intensities)

    assert "saxs.series.temperature.guinier" not in {
        item.figure_id for item in definitions
    }


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


def test_legacy_v2_saxs_lifecycle_is_ready_for_all_modes(tmp_path) -> None:
    cases = (
        (
            "static",
            "saxs_static",
            build_saxs_figure_definitions(
                _saxs_provider_state(
                    _batch_results=[
                        _analyzed_saxs_frame("a", [0.1, 0.2], [10.0, 5.0]),
                        _analyzed_saxs_frame("b", [0.1, 0.2], [9.0, 4.0]),
                    ]
                )
            ),
        ),
        (
            "strain",
            "saxs_strain",
            build_saxs_figure_definitions(
                _saxs_provider_state(
                    _strain_result=SimpleNamespace(
                        strains=np.asarray([0.0, 25.0])
                    ),
                    _q_list=[np.asarray([0.1, 0.2]), np.asarray([0.1, 0.2])],
                    _I_list=[np.asarray([10.0, 5.0]), np.asarray([9.0, 4.0])],
                    _conditions=[0.0, 25.0],
                )
            ),
        ),
        (
            "temperature",
            "temperature_saxs",
            build_saxs_temperature_definitions(
                TempSeriesResult(
                    temperatures=np.asarray([30.0, 60.0]),
                    L_array=np.asarray([12.0, 11.0]),
                    lc_array=np.asarray([4.0, 3.0]),
                    lc_effective_array=np.asarray([4.0, 3.0]),
                    Q_star_array=np.asarray([100.0, 90.0]),
                    Xc_array=np.asarray([0.4, 0.42]),
                ),
                (np.asarray([0.1, 0.2, 0.3]),) * 2,
                (np.asarray([10.0, 5.0, 2.0]),) * 2,
            ),
        ),
    )

    for mode, adapter, definitions in cases:
        assert definitions
        assert all(item.recipe["v2_adapter"] == adapter for item in definitions)
        assert all(
            build_v2_definition_artifact(item).capability["v2_runtime"] == "ready"
            for item in definitions
        )
        manifest = FigurePipeline().run(
            output_root=tmp_path,
            run_id=f"legacy-saxs-v2-{mode}",
            technique="saxs",
            definitions=(definitions[0],),
        )
        entry = manifest.figures[0]
        assert entry.status == "ready"
        assert entry.capability_report["v2_runtime"] == "ready"
        assert (
            tmp_path
            / "runs"
            / f"legacy-saxs-v2-{mode}"
            / entry.capability_report["v2_sidecar"]
        ).is_file()


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
        "saxs.series.static.kratky",
    ]
    waterfall = next(item for item in definitions if item.figure_id == "saxs.series.static.waterfall")
    assert [obj["name"] for obj in waterfall.objects] == [
        "sample-a",
        "sample-b",
    ]
    assert len(waterfall.data_sources) == 2
    kratky = next(item for item in definitions if item.figure_id == "saxs.series.static.kratky")
    assert all(obj["y_column"] == "intensity_q2" for obj in kratky.objects)
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
        "saxs.series.strain.kratky",
    ]
    waterfall = next(item for item in definitions if item.figure_id == "saxs.series.strain.waterfall")
    assert [obj["name"] for obj in waterfall.objects] == [
        "0% strain",
        "25% strain",
    ]
    kratky = next(item for item in definitions if item.figure_id == "saxs.series.strain.kratky")
    assert all(obj["y_column"] == "intensity_q2" for obj in kratky.objects)
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


def test_legacy_temperature_provider_omits_unplottable_frame_with_evidence(
    saxs_temperature_inputs,
):
    result, q_values, intensities = saxs_temperature_inputs
    q_values = list(q_values)
    intensities = list(intensities)
    q_values[1] = np.asarray(["bad-q", "also-bad"], dtype=object)
    intensities[1] = np.asarray(["bad-intensity", "still-bad"], dtype=object)

    definitions = build_saxs_temperature_definitions(
        result,
        q_values,
        intensities,
    )

    frame_ids = {item.figure_id for item in definitions}
    assert "saxs.frame.temperature.scattering.001" in frame_ids
    assert "saxs.frame.temperature.scattering.002" not in frame_ids
    parameters = next(
        item
        for item in definitions
        if item.figure_id == "saxs.series.temperature.parameters"
    )
    assert parameters.data_sources[0].values["temperature_C"] == (30.0,)
    evidence = parameters.recipe["evidence"]
    assert evidence["included_frame_indices"] == [0]
    assert evidence["omitted_frame_indices"] == [1]
    assert evidence["omission_reasons"][1] == "figure_profile_unavailable"


def test_legacy_condition_axis_dirty_values_keep_frame_order():
    conditions = ["0", "bad-strain", "25"]
    state = _saxs_provider_state(
        _strain_result=SimpleNamespace(strains=None),
        _q_list=[np.asarray([0.1, 0.2])] * 3,
        _I_list=[np.asarray([10.0, 5.0])] * 3,
        _conditions=conditions,
    )

    definitions = build_saxs_figure_definitions(state)

    assert [item.figure_id for item in definitions] == [
        "saxs.frame.strain.scattering.001",
        "saxs.frame.strain.scattering.002",
        "saxs.frame.strain.scattering.003",
        "saxs.series.strain.waterfall",
        "saxs.series.strain.kratky",
    ]
    assert [item.title for item in definitions[:3]] == [
        "SAXS Scattering - 0% strain",
        "SAXS Scattering - Frame 2",
        "SAXS Scattering - 25% strain",
    ]
    assert conditions == ["0", "bad-strain", "25"]


def test_dirty_temperature_axis_preserves_frame_positions_and_marks_missing_condition(
    saxs_temperature_inputs,
):
    result, q_values, intensities = saxs_temperature_inputs
    result.temperatures = np.asarray(["30", "bad-temperature"], dtype=object)

    definitions = build_saxs_temperature_definitions(result, q_values, intensities)

    assert [item.figure_id for item in definitions[:2]] == [
        "saxs.frame.temperature.scattering.001",
        "saxs.frame.temperature.scattering.002",
    ]
    assert definitions[1].title == "SAXS Scattering At Frame 2"
    assert definitions[1].recipe["inputs"]["temperature_C"] is None

    by_id = {item.figure_id: item for item in definitions}
    parameter_values = by_id["saxs.series.temperature.parameters"].data_sources[0].values[
        "temperature_C"
    ]
    heatmap_values = by_id["saxs.series.temperature.heatmap"].data_sources[0].values[
        "temperature_C"
    ]
    assert parameter_values[0] == 30.0
    assert np.isnan(parameter_values[1])
    assert heatmap_values[:5] == (30.0,) * 5
    assert all(np.isnan(value) for value in heatmap_values[5:])

    for definition in definitions:
        validate_figure_definition(definition)


def test_dirty_temperature_derived_arrays_preserve_metric_positions_and_fallback(
    saxs_temperature_inputs,
):
    result, q_values, intensities = saxs_temperature_inputs
    result.L_array = np.asarray(["12.0", "bad-long-period"], dtype=object)
    result.lc_array = np.asarray(["4.0", "bad-raw-lc"], dtype=object)
    result.lc_effective_array = np.asarray(["4.1", "bad-effective-lc"], dtype=object)
    result.Q_star_array = np.asarray(["100.0", "bad-invariant"], dtype=object)
    result.Xc_array = np.asarray(["0.4", "bad-crystallinity"], dtype=object)

    definitions = build_saxs_temperature_definitions(result, q_values, intensities)

    parameters = next(
        item
        for item in definitions
        if item.figure_id == "saxs.series.temperature.parameters"
    )
    values = parameters.data_sources[0].values

    assert values["L_nm"][0] == 12.0
    assert np.isnan(values["L_nm"][1])
    assert values["lc_nm"][0] == 4.1
    assert np.isnan(values["lc_nm"][1])
    assert values["Q_star"][0] == 100.0
    assert np.isnan(values["Q_star"][1])
    assert values["crystallinity_fraction"][0] == 0.4
    assert np.isnan(values["crystallinity_fraction"][1])
    metric_keys = ("L_nm", "lc_nm", "la_nm", "Q_star", "crystallinity_fraction")
    assert all(np.isnan(values[key][1]) for key in metric_keys)

    for definition in definitions:
        validate_figure_definition(definition)
