from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from polynexus.core.saxs_engine.figure_common import SAXSFrameView
from polynexus.core.saxs_engine.figure_eligibility import (
    classify_frame_eligibility,
)
from polynexus.core.saxs_engine.figure_provider import build_saxs_figure_definitions
from polynexus.core.saxs_engine.figure_selection import resolve_saxs_figure_mode


def _engine(**overrides):
    state = {
        "_temperature_result": None,
        "_strain_result": None,
        "_condition_type": "static",
        "cfg": SimpleNamespace(experiment_type="static"),
    }
    state.update(overrides)
    return SimpleNamespace(**state)


def _frame(*, parameters=None, quality_flag=""):
    return SAXSFrameView(
        index=0,
        label="frame",
        condition=20.0,
        q=np.asarray([0.1, 0.2, 0.3]),
        intensity=np.asarray([2.0, 4.0, 3.0]),
        analysis=SimpleNamespace(quality_flag=quality_flag),
        parameters=parameters or {},
    )


def test_completed_temperature_result_has_priority_over_declared_static_mode():
    decision = resolve_saxs_figure_mode(
        _engine(
            _temperature_result=SimpleNamespace(),
            _condition_type="static",
            cfg=SimpleNamespace(experiment_type="static"),
        )
    )

    assert decision.mode == "temperature"
    assert decision.reason == "completed_temperature_result"


def test_mixed_completed_series_is_explicitly_unsupported():
    decision = resolve_saxs_figure_mode(
        _engine(
            _temperature_result=SimpleNamespace(),
            _strain_result=SimpleNamespace(),
        )
    )

    assert decision.mode == "unsupported"
    assert decision.reason == "mixed_completed_series"


def test_declared_temperature_without_completed_result_is_not_static():
    decision = resolve_saxs_figure_mode(
        _engine(
            _condition_type="temperature",
            cfg=SimpleNamespace(experiment_type="temperature"),
        )
    )

    assert decision.mode == "incomplete"
    assert decision.reason == "temperature_result_missing"


def test_configuration_temperature_takes_precedence_over_stale_static_condition_type():
    decision = resolve_saxs_figure_mode(
        _engine(
            _condition_type="static",
            cfg=SimpleNamespace(experiment_type="temperature"),
        )
    )

    assert decision.mode == "incomplete"
    assert decision.reason == "temperature_result_missing"


def test_missing_frame_evidence_is_supplementary_not_main():
    decision = classify_frame_eligibility(_frame(quality_flag="WARN:low_snr"))

    assert decision.highest_role == "si"
    assert decision.reasons == ("limited_or_unclassified_quality",)


def test_analysis_error_cannot_be_promoted_to_main_by_candidate_flag():
    decision = classify_frame_eligibility(
        _frame(
            parameters={"paper_figure_candidate": True},
            quality_flag="ERROR:qstar",
        )
    )

    assert decision.highest_role == "diagnostic"
    assert decision.reasons == ("analysis_error",)


def test_provider_persists_emitted_evidence_role_on_frame_definition():
    analysis = SimpleNamespace(
        label="sample",
        condition_value=np.nan,
        q=np.asarray([0.1, 0.2, 0.3]),
        I=np.asarray([2.0, 4.0, 3.0]),
        I_smooth=np.asarray([2.0, 4.0, 3.0]),
        final_parameters={"quality_flag": "OK", "paper_figure_candidate": True, "Q_star_valid": True},
    )
    engine = _engine(
        _analysis=analysis,
        _batch_results=[analysis],
        _q_list=[analysis.q],
        _I_list=[analysis.I],
        _conditions=[np.nan],
        _file_list=["sample.dat"],
    )

    definitions = build_saxs_figure_definitions(engine)

    assert definitions[0].publication_role == "main"


def test_mixed_frame_roles_downgrade_series_and_preserve_evidence_reasons():
    analyses = [
        SimpleNamespace(
            label="main-frame",
            condition_value=0.0,
            q=np.asarray([0.1, 0.2, 0.3]),
            I=np.asarray([2.0, 4.0, 3.0]),
            final_parameters={"quality_flag": "OK", "paper_figure_candidate": True, "Q_star_valid": True},
        ),
        SimpleNamespace(
            label="diagnostic-frame",
            condition_value=10.0,
            q=np.asarray([0.1, 0.2, 0.3]),
            I=np.asarray([2.0, 4.0, 3.0]),
            final_parameters={"quality_flag": "ERROR:qstar"},
        ),
    ]
    engine = _engine(
        _analysis=analyses[0],
        _batch_results=analyses,
        _q_list=[item.q for item in analyses],
        _I_list=[item.I for item in analyses],
        _conditions=[0.0, 10.0],
        _file_list=["main.dat", "diagnostic.dat"],
    )

    definitions = build_saxs_figure_definitions(engine)
    waterfall = next(
        item for item in definitions if item.figure_id == "saxs.series.static.waterfall"
    )

    assert [item.publication_role for item in definitions[:2]] == ["main", "diagnostic"]
    assert waterfall.publication_role == "diagnostic"
    assert waterfall.recipe["evidence"]["reasons"][1] == "analysis_error"
