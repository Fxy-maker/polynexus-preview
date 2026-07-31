from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np

from polynexus.core.figures.v2_capabilities import build_v2_definition_artifact
from polynexus.core.figures.validation import validate_figure_definition
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


def _static_engine_with_method_evidence() -> SimpleNamespace:
    engine = _static_engine()
    engine._batch_results[0].metric_evidence = {
        "porod": {
            "value": 1.2,
            "level": "Trend",
            "reason_codes": ["porod_slope_deviation_observed"],
        },
        "kratky": {
            "value": 0.3,
            "level": "Diagnostic",
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
    }
    engine._batch_results[1].metric_evidence = {
        "porod": {
            "value": None,
            "level": "Unusable",
            "reason_codes": "porod_payload_missing",
        },
        "kratky": {
            "value": np.nan,
            "level": "Unusable",
            "reason_codes": ["kratky_peak_missing"],
        },
        "lamellar": {
            "value": 11.5,
            "level": "Trend",
            "reason_codes": [],
        },
    }
    engine._batch_results.append(
        SimpleNamespace(
            label="sample-3",
            condition_value=2.0,
            q=engine._q_list[0],
            I=np.asarray([98.0, 68.0, 26.0, 7.0]),
            quality_flag="OK",
            final_parameters={
                "file": "sample-3.dat",
                "paper_figure_candidate": True,
                "paper_conclusion_candidate": True,
            },
            fit_regions=(),
            correlation=None,
            idf=None,
            porod=None,
            kratky=None,
            metric_evidence={
                "porod": {"value": 0.9, "level": "Trend", "reason_codes": []},
                "kratky": {"value": 0.2, "level": "Diagnostic", "reason_codes": []},
                "invariant": {"value": 90.0, "level": "Trend", "reason_codes": []},
                "lamellar": {"value": 11.0, "level": "Trend", "reason_codes": []},
            },
        )
    )
    engine._batch_params.append(
        {
            "file": "sample-3.dat",
            "paper_figure_candidate": True,
            "paper_conclusion_candidate": True,
        }
    )
    engine._q_list.append(engine._q_list[0])
    engine._I_list.append(np.asarray([98.0, 68.0, 26.0, 7.0]))
    engine._conditions.append(2)
    engine._file_list.append("sample-3.dat")
    return engine


def test_static_method_evidence_diagnostic_figure_preserves_frame_audit() -> None:
    engine = _static_engine_with_method_evidence()
    definitions = build_static_saxs_figure_definitions(engine)

    figure = next(
        item
        for item in definitions
        if item.figure_id == "saxs.static.method_evidence"
    )
    assert figure.publication_role == "diagnostic"
    assert figure.scope == "series"
    audit_sources = {
        source.source_id: source
        for source in figure.data_sources
        if source.role == "method_evidence_audit"
    }
    assert set(audit_sources) == {
        "static-method-evidence-porod",
        "static-method-evidence-kratky",
        "static-method-evidence-invariant",
        "static-method-evidence-lamellar",
    }

    porod = audit_sources["static-method-evidence-porod"]
    assert porod.values["frame_index"] == (0, 1, 2)
    assert porod.values["value"] == (1.2, None, 0.9)
    assert porod.values["source_path"] == (
        "sample-1.dat",
        "sample-2.dat",
        "sample-3.dat",
    )
    assert porod.values["frame_level"] == ("Trend", "Unusable", "Trend")
    assert porod.values["frame_reason_codes"] == (
        "porod_slope_deviation_observed",
        "porod_payload_missing",
        None,
    )

    invariant = audit_sources["static-method-evidence-invariant"]
    assert invariant.values["value"] == (100.0, None, 90.0)
    assert invariant.values["frame_level"] == ("Trend", None, "Trend")
    assert invariant.values["frame_reason_codes"] == (None, None, None)

    plot_sources = {
        source.source_id: source
        for source in figure.data_sources
        if source.role == "method_evidence_plot"
    }
    assert plot_sources["static-method-evidence-porod-plot"].values == {
        "frame_index": (0.0, 2.0),
        "value": (1.2, 0.9),
    }
    assert plot_sources["static-method-evidence-lamellar-plot"].values == {
        "frame_index": (0.0, 1.0, 2.0),
        "value": (12.0, 11.5, 11.0),
    }
    assert plot_sources["static-method-evidence-kratky-plot"].values == {
        "frame_index": (0.0, 2.0),
        "value": (0.3, 0.2),
    }
    assert figure.recipe["parameters"]["missing_values_preserved"] is True
    assert figure.recipe["parameters"]["interpolation"] is False
    assert figure.recipe["parameters"]["reclassification"] is False
    assert figure.recipe["parameters"]["sequence_axis"] == "frame_index"

    json.dumps(
        {
            source.source_id: dict(source.values)
            for source in figure.data_sources
        },
        allow_nan=False,
    )
    validate_figure_definition(figure)
    assert build_v2_definition_artifact(figure).capability["v2_runtime"] == "ready"

    engine._batch_results[0].metric_evidence["porod"]["value"] = 99.0
    assert porod.values["value"] == (1.2, None, 0.9)


def test_static_provider_omits_empty_method_evidence_figure() -> None:
    definitions = build_static_saxs_figure_definitions(_static_engine())

    assert "saxs.static.method_evidence" not in {
        item.figure_id for item in definitions
    }
