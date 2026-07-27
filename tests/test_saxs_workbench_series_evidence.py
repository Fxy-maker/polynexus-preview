from __future__ import annotations

from copy import deepcopy

import numpy as np

from polynexus.core.saxs import SAXSEngine
from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.saxs_strain import StrainSeriesResult
from polynexus.core.saxs_engine.saxs_temperature import TempSeriesResult
from polynexus.data.sample_db import SampleDB
from polynexus.gui.analysis_run_service import AnalysisRunPersistenceContext, persist_analysis_run
from polynexus.gui.analysis_history_service import flatten_params
from polynexus.gui.results_table_service import build_results_table_model
from polynexus.gui.saxs_results_table_service import build_saxs_results_presentation


def _series_metric_summary(*, level: str = "Trend", frame_count: int = 2) -> dict:
    return {
        "metric_name": "Porod",
        "frame_count": frame_count,
        "evidence_frame_count": frame_count,
        "usable_frame_count": frame_count,
        "diagnostic_frame_count": 0,
        "unusable_frame_count": 0,
        "missing_frame_count": 0,
        "coverage_fraction": 1.0,
        "level": level,
        "applicable": level == "Trend",
        "level_counts": {"Quantitative": 0, "Trend": frame_count, "Diagnostic": 0, "Unusable": 0},
        "reason_codes": [],
        "source_ref": "saxs_temperature.metric_evidence",
    }


def _series_params() -> dict:
    return {
        "batch_frames": 2,
        "_batch_data": [
            {"temperature_C": 20.0, "L_nm": 12.0},
            {"temperature_C": 40.0, "L_nm": 12.2},
        ],
        "metric_evidence": {"porod": _series_metric_summary()},
    }


def test_workbench_renders_temperature_guinier_sequence_diagnostics():
    params = _series_params()
    params["guinier_sequence_evidence"] = {
        "frame_count": 3,
        "valid_frame_count": 2,
        "missing_frame_indices": [1],
        "diagnostic_frame_indices": [],
        "frame_source_indices": [4, 7, 9],
        "level": "Diagnostic",
        "reason_codes": ["guinier_sequence_missing_frames"],
    }

    presentation = build_saxs_results_presentation(
        params, submodule="saxs.temperature", language="en"
    )
    review_text = presentation.risk_text + " " + presentation.next_text

    assert "Rg sequence" in review_text
    assert "Diagnostic" in review_text
    assert "2/3" in review_text
    assert "source indices" in review_text
    assert "guinier_sequence_missing_frames" in review_text
    assert "physical pass" not in review_text.lower()


def test_workbench_renders_existing_rescue_candidates_as_candidate_only_review():
    params = _series_params()
    params["sequence_rescue_candidates"] = [
        {
            "candidate_id": "temperature-frame-1-lc-tangent",
            "kind": "deterministic",
            "parameters": {
                "frame_index": 1,
                "axis_name": "temperature",
                "axis_value": 180.0,
                "proposed_source": "tangent",
                "proposed_value_nm": 3.2,
                "apply_mode": "candidate_only",
                "preserve_missing_frames": True,
            },
            "reason_codes": ["sequence_existing_alternative"],
            "source": "saxs_temperature.select_lc_sequence_path",
            "requires_validation": True,
        }
    ]
    before = deepcopy(params)

    presentation = build_saxs_results_presentation(
        params, submodule="saxs.temperature", language="en"
    )
    review_text = presentation.risk_text + " " + presentation.next_text

    assert "rescue candidate" in review_text.lower()
    assert "1" in review_text
    assert "frame=1" in review_text
    assert "source=tangent" in review_text
    assert "candidate_only" in review_text
    assert "requires validation" in review_text.lower()
    assert "deterministic re-analysis" in review_text.lower()
    assert "applied" not in review_text.lower()
    assert "accepted" not in review_text.lower()
    assert "physically valid" not in review_text.lower()
    assert params == before


def test_workbench_ignores_missing_or_malformed_rescue_candidates_and_localizes():
    params = {
        **_series_params(),
        "sequence_rescue_candidates": [None, "malformed", {}],
    }
    before = deepcopy(params)

    english = build_saxs_results_presentation(
        params, submodule="saxs.temperature", language="en"
    )
    chinese = build_saxs_results_presentation(
        params, submodule="saxs.temperature", language="zh"
    )

    assert "rescue candidate" not in (english.risk_text + english.next_text).lower()
    assert "救援候选" not in (chinese.risk_text + chinese.next_text)
    assert params == before


