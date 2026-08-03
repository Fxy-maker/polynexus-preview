from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np

from polynexus.core.figures.v2_capabilities import build_v2_definition_artifact
from polynexus.core.figures.validation import validate_figure_definition
from polynexus.core.saxs_engine.figure_strain import build_strain_figure_definitions


def _strain_engine_with_method_evidence() -> SimpleNamespace:
    q = np.asarray([0.1, 0.2, 0.4, 0.8], dtype=float)
    analyses = []
    rows = []
    evidence = (
        {
            "porod": {
                "value": 1.2,
                "level": "Trend",
                "reason_codes": ["porod_slope_deviation_observed"],
            },
            "kratky": {"value": 0.3, "level": "Diagnostic", "reason_codes": []},
            "invariant": {"value": 100.0, "level": "Trend", "reason_codes": []},
            "lamellar": {
                "value": 12.0,
                "level": "Diagnostic",
                "reason_codes": ["lamellar_phi_c_invalid"],
            },
        },
        {
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
            "lamellar": {"value": 11.5, "level": "Trend", "reason_codes": []},
        },
        {
            "porod": {"value": 0.9, "level": "Trend", "reason_codes": []},
            "kratky": {"value": 0.2, "level": "Diagnostic", "reason_codes": []},
            "invariant": {"value": 90.0, "level": "Trend", "reason_codes": []},
            "lamellar": {"value": 11.0, "level": "Trend", "reason_codes": []},
        },
    )
    for index, metric_evidence in enumerate(evidence):
        row = {
            "file": f"strain-{index}.dat",
            "L_nm": 15.0 - index,
            "lc_nm": 6.0,
            "la_nm": 9.0,
            "Xc": 0.4,
            "Q_rel": 1.0,
            "Q_star_valid": True,
            "lc_confidence": 0.8,
            "paper_figure_candidate": True,
            "paper_conclusion_candidate": True,
        }
        rows.append(row)
        analyses.append(
            SimpleNamespace(
                label=f"strain-{index}",
                condition_value=float(index * 25),
                q=q,
                I=np.asarray([100.0, 70.0, 28.0, 8.0]) - index,
                I_smooth=np.asarray([100.0, 70.0, 28.0, 8.0]) - index,
                quality_flag="OK",
                final_parameters=row,
                metric_evidence=metric_evidence,
                correlation=None,
                idf=None,
                anisotropy=None,
                fit_regions=(),
            )
        )
    return SimpleNamespace(
        _batch_results=analyses,
        _batch_params=rows,
        _q_list=[q, q, q],
        _I_list=[analysis.I for analysis in analyses],
        _conditions=[0.0, 25.0, 50.0],
        _file_list=[row["file"] for row in rows],
        _analysis=None,
        _temperature_result=None,
        _strain_result=SimpleNamespace(
            strains=np.asarray([0.0, 25.0, 50.0]),
            strain_points=[],
            metric_evidence={"porod": {"level": "Trend"}},
        ),
        _condition_type="strain",
        cfg=SimpleNamespace(experiment_type="strain"),
    )


def test_strain_method_evidence_diagnostic_figure_preserves_frame_audit() -> None:
    engine = _strain_engine_with_method_evidence()
    definitions = build_strain_figure_definitions(engine)

    figure = next(
        item
        for item in definitions
        if item.figure_id == "saxs.strain.method_evidence"
    )
    assert figure.publication_role == "diagnostic"
    assert figure.scope == "series"
    audit_sources = {
        source.source_id: source
        for source in figure.data_sources
        if source.role == "method_evidence_audit"
    }
    assert set(audit_sources) == {
        "strain-method-evidence-porod",
        "strain-method-evidence-kratky",
        "strain-method-evidence-invariant",
        "strain-method-evidence-lamellar",
    }

    porod = audit_sources["strain-method-evidence-porod"]
    assert porod.values["strain_pct"] == (0.0, 25.0, 50.0)
    assert porod.values["value"] == (1.2, None, 0.9)
    assert porod.values["frame_index"] == (0, 1, 2)
    assert porod.values["source_path"] == (
        "strain-0.dat",
        "strain-1.dat",
        "strain-2.dat",
    )
    assert porod.values["frame_level"] == ("Trend", "Unusable", "Trend")
    assert porod.values["frame_reason_codes"] == (
        "porod_slope_deviation_observed",
        "porod_payload_missing",
        None,
    )

    invariant = audit_sources["strain-method-evidence-invariant"]
    assert invariant.values["value"] == (100.0, None, 90.0)
    assert invariant.values["frame_level"] == ("Trend", None, "Trend")

    plot_sources = {
        source.source_id: source
        for source in figure.data_sources
        if source.role == "method_evidence_plot"
    }
    assert plot_sources["strain-method-evidence-porod-plot"].values == {
        "strain_pct": (0.0, 50.0),
        "value": (1.2, 0.9),
    }
    assert plot_sources["strain-method-evidence-lamellar-plot"].values == {
        "strain_pct": (0.0, 25.0, 50.0),
        "value": (12.0, 11.5, 11.0),
    }
    assert figure.recipe["parameters"]["condition_axis"] == "strain_pct"
    assert figure.recipe["parameters"]["missing_values_preserved"] is True
    assert figure.recipe["parameters"]["interpolation"] is False
    assert figure.recipe["parameters"]["reclassification"] is False
    assert figure.recipe["parameters"]["renderer_minimum_pairs"] == 2

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


def test_strain_provider_omits_empty_method_evidence_figure() -> None:
    engine = _strain_engine_with_method_evidence()
    for analysis in engine._batch_results:
        analysis.metric_evidence = {}

    definitions = build_strain_figure_definitions(engine)

    assert "saxs.strain.method_evidence" not in {
        item.figure_id for item in definitions
    }
