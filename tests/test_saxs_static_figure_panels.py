from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from polynexus.core.saxs_engine.figure_static import build_static_saxs_figure_definitions


def _static_engine() -> SimpleNamespace:
    q = np.asarray([0.10, 0.20, 0.40, 0.80], dtype=float)
    rows = [
        {
            "file": f"sample-{index + 1}.dat",
            "L_nm": 15.0 + index,
            "lc_nm": 6.0 + index,
            "la_nm": 9.0,
            "Xc": 0.4 + index * 0.01,
            "Q_rel": 1.0,
            "Q_star_valid": True,
            "lc_confidence": 0.8,
            "paper_figure_candidate": True,
            "paper_conclusion_candidate": True,
        }
        for index in range(2)
    ]
    analyses = []
    for index, row in enumerate(rows):
        analysis = SimpleNamespace(
            label=f"sample-{index + 1}",
            condition_value=float(index),
            q=q,
            I=np.asarray([100.0, 70.0, 28.0, 8.0]) - index,
            quality_flag="OK",
            final_parameters=row,
            fit_regions=({"kind": "bragg_peak", "q_peak_fit": 0.4},),
            correlation=(
                {"r": [0.0, 4.0, 8.0, 12.0], "gamma": [1.0, -0.2, 0.5, 0.1]}
                if index == 0
                else None
            ),
            idf=None,
            porod=None,
            kratky={"q": q, "kratky": q * q},
        )
        analyses.append(analysis)
    return SimpleNamespace(
        _batch_results=analyses,
        _batch_params=rows,
        _q_list=[item.q for item in analyses],
        _I_list=[item.I for item in analyses],
        _conditions=[0, 1],
        _file_list=[row["file"] for row in rows],
        _analysis=None,
        _temperature_result=None,
        _strain_result=None,
        _condition_type="static",
        cfg=SimpleNamespace(experiment_type="static"),
    )


def test_static_pack_orders_main_support_and_diagnostics() -> None:
    definitions = build_static_saxs_figure_definitions(_static_engine())

    assert [item.figure_id for item in definitions] == [
        "saxs.static.comparison",
        "saxs.static.correlation.support",
        "saxs.static.frame.000.correlation",
        "saxs.static.frame.000.kratky",
        "saxs.static.frame.001.kratky",
    ]
    assert [item.display_order for item in definitions] == [10, 20, 100, 104, 114]
    assert definitions[0].publication_role == "main"
    assert definitions[1].publication_role == "si"
    assert all(item.publication_role == "diagnostic" for item in definitions[2:])


def test_dirty_projection_keeps_valid_static_pairs() -> None:
    engine = _static_engine()
    engine._q_list[0] = np.asarray(
        ["0.10", "bad-q", "0.40", "0.80"],
        dtype=object,
    )
    engine._I_list[0] = np.asarray(
        ["100.0", "70.0", "bad-intensity", "8.0"],
        dtype=object,
    )
    q_before = engine._q_list[0].copy()
    intensity_before = engine._I_list[0].copy()

    definitions = build_static_saxs_figure_definitions(engine)
    comparison = next(
        item for item in definitions if item.figure_id == "saxs.static.comparison"
    )
    profile = next(
        source
        for source in comparison.data_sources
        if source.source_id == "static-frame-000-profile"
    )

    assert profile.values["q_nm_inv"] == (0.1, 0.8)
    assert profile.values["intensity"] == (100.0, 8.0)
    assert np.array_equal(engine._q_list[0], q_before)
    assert np.array_equal(engine._I_list[0], intensity_before)


def test_dirty_projection_all_invalid_static_profile_remains_fail_closed() -> None:
    engine = _static_engine()
    engine._q_list[0] = np.asarray(["bad-q", "also-bad"], dtype=object)
    engine._I_list[0] = np.asarray(
        ["bad-intensity", "also-bad"],
        dtype=object,
    )

    definitions = build_static_saxs_figure_definitions(engine)

    assert "saxs.static.comparison" not in {
        item.figure_id for item in definitions
    }
