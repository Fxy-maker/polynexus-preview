from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np

from polynexus.core.saxs_engine.figure_temperature import (
    build_temperature_figure_definitions,
)
from polynexus.core.saxs_engine.figure_provider import build_saxs_figure_definitions
from polynexus.core.saxs_engine.saxs_temperature import TempSeriesResult


def _temperature_engine(
    *,
    frame_count: int = 3,
    avrami: dict[str, object] | None = None,
    completed_results: bool = False,
) -> SimpleNamespace:
    q = np.asarray([0.08, 0.12, 0.18, 0.25], dtype=float)
    intensities = [
        np.asarray([8.0, 6.0, 3.0, 1.0], dtype=float) * (1.0 + index * 0.05)
        for index in range(frame_count)
    ]
    parameters = [
        {
            "quality_flag": "OK",
            "L_nm": 12.0 + index,
            "lc_nm": 4.0 + index * 0.2,
            "la_nm": 8.0 + index * 0.8,
            "q_star_nm1": 0.45 + index * 0.01,
            "Xc_effective": 0.4 + index * 0.05,
        }
        for index in range(frame_count)
    ]
    analyses = [
        SimpleNamespace(
            label=f"frame-{index}",
            correlation={"r": [1.0, 2.0, 3.0], "gamma": [0.8, 0.5, 0.2]},
            idf={"r_idf": [1.0, 2.0, 3.0], "idf": [0.2, 0.4, 0.3]},
            final_parameters=parameters[index],
        )
        for index in range(frame_count)
    ]
    result = TempSeriesResult(
        temperatures=np.arange(frame_count, dtype=float),
        L_array=np.asarray([item["L_nm"] for item in parameters], dtype=float),
        lc_array=np.asarray([item["lc_nm"] for item in parameters], dtype=float),
        lc_effective_array=np.asarray([item["lc_nm"] for item in parameters], dtype=float),
        Q_star_array=np.asarray([1.0, 1.1, 1.2][:frame_count], dtype=float),
        Xc_array=np.asarray([item["Xc_effective"] for item in parameters], dtype=float),
        avrami=avrami or {},
    )
    return SimpleNamespace(
        _temperature_result=result,
        _batch_results=analyses,
        _batch_params=parameters,
        _q_list=[q.copy() for _ in range(frame_count)],
        _I_list=intensities,
        _conditions=np.arange(frame_count, dtype=float),
        _file_list=[f"frame-{index}.dat" for index in range(frame_count)],
        _condition_type="temperature",
        _results=[object()] if completed_results else [],
        cfg=SimpleNamespace(
            experiment_type="temperature",
            condition_label="Time",
            condition_unit="s",
        ),
    )


def test_temperature_panels_keep_publication_order_and_roles() -> None:
    definitions = build_temperature_figure_definitions(
        _temperature_engine(
            avrami={
                "valid": True,
                "n": 2.1,
                "k_sn": 0.03,
                "t_half_s": 4.0,
            }
        )
    )

    assert [definition.figure_id for definition in definitions[:3]] == [
        "saxs.temperature.evolution",
        "saxs.temperature.avrami",
        "saxs.temperature.waterfall",
    ]
    assert [definition.display_order for definition in definitions[:3]] == [10, 20, 100]
    assert definitions[0].publication_role == "main"
    assert definitions[1].publication_role == "main"
    assert definitions[2].publication_role == "si"
    assert all(
        definition.display_order >= 200
        and definition.publication_role in {"si", "diagnostic"}
        for definition in definitions
        if definition.figure_id.startswith("saxs.temperature.evidence.")
    )


def test_temperature_fallback_keeps_waterfall_and_adds_only_si_summary() -> None:
    definitions = build_saxs_figure_definitions(
        _temperature_engine(
            frame_count=2,
            completed_results=True,
            avrami={"valid": False},
        )
    )
    by_id = {definition.figure_id: definition for definition in definitions}

    assert "saxs.temperature.evolution" not in by_id
    assert "saxs.temperature.avrami" not in by_id
    assert by_id["saxs.temperature.waterfall"].publication_role == "si"
    assert by_id["saxs.series.temperature.parameters"].publication_role == "si"
    assert by_id["saxs.series.temperature.heatmap"].publication_role == "si"
    assert by_id["saxs.series.temperature.parameters"].display_order == 110
    assert by_id["saxs.series.temperature.heatmap"].display_order == 120
    assert all(
        definition.publication_role != "main"
        for definition in definitions
        if definition.figure_id.startswith("saxs.temperature.evidence.")
    )


def _method_metric(value, level, reason_codes=()):
    return {
        "value": value,
        "level": level,
        "reason_codes": list(reason_codes),
    }