def test_temperature_get_parameters_transports_existing_series_evidence_without_mutation():
    engine = SAXSEngine(SAXSConfig())
    summary = {"porod": _series_metric_summary()}
    series = TempSeriesResult(
        temperatures=np.array([20.0, 40.0]),
        lc_array=np.array([3.0, 3.1]),
        lc_effective_array=np.array([3.0, 3.1]),
        metric_evidence=summary,
    )
    engine._temperature_result = series
    engine._batch_params = [
        {"temperature_C": 20.0, "L_nm": 12.0},
        {"temperature_C": 40.0, "L_nm": 12.2},
    ]
    batch_before = deepcopy(engine._batch_params)
    before = deepcopy(summary)

    payload = engine.get_parameters()

    assert payload["metric_evidence"] == summary
    assert [row["L_nm"] for row in payload["_batch_data"]] == [12.0, 12.2]
    assert engine._batch_params == batch_before
    assert summary == before
    assert payload["metric_evidence"] is not summary


def test_strain_get_parameters_transports_existing_series_evidence_without_mutation():
    engine = SAXSEngine(SAXSConfig())
    summary = {"porod": _series_metric_summary()}
    series = StrainSeriesResult(
        strains=np.array([0.0, 10.0]),
        L_array=np.array([12.0, 12.2]),
        Q_star_array=np.array([1.0, 1.1]),
        metric_evidence=summary,
    )
    engine._strain_result = series
    engine._batch_params = [
        {"strain_pct": 0.0, "L_nm": 12.0},
        {"strain_pct": 10.0, "L_nm": 12.2},
    ]
    batch_before = deepcopy(engine._batch_params)
    before = deepcopy(summary)

    payload = engine.get_parameters()

    assert payload["metric_evidence"] == summary
    assert [row["L_nm"] for row in payload["_batch_data"]] == [12.0, 12.2]
    assert engine._batch_params == batch_before
    assert summary == before
    assert payload["metric_evidence"] is not summary


def test_transport_preserves_malformed_evidence_for_diagnostics():
    engine = SAXSEngine(SAXSConfig())
    malformed = ["preserve", {"raw": "value"}]
    summary = {"porod": _series_metric_summary(), "malformed": malformed}
    engine._temperature_result = TempSeriesResult(
        temperatures=np.array([20.0, 40.0]),
        lc_array=np.array([3.0, 3.1]),
        lc_effective_array=np.array([3.0, 3.1]),
        metric_evidence=summary,
    )

    payload = engine.get_parameters()

    assert payload["metric_evidence"]["malformed"] == malformed
    assert payload["metric_evidence"]["malformed"] is not malformed


def test_mixed_series_evidence_is_visible_as_downgraded_review_text():
    params = {
        "batch_frames": 3,
        "_batch_data": [
            {"temperature_C": 20.0, "L_nm": 12.0},
            {"temperature_C": 40.0, "L_nm": 12.2},
            {"temperature_C": 60.0, "L_nm": None},
        ],
        "metric_evidence": {
            "porod": {
                **_series_metric_summary(level="Diagnostic", frame_count=3),
                "evidence_frame_count": 2,
                "usable_frame_count": 1,
                "diagnostic_frame_count": 1,
                "missing_frame_count": 1,
                "coverage_fraction": 2 / 3,
                "applicable": False,
                "level_counts": {"Quantitative": 0, "Trend": 1, "Diagnostic": 1, "Unusable": 0},
                "reason_codes": ["series_metric_missing_frames", "series_metric_diagnostic_frames"],
            }
        },
    }

    presentation = build_saxs_results_presentation(
        params, submodule="saxs.temperature", language="en"
    )
    review_text = presentation.risk_text + " " + presentation.next_text

    assert "Porod" in review_text
    assert "2/3" in review_text
    assert "Diagnostic" in review_text
    assert "missing" in review_text.lower()
    metric_column = next(
        index
        for index, column in enumerate(presentation.diagnostics.columns)
        if column.key == "metric_evidence"
    )
    assert "series_metric_missing_frames" in presentation.diagnostics.rows[-1][metric_column].display


def test_complete_series_evidence_is_trend_capped_in_review_text():
    presentation = build_saxs_results_presentation(
        _series_params(), submodule="saxs.temperature", language="en"
    )
    review_text = presentation.risk_text + " " + presentation.next_text

    assert "Porod" in review_text
    assert "2/2" in review_text
    assert "Trend" in review_text
    assert "Quantitative" not in review_text
    assert not presentation.risk_text


