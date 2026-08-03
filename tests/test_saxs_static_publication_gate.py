from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from polynexus.core.saxs_engine.figure_static import (
    build_static_saxs_figure_definitions,
)


def _engine(*, parameters: dict[str, object]) -> SimpleNamespace:
    q = np.asarray([0.10, 0.20, 0.40, 0.80], dtype=float)
    analysis = SimpleNamespace(
        label="sample",
        condition_value=0.0,
        q=q,
        I=np.asarray([100.0, 70.0, 28.0, 8.0]),
        I_smooth=np.asarray([100.0, 70.0, 28.0, 8.0]),
        final_parameters=dict(parameters),
        quality_flag=str(parameters.get("quality_flag", "")),
        kratky={"q": q, "kratky": q * q},
        correlation=None,
        idf=None,
        porod=None,
        guinier=None,
    )
    return SimpleNamespace(
        _batch_results=[analysis],
        _batch_params=[dict(parameters)],
        _q_list=[q],
        _I_list=[analysis.I],
        _conditions=[0.0],
        _file_list=["sample.dat"],
        _analysis=None,
        _temperature_result=None,
        _strain_result=None,
        _condition_type="static",
        cfg=SimpleNamespace(experiment_type="static"),
    )


def test_static_requires_explicit_publication_candidate_for_main() -> None:
    definitions = build_static_saxs_figure_definitions(
        _engine(parameters={"quality_flag": "OK"})
    )

    assert definitions
    assert all(item.publication_role != "main" for item in definitions)
    assert all(
        item.recipe["parameters"]["no_publication_ready_figure"] is True
        for item in definitions
    )
    assert all(
        item.recipe["parameters"]["no_publication_ready_reason"]
        == "static_frame_publication_authorization_missing"
        for item in definitions
    )


def test_static_explicit_candidate_can_produce_main() -> None:
    definitions = build_static_saxs_figure_definitions(
        _engine(
            parameters={
                "quality_flag": "OK",
                "paper_figure_candidate": True,
                "lc_reliability_status": "usable",
            }
        )
    )

    assert definitions[0].figure_id == "saxs.static.sample"
    assert definitions[0].publication_role == "main"
    assert "no_publication_ready_figure" not in definitions[0].recipe["parameters"]


def test_static_reliability_status_alone_cannot_authorize_main() -> None:
    definitions = build_static_saxs_figure_definitions(
        _engine(
            parameters={
                "quality_flag": "OK",
                "lc_reliability_status": "usable",
            }
        )
    )

    assert definitions
    assert all(item.publication_role != "main" for item in definitions)


def test_static_explicit_rejection_preserves_diagnostic_evidence() -> None:
    definitions = build_static_saxs_figure_definitions(
        _engine(
            parameters={
                "quality_flag": "OK",
                "paper_figure_candidate": False,
            }
        )
    )

    assert definitions
    assert all(item.publication_role != "main" for item in definitions)
    assert any(item.publication_role == "diagnostic" for item in definitions)
