from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from polynexus.core.figures.pipeline import FigurePipeline
from polynexus.core.figures.validation import validate_figure_definition
from polynexus.core.saxs_engine.figure_provider import build_saxs_figure_definitions
from polynexus.core.saxs_engine.figure_static import build_static_saxs_figure_definitions
from polynexus.core.saxs_engine.figure_strain import build_strain_figure_definitions


def _analysis(index: int, params: dict[str, object], *, diagnostics: bool = False):
    q = np.asarray([0.10, 0.20, 0.40, 0.80], dtype=float)
    result = SimpleNamespace(
        label=f"sample-{index + 1}",
        condition_value=float(index),
        q=q,
        I=np.asarray([100.0, 70.0, 28.0, 8.0]) - index,
        quality_flag="OK",
        final_parameters=params,
        fit_regions=({"kind": "bragg_peak", "q_peak_fit": 0.4 + index * 0.02},),
        correlation=None,
        idf=None,
        porod=None,
        kratky={"q": q, "kratky": q * q},
    )
    if diagnostics:
        result.correlation = {
            "r": np.asarray([0.0, 4.0, 8.0, 12.0]),
            "gamma": np.asarray([1.0, -0.2, 0.5, 0.1]),
        }
    return result


def _static_engine(count: int = 2):
    rows = [
        {
            "file": f"sample-{i + 1}.dat",
            "L_nm": 15.0 + i,
            "lc_nm": 6.0 + i,
            "la_nm": 9.0,
            "Xc": 0.4 + i * 0.01,
            "Q_rel": 1.0,
            "Q_star_valid": True,
            "lc_confidence": 0.8,
        }
        for i in range(count)
    ]
    analyses = [_analysis(i, rows[i], diagnostics=i == 0) for i in range(count)]
    return SimpleNamespace(
        _batch_results=analyses,
        _batch_params=rows,
        _q_list=[item.q for item in analyses],
        _I_list=[item.I for item in analyses],
        _conditions=list(range(count)),
        _file_list=[row["file"] for row in rows],
        _analysis=None,
        _temperature_result=None,
        _strain_result=None,
        _condition_type="static",
        cfg=SimpleNamespace(experiment_type="static"),
    )


def test_static_pack_separates_main_si_and_diagnostic_correlation() -> None:
    definitions = build_static_saxs_figure_definitions(_static_engine())
    assert definitions
    assert definitions[0].figure_id == "saxs.static.comparison"
    assert definitions[0].publication_role == "main"
    assert any(item.publication_role == "si" for item in definitions)
    correlations = [item for item in definitions if "correlation" in item.figure_id]
    assert correlations
    assert all(item.publication_role != "main" for item in correlations)
    assert [item.recipe["parameters"]["display_order"] for item in definitions] == sorted(
        item.recipe["parameters"]["display_order"] for item in definitions
    )
    for item in definitions:
        validate_figure_definition(item)


def test_dispatch_uses_static_pack_and_publishes_audited_editable_documents(tmp_path) -> None:
    definitions = build_saxs_figure_definitions(_static_engine())
    assert definitions == build_static_saxs_figure_definitions(_static_engine())
    manifest = FigurePipeline().run(
        output_root=tmp_path,
        run_id="saxs-static-upgrade",
        technique="saxs",
        definitions=definitions,
    )
    assert all(item.status == "ready" for item in manifest.figures)
    assert all(item.capability_report["object_editing"] for item in manifest.figures)
    assert manifest.figures[0].publication_role == "main"


def test_strain_pack_uses_1d_fallback_and_keeps_correlation_out_of_main() -> None:
    engine = _static_engine(3)
    engine._condition_type = "strain"
    engine.cfg.experiment_type = "strain"
    engine._strain_result = SimpleNamespace(strains=np.asarray([0.0, 25.0, 50.0]))
    definitions = build_strain_figure_definitions(engine)
    assert any(item.publication_role == "main" for item in definitions)
    assert any(item.publication_role == "si" for item in definitions)
    assert all(
        item.publication_role != "main"
        for item in definitions
        if "correlation" in item.figure_id
    )
    assert all("detector" not in str(item.recipe).lower() for item in definitions)
