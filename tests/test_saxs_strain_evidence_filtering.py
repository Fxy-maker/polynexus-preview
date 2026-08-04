from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from polynexus.core.saxs_engine.figure_provider import build_saxs_figure_definitions


def _strain_engine_with_evidence():
    conditions = [0.0, 25.0, 50.0]
    q_list = [np.asarray([0.1, 0.2, 0.3])] * len(conditions)
    intensity_list = [np.asarray([10.0, 5.0, 2.0])] * len(conditions)
    params = [
        {"paper_figure_candidate": True, "quality_flag": "OK", "Q_star_valid": True, "file": "frame_0.dat"},
        {
            "paper_figure_candidate": False,
            "quality_flag": "WARN:low_snr",
            "file": "frame_1.dat",
        },
        {"paper_figure_candidate": True, "quality_flag": "OK", "Q_star_valid": True, "file": "frame_2.dat"},
    ]
    analyses = [
        SimpleNamespace(
            label=f"frame-{index}",
            condition_value=condition,
            q=q_list[index],
            I=intensity_list[index],
            final_parameters=dict(params[index]),
        )
        for index, condition in enumerate(conditions)
    ]
    return SimpleNamespace(
        _temperature_result=None,
        _strain_result=SimpleNamespace(strains=np.asarray(conditions)),
        _condition_type="strain",
        cfg=SimpleNamespace(experiment_type="strain"),
        _q_list=q_list,
        _I_list=intensity_list,
        _conditions=conditions,
        _batch_results=analyses,
        _batch_params=params,
        _file_list=[item["file"] for item in params],
    )


def test_strain_mixed_evidence_downgrades_waterfall_and_preserves_order():
    definitions = build_saxs_figure_definitions(_strain_engine_with_evidence())

    frames = [item for item in definitions if item.scope == "frame"]
    waterfall = next(
        item for item in definitions if item.figure_id == "saxs.series.strain.waterfall"
    )

    assert [item.publication_role for item in frames] == ["main", "diagnostic", "main"]
    assert [obj["name"] for obj in waterfall.objects] == [
        "0% strain",
        "25% strain",
        "50% strain",
    ]
    assert waterfall.publication_role == "diagnostic"
    assert waterfall.recipe["evidence"]["included_frame_indices"] == [0, 1, 2]
    assert waterfall.recipe["evidence"]["omitted_frame_indices"] == []
    assert waterfall.recipe["evidence"]["reasons"][1] == "analysis_rejected_paper_figure"
