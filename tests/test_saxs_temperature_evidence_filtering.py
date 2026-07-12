from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from polynexus.core.saxs_engine.figure_provider import build_saxs_figure_definitions


def _temperature_engine_with_evidence(rejected_index: int = 2):
    conditions = [30.0, 45.0, 60.0, 75.0, 90.0]
    q_list = [np.asarray([0.1, 0.2, 0.3])] * len(conditions)
    intensity_list = [np.asarray([10.0, 5.0, 2.0])] * len(conditions)
    params = []
    analyses = []
    for index, condition in enumerate(conditions):
        evidence = {
            "paper_figure_candidate": index != rejected_index,
            "lc_reliability_status": "usable" if index != rejected_index else "low_confidence",
            "Q_star_valid": index != rejected_index,
            "L_nm": 12.125 + index * 0.225,
            "lc_nm": 3.225 + index * 0.125,
            "Q_star": 102.5 + index * 1.75,
            "Xc": 0.265 + index * 0.0125,
            "file": f"frame_{index}.dat",
        }
        params.append(evidence)
        analyses.append(
            SimpleNamespace(
                label=f"frame-{index}",
                condition_value=condition,
                q=q_list[index],
                I=intensity_list[index],
                final_parameters=dict(evidence),
                structure=SimpleNamespace(L=90.0 + index, lc=40.0 + index),
            )
        )
    result = SimpleNamespace(
        temperatures=np.asarray(conditions),
        L_array=np.asarray([item["L_nm"] for item in params]),
        lc_array=np.asarray([item["lc_nm"] for item in params]),
        lc_effective_array=np.asarray([item["lc_nm"] for item in params]),
        Q_star_array=np.asarray([item["Q_star"] for item in params]),
        Xc_array=np.asarray([item["Xc"] for item in params]),
    )
    return SimpleNamespace(
        _temperature_result=result,
        _strain_result=None,
        _condition_type="temperature",
        cfg=SimpleNamespace(experiment_type="temperature"),
        _q_list=q_list,
        _I_list=intensity_list,
        _batch_results=analyses,
        _batch_params=params,
        _conditions=conditions,
        _file_list=[item["file"] for item in params],
    )


def _definition(definitions, figure_id: str):
    return next(item for item in definitions if item.figure_id == figure_id)


def test_temperature_main_sources_omit_rejected_middle_frame():
    engine = _temperature_engine_with_evidence(rejected_index=2)

    definitions = build_saxs_figure_definitions(engine)
    parameters = _definition(definitions, "saxs.series.temperature.parameters")
    source = parameters.data_sources[0]

    assert source.values["temperature_C"] == (30.0, 45.0, 75.0, 90.0)
    assert source.values["L_nm"] == (12.125, 12.35, 12.8, 13.025)
    assert parameters.publication_role == "main"


def test_temperature_missing_evidence_keeps_summary_supplementary():
    engine = _temperature_engine_with_evidence()
    for params in engine._batch_params:
        params.pop("paper_figure_candidate", None)
        params.pop("lc_reliability_status", None)
        params["quality_flag"] = "WARN:low_snr"
    for analysis, params in zip(engine._batch_results, engine._batch_params):
        analysis.final_parameters = dict(params)

    parameters = _definition(
        build_saxs_figure_definitions(engine),
        "saxs.series.temperature.parameters",
    )

    assert parameters.publication_role == "si"
    assert parameters.recipe["evidence"]["included_frame_indices"] == [0, 1, 2, 3, 4]
    assert parameters.recipe["evidence"]["omitted_frame_indices"] == []


def test_temperature_evidence_recipe_records_rejection_reason():
    definitions = build_saxs_figure_definitions(_temperature_engine_with_evidence())
    parameters = _definition(definitions, "saxs.series.temperature.parameters")

    evidence = parameters.recipe["evidence"]
    assert evidence["included_frame_indices"] == [0, 1, 3, 4]
    assert evidence["omitted_frame_indices"] == [2]
    assert evidence["omission_reasons"][2] == "analysis_rejected_paper_figure"


def test_temperature_heatmap_uses_the_same_selected_frame_indices():
    definitions = build_saxs_figure_definitions(_temperature_engine_with_evidence())
    heatmap = _definition(definitions, "saxs.series.temperature.heatmap")
    source = heatmap.data_sources[0]

    assert set(source.values["temperature_C"]) == {30.0, 45.0, 75.0, 90.0}
    assert 60.0 not in source.values["temperature_C"]


def test_temperature_recipe_counts_match_filtered_summary_sources():
    definitions = build_saxs_figure_definitions(_temperature_engine_with_evidence())
    parameters = _definition(definitions, "saxs.series.temperature.parameters")
    heatmap = _definition(definitions, "saxs.series.temperature.heatmap")

    assert parameters.recipe["inputs"]["temperature_count"] == 4
    assert heatmap.recipe["inputs"]["temperature_count"] == 4


def test_temperature_per_frame_role_and_waterfall_preserve_diagnostic_evidence():
    definitions = build_saxs_figure_definitions(_temperature_engine_with_evidence())
    frame = _definition(definitions, "saxs.frame.temperature.scattering.003")
    waterfall = _definition(definitions, "saxs.series.temperature.waterfall")

    assert frame.publication_role == "diagnostic"
    assert frame.recipe["evidence"]["reasons"][2] == "analysis_rejected_paper_figure"
    assert waterfall.publication_role == "diagnostic"


def test_temperature_main_sources_use_emitted_final_values_not_raw_structure():
    definitions = build_saxs_figure_definitions(_temperature_engine_with_evidence())
    parameters = _definition(definitions, "saxs.series.temperature.parameters")
    values = parameters.data_sources[0].values

    assert values["L_nm"][0] == 12.125
    assert values["L_nm"][0] != 90.0
