from __future__ import annotations

import copy
from types import SimpleNamespace

import numpy as np

from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.core import LongPeriodResult, StructureParams
from polynexus.core.saxs_engine.saxs_quality_contracts import (
    build_data_quality_report,
    build_guinier_evidence,
)
from polynexus.core.saxs_engine.saxs_temperature import (
    TempSeriesResult,
    TemperaturePointResult,
    analyze_temperature_series,
)


_SEQUENCE_INTEGRITY_COLUMNS = (
    "Rg_sequence_frame_source_indices",
    "Rg_sequence_missing_frame_indices",
    "Rg_sequence_diagnostic_frame_indices",
    "Rg_sequence_invalid_temperature_indices",
    "Rg_sequence_duplicate_temperature_indices",
    "Rg_sequence_nonmonotonic_temperature_indices",
    "Rg_sequence_continuity_break_indices",
    "Rg_sequence_duplicate_source_index_indices",
    "Rg_sequence_invalid_source_index_indices",
    "Rg_sequence_source_index_order_reordered",
)


def _fake_frame_result(q, intensity):
    quality = build_data_quality_report(q, intensity, source_id="frame")
    evidence = build_guinier_evidence(
        q[:12], np.log(intensity[:12]), rg_nm=4.0, i0=float(intensity[0]),
        quality_report=quality, applicability="supported",
    )
    return SimpleNamespace(
        long_period=LongPeriodResult(L_best=10.0, L_confidence=0.8, method_used="bragg"),
        structure=StructureParams(L=10.0, lc=3.0, la=7.0, phi_c=0.3, confidence_lc=0.8),
        guinier_evidence=evidence.to_dict(),
        data_quality_report=quality.to_dict(),
    )


def test_temperature_dataframe_projects_existing_guinier_sequence_integrity_without_mutation():
    sequence = {
        "level": "Diagnostic",
        "reason_codes": ["guinier_sequence_source_index_duplicate"],
        "frame_source_indices": [2, 0, 1],
        "missing_frame_indices": [1],
        "diagnostic_frame_indices": [1, 2],
        "invalid_temperature_indices": [2],
        "duplicate_temperature_indices": [0, 1],
        "nonmonotonic_temperature_indices": [1],
        "continuity_break_indices": [2],
        "duplicate_source_index_indices": [0, 2],
        "invalid_source_index_indices": [1],
        "source_index_order_reordered": True,
    }
    before = copy.deepcopy(sequence)
    result = TempSeriesResult(
        temp_points=[TemperaturePointResult(source_index=2, temperature_C=170.0)],
        guinier_sequence_evidence=sequence,
    )

    table = result.to_dataframe()
    row = table.iloc[0]

    assert row["Rg_sequence_frame_source_indices"] == "2|0|1"
    assert row["Rg_sequence_missing_frame_indices"] == "1"
    assert row["Rg_sequence_diagnostic_frame_indices"] == "1|2"
    assert row["Rg_sequence_invalid_temperature_indices"] == "2"
    assert row["Rg_sequence_duplicate_temperature_indices"] == "0|1"
    assert row["Rg_sequence_nonmonotonic_temperature_indices"] == "1"
    assert row["Rg_sequence_continuity_break_indices"] == "2"
    assert row["Rg_sequence_duplicate_source_index_indices"] == "0|2"
    assert row["Rg_sequence_invalid_source_index_indices"] == "1"
    assert bool(row["Rg_sequence_source_index_order_reordered"]) is True
    assert sequence == before


def test_temperature_dataframe_keeps_rows_and_empty_sequence_integrity_fields_missing():
    table = TempSeriesResult(
        temp_points=[TemperaturePointResult(source_index=4, temperature_C=190.0)]
    ).to_dataframe()

    assert len(table) == 1
    for column in _SEQUENCE_INTEGRITY_COLUMNS:
        assert column in table.columns
        assert table[column].isna().all()


def test_temperature_frames_retain_individual_guinier_evidence(monkeypatch):
    import polynexus.core.saxs_engine.saxs_temperature as module

    q = np.linspace(0.02, 0.6, 24)
    intensity = 120.0 * np.exp(-(q**2) * 4.0**2 / 3.0)
    q_list = [q, q]
    i_list = [intensity, intensity * 0.9]

    monkeypatch.setattr(module, "analyze_single", lambda q_arr, i_arr, cfg: _fake_frame_result(q_arr, i_arr))
    monkeypatch.setattr(module, "scattering_invariant", lambda q_arr, i_arr, cfg=None: 1.0)
    monkeypatch.setattr(module, "bragg_long_period", lambda q_arr, i_arr: (10.0, 0.628, {}))

    result = analyze_temperature_series([170.0, 180.0], q_list, i_list, cfg=SAXSConfig())

    assert len(result.temp_points) == 2
    assert [point.guinier_level for point in result.temp_points] == ["Quantitative", "Quantitative"]
    assert all(point.guinier_evidence["metric"]["metric_name"] == "Rg" for point in result.temp_points)
    assert all(point.Rg_nm == 4.0 for point in result.temp_points)