def test_condition_axis_defects_are_visible_without_replacing_full_diagnostics():
    params = _series_params()
    params["metric_evidence"]["porod"] = {
        **_series_metric_summary(frame_count=4),
        "condition_axis": {
            "condition_name": "temperature_C",
            "condition_values": [20.0, 20.0, 19.0, None],
            "invalid_condition_indices": [3],
            "duplicate_condition_indices": [0, 1],
            "nonmonotonic_condition_indices": [1, 2],
            "status": "diagnostic",
        },
    }

    presentation = build_saxs_results_presentation(
        params, submodule="saxs.temperature", language="en"
    )
    review_text = presentation.risk_text + " " + presentation.next_text

    assert "Porod" in review_text
    assert "temperature_C" in review_text
    assert "condition axis" in review_text
    assert "invalid=1" in review_text
    assert "duplicate=2" in review_text
    assert "non-monotonic=2" in review_text
    assert "positions=[0, 1, 2, 3]" in review_text
    assert "physical pass" not in review_text.lower()
    metric_column = next(
        index
        for index, column in enumerate(presentation.diagnostics.columns)
        if column.key == "metric_evidence"
    )
    diagnostics = presentation.diagnostics.rows[-1][metric_column].display
    assert "condition_values" in diagnostics
    assert "invalid_condition_indices" in diagnostics
    assert "nonmonotonic_condition_indices" in diagnostics


def test_ordered_condition_axis_does_not_add_workbench_risk():
    params = _series_params()
    params["metric_evidence"]["porod"]["condition_axis"] = {
        "condition_name": "temperature_C",
        "condition_values": [20.0, 40.0],
        "invalid_condition_indices": [],
        "duplicate_condition_indices": [],
        "nonmonotonic_condition_indices": [],
        "status": "ordered",
    }

    presentation = build_saxs_results_presentation(
        params, submodule="saxs.temperature", language="en"
    )

    assert presentation.risk_text == ""
    assert "condition axis" not in presentation.next_text.lower()


def test_condition_axis_review_text_is_localized():
    params = _series_params()
    params["metric_evidence"]["porod"]["condition_axis"] = {
        "condition_name": "temperature_C",
        "condition_values": [],
        "invalid_condition_indices": [],
        "duplicate_condition_indices": [],
        "nonmonotonic_condition_indices": [],
        "status": "empty",
    }

    presentation = build_saxs_results_presentation(
        params, submodule="saxs.temperature", language="zh"
    )
    review_text = presentation.risk_text + " " + presentation.next_text

    assert "条件轴" in review_text
    assert "诊断" in review_text
    assert "temperature_C" in review_text


def test_static_batch_evidence_uses_batch_quality_wording_and_keeps_diagnostics():
    params = {
        "batch_frames": 3,
        "metric_evidence_scope": "static_batch",
        "_batch_data": [
            {"file": "frame_001.dat"},
            {"file": "frame_002.dat"},
            {"file": "frame_003.dat"},
        ],
        "metric_evidence": {
            "porod": {
                "metric_name": "Porod",
                "frame_count": 3,
                "evidence_frame_count": 2,
                "usable_frame_count": 1,
                "diagnostic_frame_count": 1,
                "unusable_frame_count": 0,
                "missing_frame_count": 1,
                "coverage_fraction": 2 / 3,
                "level": "Diagnostic",
                "applicable": False,
                "reason_codes": [
                    "series_metric_missing_frames",
                    "series_metric_diagnostic_frames",
                ],
            }
        },
    }

    presentation = build_saxs_results_presentation(
        params, submodule="saxs.static", language="en"
    )
    review_text = presentation.risk_text + " " + presentation.next_text

    assert "Batch quality" in review_text
    assert "2/3" in review_text
    assert "Diagnostic" in review_text
    assert "series_metric_missing_frames" in review_text
    assert "temperature trend" not in review_text.lower()
    assert "strain trend" not in review_text.lower()

    metric_column = next(
        index
        for index, column in enumerate(presentation.diagnostics.columns)
        if column.key == "metric_evidence"
    )
    assert "series_metric_missing_frames" in presentation.diagnostics.rows[-1][metric_column].display


def test_aligned_batch_evidence_does_not_claim_static_or_series_trend():
    params = {
        "batch_frames": 2,
        "metric_evidence_scope": "aligned_batch",
        "_batch_data": [{"file": "frame-0"}, {"file": "frame-1"}],
        "metric_evidence": {
            "porod": {
                **_series_metric_summary(level="Diagnostic"),
                "evidence_frame_count": 1,
                "usable_frame_count": 1,
                "missing_frame_count": 1,
                "coverage_fraction": 0.5,
                "applicable": False,
                "reason_codes": ["series_metric_missing_frames"],
            }
        },
    }

    presentation = build_saxs_results_presentation(
        params, submodule="saxs.temperature", language="en"
    )
    review_text = presentation.risk_text + " " + presentation.next_text

    assert "Aligned batch quality" in review_text
    assert "static batch" not in review_text.lower()
    assert "series trend" not in review_text.lower()