def _production_method_evidence_engine(*, duplicate_source_index: bool = False):
    engine = _temperature_engine()
    engine.cfg.condition_label = "Temperature"
    engine.cfg.condition_unit = "C"
    points = [
        SimpleNamespace(
            source_index=2,
            metric_evidence={
                "porod": _method_metric(0.9, "Trend"),
                "kratky": _method_metric(0.2, "Diagnostic", ("kratky_peak_missing",)),
                "invariant": _method_metric(81.0, "Trend"),
                "lamellar": _method_metric(10.8, "Trend"),
            },
        ),
        SimpleNamespace(
            source_index=0,
            metric_evidence={
                "porod": _method_metric(1.2, "Trend", ("porod_slope_deviation_observed",)),
                "kratky": _method_metric(0.3, "Trend"),
                "invariant": _method_metric(100.0, "Trend"),
                "lamellar": _method_metric(12.0, "Diagnostic", ("lamellar_phi_c_invalid",)),
            },
        ),
        SimpleNamespace(
            source_index=1,
            metric_evidence={
                "porod": _method_metric(None, "Unusable", ("porod_payload_missing",)),
                "kratky": None,
                "invariant": _method_metric(92.0, "Trend"),
                "lamellar": _method_metric(11.5, "Trend"),
            },
        ),
    ]
    if duplicate_source_index:
        points.insert(
            1,
            SimpleNamespace(
                source_index=0,
                metric_evidence={
                    "porod": _method_metric(99.0, "Trend"),
                },
            ),
        )
    engine._temperature_result.temp_points = points
    return engine


def test_production_temperature_method_evidence_figure_binds_by_source_index():
    engine = _production_method_evidence_engine()

    definitions = build_temperature_figure_definitions(engine)

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
        "saxs-temperature-method-evidence-porod",
        "saxs-temperature-method-evidence-kratky",
        "saxs-temperature-method-evidence-invariant",
        "saxs-temperature-method-evidence-lamellar",
    }
    porod = audit_sources["saxs-temperature-method-evidence-porod"]
    assert porod.values["temperature_C"] == (0.0, 1.0, 2.0)
    assert porod.values["value"] == (1.2, None, 0.9)
    assert porod.values["source_index"] == (0, 1, 2)
    assert porod.values["frame_level"] == ("Trend", "Unusable", "Trend")
    assert porod.values["frame_reason_codes"] == (
        "porod_slope_deviation_observed",
        "porod_payload_missing",
        None,
    )
    plot = next(
        source
        for source in figure.data_sources
        if source.source_id == "saxs-temperature-method-evidence-porod-plot"
    )
    assert plot.values == {
        "temperature_C": (0.0, 2.0),
        "value": (1.2, 0.9),
    }
    assert figure.recipe["parameters"]["missing_values_preserved"] is True
    assert figure.recipe["parameters"]["interpolation"] is False
    assert figure.recipe["parameters"]["reclassification"] is False
    json.dumps(
        {source.source_id: dict(source.values) for source in figure.data_sources},
        allow_nan=False,
    )
    assert definitions[0].figure_id == "saxs.temperature.evolution"


def test_production_temperature_method_evidence_duplicate_source_fails_closed():
    engine = _production_method_evidence_engine(duplicate_source_index=True)

    definitions = build_temperature_figure_definitions(engine)

    figure = next(
        item
        for item in definitions
        if item.figure_id == "saxs.series.temperature.method_evidence"
    )
    porod = next(
        source
        for source in figure.data_sources
        if source.source_id == "saxs-temperature-method-evidence-porod"
    )
    assert porod.values["value"] == (None, None, 0.9)
    assert porod.values["source_index"] == (None, 1, 2)
    plot = next(
        source
        for source in figure.data_sources
        if source.source_id == "saxs-temperature-method-evidence-porod-plot"
    )
    assert plot.values == {
        "temperature_C": (2.0,),
        "value": (0.9,),
    }


def test_dirty_projection_temperature_waterfall_keeps_valid_pairs() -> None:
    engine = _temperature_engine()
    engine._q_list[0] = np.asarray(
        ["0.08", "bad-q", "0.18", "0.25"],
        dtype=object,
    )
    engine._I_list[0] = np.asarray(
        ["8.0", "6.0", "bad-intensity", "1.0"],
        dtype=object,
    )
    q_before = engine._q_list[0].copy()
    intensity_before = engine._I_list[0].copy()

    definitions = build_temperature_figure_definitions(engine)
    waterfall = next(
        item
        for item in definitions
        if item.figure_id == "saxs.temperature.waterfall"
    )
    source = next(
        item
        for item in waterfall.data_sources
        if item.source_id == "saxs-temperature-waterfall-000"
    )

    assert source.values["q_nm1"] == (0.08, 0.25)
    assert source.values["intensity_offset"] == (8.0, 1.0)
    assert np.array_equal(engine._q_list[0], q_before)
    assert np.array_equal(engine._I_list[0], intensity_before)