def test_temperature_core_failure_does_not_fabricate_guinier_evidence(monkeypatch):
    import polynexus.core.saxs_engine.saxs_temperature as module

    q = np.linspace(0.02, 0.6, 24)
    intensity = 120.0 * np.exp(-(q**2) * 4.0**2 / 3.0)
    calls = {"count": 0}

    def fake_analyze(q_arr, i_arr, cfg):
        calls["count"] += 1
        if calls["count"] == 2:
            raise RuntimeError("injected frame failure")
        return _fake_frame_result(q_arr, i_arr)

    monkeypatch.setattr(module, "analyze_single", fake_analyze)
    monkeypatch.setattr(module, "scattering_invariant", lambda q_arr, i_arr, cfg=None: 1.0)
    monkeypatch.setattr(module, "bragg_long_period", lambda q_arr, i_arr: (10.0, 0.628, {}))

    result = analyze_temperature_series(
        [170.0, 180.0], [q, q], [intensity, intensity], cfg=SAXSConfig()
    )

    assert result.temp_points[0].guinier_evidence is not None
    assert result.temp_points[1].guinier_evidence is None
    assert result.temp_points[1].guinier_level == "Unusable"
    assert result.metric_evidence["guinier"]["missing_frame_count"] == 1
    assert result.metric_evidence["guinier"]["evidence_frame_count"] == 1
    assert result.metric_evidence["guinier"]["level"] == "Diagnostic"


def test_temperature_invariant_failure_isolated_to_middle_frame(monkeypatch):
    import polynexus.core.saxs_engine.saxs_temperature as module

    q = np.linspace(0.02, 0.6, 24)
    intensity = 120.0 * np.exp(-(q**2) * 4.0**2 / 3.0)
    invariant_calls = {"count": 0}

    def flaky_invariant(q_arr, i_arr, cfg=None):
        del q_arr, i_arr, cfg
        invariant_calls["count"] += 1
        if invariant_calls["count"] == 3:
            raise RuntimeError("injected middle-frame invariant failure")
        return 1.0

    monkeypatch.setattr(module, "analyze_single", lambda q_arr, i_arr, cfg: _fake_frame_result(q_arr, i_arr))
    monkeypatch.setattr(module, "scattering_invariant", flaky_invariant)
    monkeypatch.setattr(module, "bragg_long_period", lambda q_arr, i_arr: (10.0, 0.628, {}))

    result = analyze_temperature_series(
        [170.0, 180.0, 190.0],
        [q, q, q],
        [intensity, intensity, intensity],
        cfg=SAXSConfig(),
        exp_type="cooling",
    )

    assert len(result.temp_points) == 3
    assert np.isfinite(result.temp_points[0].Q_star)
    assert not np.isfinite(result.temp_points[1].Q_star)
    assert "temperature_frame_invariant_unavailable" in result.temp_points[1].warnings
    assert np.isfinite(result.temp_points[2].Q_star)
    assert result.temp_points[2].guinier_evidence is not None


def test_temperature_reference_failures_do_not_abort_later_frames(monkeypatch):
    import polynexus.core.saxs_engine.saxs_temperature as module

    q = np.linspace(0.02, 0.6, 24)
    intensity = 120.0 * np.exp(-(q**2) * 4.0**2 / 3.0)

    def failing_reference_invariant(q_arr, i_arr, cfg=None):
        del q_arr, i_arr, cfg
        if not hasattr(failing_reference_invariant, "calls"):
            failing_reference_invariant.calls = 0
        failing_reference_invariant.calls += 1
        if failing_reference_invariant.calls == 1:
            raise RuntimeError("injected reference invariant failure")
        return 1.0

    def failing_reference_long_period(q_arr, i_arr):
        del q_arr, i_arr
        raise RuntimeError("injected reference long-period failure")

    monkeypatch.setattr(module, "analyze_single", lambda q_arr, i_arr, cfg: _fake_frame_result(q_arr, i_arr))
    monkeypatch.setattr(module, "scattering_invariant", failing_reference_invariant)
    monkeypatch.setattr(module, "bragg_long_period", failing_reference_long_period)

    result = analyze_temperature_series(
        [170.0, 180.0, 190.0],
        [q, q, q],
        [intensity, intensity, intensity],
        cfg=SAXSConfig(),
        exp_type="cooling",
    )

    assert len(result.temp_points) == 3
    assert result.temp_points[1].guinier_evidence is not None
    assert result.temp_points[2].guinier_evidence is not None
    assert all(np.isfinite(point.Q_star) for point in result.temp_points)
    assert not any(np.isfinite(point.Xc_relative) for point in result.temp_points)
    assert "temperature_reference_invariant_unavailable" in result.temp_points[0].warnings
    assert "temperature_reference_long_period_unavailable" in result.temp_points[0].warnings