def test_guinier_series_evidence_uses_rg_label_in_review_text():
    params = _series_params()
    params["metric_evidence"]["guinier"] = {
        **_series_metric_summary(),
        "metric_name": "guinier",
    }

    presentation = build_saxs_results_presentation(
        params, submodule="saxs.temperature", language="en"
    )

    assert "Rg" in (presentation.risk_text + presentation.next_text)


def test_series_evidence_review_text_is_localized():
    presentation = build_saxs_results_presentation(
        {
            **_series_params(),
            "metric_evidence": {
                "porod": {
                    **_series_metric_summary(level="Diagnostic"),
                    "evidence_frame_count": 1,
                    "usable_frame_count": 0,
                    "diagnostic_frame_count": 1,
                    "missing_frame_count": 1,
                    "coverage_fraction": 0.5,
                    "applicable": False,
                    "level_counts": {"Quantitative": 0, "Trend": 0, "Diagnostic": 1, "Unusable": 0},
                    "reason_codes": ["series_metric_missing_frames"],
                }
            },
        },
        submodule="saxs.strain",
        language="zh",
    )

    review_text = presentation.risk_text + " " + presentation.next_text
    assert review_text
    assert "Porod" in review_text
    assert "诊断" in review_text


def test_results_table_model_carries_series_review_text_and_keeps_profile_candidates():
    model = build_results_table_model(
        _series_params(),
        ordered_columns_fn=lambda columns: list(columns),
        flatten_params_fn=flatten_params,
        technique="saxs",
        submodule="temperature",
        language="en",
    )

    assert model.profile.key == "saxs.temperature"
    assert model.next_text
    assert model.risk_text == ""
    assert next(link for link in model.profile.figure_links if link.role == "main").candidates == (
        "saxs.temperature.evolution",
        "saxs.temperature.waterfall",
        "saxs.series.temperature.parameters",
    )


def test_history_persistence_retains_series_evidence_in_parameters(tmp_path):
    db = SampleDB(tmp_path / "samples.db")
    data_file = tmp_path / "temperature.csv"
    data_file.write_text("temperature_C,L_nm\n20,12\n", encoding="utf-8")
    params = _series_params()
    before = deepcopy(params)
    context = AnalysisRunPersistenceContext(
        technique="saxs",
        submodule="saxs.temperature",
        data_file=str(data_file),
        output_dir=str(tmp_path / "output"),
        project_label="PA6",
    )

    run_id = persist_analysis_run(
        db,
        {
            "technique": "saxs",
            "parameters": params,
        },
        context,
    )

    run = db.get_analysis_run(run_id)
    assert run["parameters"]["metric_evidence"] == params["metric_evidence"]
    assert run["results_summary"]["result"]["parameters"]["metric_evidence"] == params["metric_evidence"]
    assert params == before
    db.close()


def test_history_persistence_retains_static_batch_evidence_scope_and_rows(tmp_path):
    db = SampleDB(tmp_path / "samples.db")
    data_file = tmp_path / "static_batch.csv"
    data_file.write_text("file,L_nm\nframe_001.dat,12\n", encoding="utf-8")
    params = {
        "batch_frames": 2,
        "metric_evidence_scope": "static_batch",
        "metric_evidence": {
            "porod": {
                "metric_name": "Porod",
                "frame_count": 2,
                "evidence_frame_count": 1,
                "usable_frame_count": 1,
                "diagnostic_frame_count": 0,
                "unusable_frame_count": 0,
                "missing_frame_count": 1,
                "coverage_fraction": 0.5,
                "level": "Diagnostic",
                "reason_codes": ["series_metric_missing_frames"],
            }
        },
        "_batch_data": [
            {
                "file": "frame_001.dat",
                "metric_evidence": {"porod": {"level": "Trend"}},
            },
            {"file": "frame_002.dat"},
        ],
    }
    before = deepcopy(params)
    context = AnalysisRunPersistenceContext(
        technique="saxs",
        submodule="saxs.static",
        data_file=str(data_file),
        output_dir=str(tmp_path / "output"),
        project_label="PA6",
    )

    run_id = persist_analysis_run(
        db,
        {"technique": "saxs", "parameters": params},
        context,
    )

    run = db.get_analysis_run(run_id)
    assert run["parameters"]["metric_evidence_scope"] == "static_batch"
    assert run["parameters"]["_batch_data"][0]["metric_evidence"]["porod"]["level"] == "Trend"
    assert run["results_summary"]["result"]["parameters"]["metric_evidence"] == params["metric_evidence"]
    assert params == before
    db.close()