def test_dirty_temperature_profile_records_pair_provenance() -> None:
    engine = _temperature_engine()
    engine._q_list[0] = np.asarray([0.08, np.nan, 0.18, 0.25], dtype=float)
    engine._I_list[0] = np.asarray([8.0, 6.0, np.inf, 1.0], dtype=float)

    definitions = build_temperature_figure_definitions(engine)
    evolution = next(
        item for item in definitions if item.figure_id == "saxs.temperature.evolution"
    )
    waterfall = next(
        item for item in definitions if item.figure_id == "saxs.temperature.waterfall"
    )
    expected = {
        "input_pair_count": 4,
        "retained_pair_count": 2,
        "nonfinite_pair_count": 2,
        "nonpositive_intensity_pair_count": 0,
        "status": "partial_invalid",
    }

    assert evolution.recipe["parameters"]["profile_projection_quality"]["0"] == expected
    assert waterfall.recipe["parameters"]["profile_projection_quality"]["0"] == expected
    json.dumps(evolution.recipe, allow_nan=False)
    json.dumps(waterfall.recipe, allow_nan=False)


def test_clean_temperature_profile_records_complete_provenance() -> None:
    definitions = build_temperature_figure_definitions(_temperature_engine())
    expected = {
        "input_pair_count": 4,
        "retained_pair_count": 4,
        "nonfinite_pair_count": 0,
        "nonpositive_intensity_pair_count": 0,
        "status": "complete",
    }

    for figure_id in ("saxs.temperature.evolution", "saxs.temperature.waterfall"):
        definition = next(item for item in definitions if item.figure_id == figure_id)
        assert definition.recipe["parameters"]["profile_projection_quality"]["0"] == expected
        json.dumps(definition.recipe, allow_nan=False)


def test_dirty_projection_temperature_trace_keeps_valid_pairs() -> None:
    engine = _temperature_engine()
    engine._batch_results[0].correlation = {
        "r": np.asarray(["1.0", "bad-r", "3.0", "4.0"], dtype=object),
        "gamma": np.asarray(["0.8", "0.5", "0.2", "bad-gamma"], dtype=object),
    }

    definitions = build_temperature_figure_definitions(engine)
    evidence = next(
        item
        for item in definitions
        if item.figure_id == "saxs.temperature.evidence.000"
    )
    source = next(
        item
        for item in evidence.data_sources
        if item.source_id == "saxs-temperature-correlation-000"
    )

    assert source.values["r_nm"] == (1.0, 3.0)
    assert source.values["gamma"] == (0.8, 0.2)


def test_temperature_auxiliary_provenance_records_dirty_avrami_and_traces() -> None:
    engine = _temperature_engine(
        avrami={
            "valid": True,
            "n": 2.1,
            "k_sn": 0.03,
            "t_half_s": 4.0,
        }
    )
    engine._conditions[1] = np.nan
    engine._batch_results[1].final_parameters["Xc_effective"] = "bad-xc"
    engine._batch_results[0].correlation = {
        "r": np.asarray(["1.0", "bad-r", "3.0", "4.0"], dtype=object),
        "gamma": np.asarray(["0.8", "0.5", "bad-gamma", "0.2"], dtype=object),
    }
    engine._batch_results[0].idf = {
        "r_idf": np.asarray(["1.0", "2.0", "bad-r", "4.0"], dtype=object),
        "idf": np.asarray(["0.2", "bad-idf", "0.3", "0.4"], dtype=object),
    }

    definitions = build_temperature_figure_definitions(engine)
    avrami = next(
        item for item in definitions if item.figure_id == "saxs.temperature.avrami"
    )
    evidence = next(
        item
        for item in definitions
        if item.figure_id == "saxs.temperature.evidence.000"
    )

    assert avrami.recipe["parameters"]["avrami_projection_quality"] == {
        "input_pair_count": 3,
        "retained_pair_count": 2,
        "nonfinite_pair_count": 1,
        "status": "partial_nonfinite",
    }
    expected_trace = {
        "input_pair_count": 4,
        "retained_pair_count": 2,
        "nonfinite_pair_count": 2,
        "status": "partial_nonfinite",
    }
    assert evidence.recipe["parameters"]["trace_projection_quality"] == {
        "correlation": expected_trace,
        "idf": expected_trace,
    }
    json.dumps(avrami.recipe, allow_nan=False)
    json.dumps(evidence.recipe, allow_nan=False)


def test_temperature_auxiliary_provenance_records_complete_avrami_and_traces() -> None:
    definitions = build_temperature_figure_definitions(
        _temperature_engine(
            avrami={
                "valid": True,
                "n": 2.1,
                "k_sn": 0.03,
                "t_half_s": 4.0,
            }
        )
    )
    avrami = next(
        item for item in definitions if item.figure_id == "saxs.temperature.avrami"
    )
    evidence = next(
        item
        for item in definitions
        if item.figure_id == "saxs.temperature.evidence.000"
    )
    expected_avrami = {
        "input_pair_count": 3,
        "retained_pair_count": 3,
        "nonfinite_pair_count": 0,
        "status": "complete",
    }
    expected_trace = {
        "input_pair_count": 3,
        "retained_pair_count": 3,
        "nonfinite_pair_count": 0,
        "status": "complete",
    }

    assert avrami.recipe["parameters"]["avrami_projection_quality"] == expected_avrami
    assert evidence.recipe["parameters"]["trace_projection_quality"] == {
        "correlation": expected_trace,
        "idf": expected_trace,
    }
    json.dumps(avrami.recipe, allow_nan=False)
    json.dumps(evidence.recipe, allow_nan=False)