def test_temperature_series_attaches_sequence_guinier_evidence(monkeypatch):
    import polynexus.core.saxs_engine.saxs_temperature as module

    q = np.linspace(0.02, 0.6, 24)
    intensity = 120.0 * np.exp(-(q**2) * 4.0**2 / 3.0)

    monkeypatch.setattr(module, "analyze_single", lambda q_arr, i_arr, cfg: _fake_frame_result(q_arr, i_arr))
    monkeypatch.setattr(module, "scattering_invariant", lambda q_arr, i_arr, cfg=None: 1.0)
    monkeypatch.setattr(module, "bragg_long_period", lambda q_arr, i_arr: (10.0, 0.628, {}))

    result = analyze_temperature_series(
        [170.0, 180.0, 190.0], [q, q, q], [intensity, intensity, intensity], cfg=SAXSConfig()
    )

    assert len(result.temp_points) == 3
    assert result.guinier_sequence_evidence["level"] == "Trend"
    assert result.guinier_sequence_evidence["valid_frame_count"] == 3
    assert result.metric_evidence["guinier"]["metric_name"] == "guinier"
    assert result.metric_evidence["guinier"]["frame_count"] == 3
    assert result.metric_evidence["guinier"]["evidence_frame_count"] == 3
    assert result.metric_evidence["guinier"]["level"] == "Trend"
    frame_table = result.to_dataframe()
    assert "Rg_sequence_level" in frame_table.columns
    assert set(frame_table["Rg_sequence_level"]) == {"Trend"}


def test_temperature_sequence_evidence_retains_original_source_indices_after_sort(monkeypatch):
    import polynexus.core.saxs_engine.saxs_temperature as module

    q = np.linspace(0.02, 0.6, 24)
    intensity = 120.0 * np.exp(-(q**2) * 4.0**2 / 3.0)

    monkeypatch.setattr(module, "analyze_single", lambda q_arr, i_arr, cfg: _fake_frame_result(q_arr, i_arr))
    monkeypatch.setattr(module, "scattering_invariant", lambda q_arr, i_arr, cfg=None: 1.0)
    monkeypatch.setattr(module, "bragg_long_period", lambda q_arr, i_arr: (10.0, 0.628, {}))

    result = analyze_temperature_series(
        [180.0, 170.0], [q, q], [intensity, intensity], cfg=SAXSConfig()
    )

    assert [point.temperature_C for point in result.temp_points] == [170.0, 180.0]
    assert [point.source_index for point in result.temp_points] == [1, 0]
    assert result.guinier_sequence_evidence["frame_source_indices"] == [1, 0]
    assert result.metric_evidence["guinier"]["frame_source_indices"] == [1, 0]
    axis = result.metric_evidence["guinier"]["condition_axis"]
    assert axis["condition_name"] == "temperature_C"
    assert axis["condition_values"] == [170.0, 180.0]
    assert axis["status"] == "ordered"
    assert list(result.to_dataframe()["source_index"]) == [1, 0]


def test_temperature_series_exposes_existing_lc_alternative_as_candidate_only(monkeypatch):
    import polynexus.core.saxs_engine.saxs_temperature as module

    q = np.linspace(0.02, 0.6, 24)
    intensity = 120.0 * np.exp(-(q**2) * 4.0**2 / 3.0)

    monkeypatch.setattr(module, "analyze_single", lambda q_arr, i_arr, cfg: _fake_frame_result(q_arr, i_arr))
    monkeypatch.setattr(module, "scattering_invariant", lambda q_arr, i_arr, cfg=None: 1.0)
    monkeypatch.setattr(module, "bragg_long_period", lambda q_arr, i_arr: (10.0, 0.628, {}))

    def fake_select(points):
        return [None for _ in points]

    def fake_apply(points, decisions):
        del decisions
        points[0].lc_effective_nm = 3.2
        points[0].lc_effective_source = "tangent"
        points[0].lc_path_status = "low_confidence"
        points[0].lc_path_reason = "selected=tangent|selection_margin=0.2"

    monkeypatch.setattr(module, "select_lc_sequence_path", fake_select)
    monkeypatch.setattr(module, "apply_lc_path_decisions", fake_apply)

    result = analyze_temperature_series(
        [170.0, 180.0], [q, q], [intensity, intensity], cfg=SAXSConfig()
    )

    assert len(result.sequence_rescue_candidates) == 1
    candidate = result.sequence_rescue_candidates[0]
    assert candidate["parameters"]["apply_mode"] == "candidate_only"
    assert candidate["parameters"]["preserve_missing_frames"] is True
    assert result.temp_points[0].lc_nm == 3.0
    assert result.to_dataframe().loc[0, "sequence_rescue_candidate"] == candidate["candidate_id"]
