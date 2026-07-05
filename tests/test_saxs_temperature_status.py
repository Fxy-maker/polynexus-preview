from __future__ import annotations

import numpy as np
import pytest

from polynexus.core.engine import get_engine
from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.core import LongPeriodResult, SAXSResult, StructureParams
from polynexus.core.saxs_engine.saxs_temperature import (
    TempSeriesResult,
    TemperaturePointResult,
    analyze_temperature_series,
    classify_lc_reliability_status,
    classify_melting_window_status,
    detect_melting_from_saxs,
)


def test_classify_melting_window_status_prefers_sequence_window() -> None:
    temperatures = np.asarray([170.0, 185.0, 195.0, 205.0, 220.0], dtype=float)

    assert classify_melting_window_status(170.0, 195.0, 205.0, 220.0, temperatures)[0] == "outside_window"
    assert classify_melting_window_status(195.0, 195.0, 205.0, 220.0, temperatures)[0] == "near_onset"
    assert classify_melting_window_status(205.0, 195.0, 205.0, 220.0, temperatures)[0] == "within_window"
    assert classify_melting_window_status(230.0, 195.0, 205.0, 220.0, temperatures)[0] == "post_end"
    assert classify_melting_window_status(185.0, np.nan, np.nan, np.nan, temperatures)[0] == "undetermined"


def test_classify_lc_reliability_status_keeps_melting_and_stability_separate() -> None:
    stable_point = TemperaturePointResult(
        temperature_C=170.0,
        L_nm=10.0,
        lc_nm=3.5,
        la_nm=6.5,
        Q_star=3.0,
        lc_confidence=0.72,
        melting_window_status="outside_window",
    )
    assert classify_lc_reliability_status(stable_point) == ("usable", "stable_structure_support")

    weak_point = TemperaturePointResult(
        temperature_C=195.0,
        L_nm=10.0,
        lc_nm=1.0,
        la_nm=9.0,
        Q_star=3.0,
        lc_confidence=0.18,
        melting_window_status="outside_window",
    )
    weak_status, weak_reason = classify_lc_reliability_status(weak_point)
    assert weak_status == "diagnostic_only"
    assert "low_lc_confidence" in weak_reason
    assert "within_melting_window" not in weak_reason

    melting_point = TemperaturePointResult(
        temperature_C=205.0,
        L_nm=10.0,
        lc_nm=2.2,
        la_nm=7.8,
        Q_star=3.0,
        lc_confidence=0.42,
        melting_window_status="within_window",
    )
    melting_status, melting_reason = classify_lc_reliability_status(melting_point)
    assert melting_status == "diagnostic_only"
    assert "within_melting_window" in melting_reason


def test_classify_lc_reliability_status_downgrades_sequence_break_before_melting() -> None:
    previous_point = TemperaturePointResult(
        temperature_C=170.0,
        L_nm=10.0,
        lc_nm=3.2,
        la_nm=6.8,
        Q_star=4.0,
        lc_confidence=0.62,
        melting_window_status="outside_window",
    )
    unstable_point = TemperaturePointResult(
        temperature_C=185.0,
        L_nm=9.8,
        lc_nm=1.1,
        la_nm=8.7,
        Q_star=1.7,
        lc_confidence=0.31,
        melting_window_status="undetermined",
    )

    status, reason = classify_lc_reliability_status(
        unstable_point,
        peak_intensity_ratio=0.48,
        q_invariant_ratio=0.43,
        previous_point=previous_point,
    )

    assert status == "diagnostic_only"
    assert "melting_window_undetermined" in reason
    assert "sequence_crystallinity_drop" in reason
    assert "sequence_continuity_break" in reason


def test_detect_melting_from_saxs_ignores_single_frame_dip() -> None:
    temperatures = np.asarray([170.0, 185.0, 195.0, 205.0], dtype=float)
    q_star = np.asarray([10.0, 10.0, 10.0, 10.0], dtype=float)
    peak_intensity = np.asarray([100.0, 94.0, 97.0, 8.0], dtype=float)

    melting = detect_melting_from_saxs(temperatures, q_star, peak_intensity)

    assert melting["Tm_onset_C"] == 205.0
    assert melting["Tm_50pct_C"] == 205.0


def test_detect_melting_from_saxs_uses_a_robust_initial_baseline() -> None:
    temperatures = np.asarray([170.0, 185.0, 195.0, 205.0], dtype=float)
    q_star = np.asarray([10.0, 10.0, 10.0, 10.0], dtype=float)
    peak_intensity = np.asarray([140.0, 100.0, 98.0, 8.0], dtype=float)

    melting = detect_melting_from_saxs(temperatures, q_star, peak_intensity)

    assert melting["Tm_onset_C"] == 205.0
    assert melting["Tm_50pct_C"] == 205.0


def test_classify_melting_window_status_can_surface_expected_melt_prior_hint() -> None:
    status, reason = classify_melting_window_status(
        215.0,
        np.nan,
        np.nan,
        np.nan,
        np.asarray([170.0, 185.0, 195.0, 215.0], dtype=float),
        220.0,
    )

    assert status == "undetermined"
    assert reason == "expected_melt_prior_hint"


def test_default_temperature_config_does_not_inject_hidden_expected_melt_prior() -> None:
    status, reason = classify_melting_window_status(
        215.0,
        np.nan,
        np.nan,
        np.nan,
        np.asarray([170.0, 185.0, 195.0, 215.0], dtype=float),
        None,
    )

    assert status == "undetermined"
    assert reason == "melting_onset_unresolved"


def test_classify_lc_reliability_status_uses_expected_melt_prior_as_soft_warning() -> None:
    point = TemperaturePointResult(
        temperature_C=215.0,
        L_nm=10.0,
        lc_nm=3.0,
        la_nm=7.0,
        Q_star=3.0,
        lc_confidence=0.72,
        melting_window_status="undetermined",
        melting_window_reason="expected_melt_prior_hint",
    )

    status, reason = classify_lc_reliability_status(point)

    assert status == "low_confidence"
    assert "expected_melt_prior_hint" in reason


def test_classify_lc_reliability_status_flags_single_method_fragility() -> None:
    point = TemperaturePointResult(
        temperature_C=170.0,
        L_nm=10.0,
        lc_nm=3.0,
        la_nm=7.0,
        Q_star=3.0,
        lc_confidence=0.42,
        melting_window_status="outside_window",
        lc_tangent_nm=3.0,
    )

    status, reason = classify_lc_reliability_status(point)

    assert status == "low_confidence"
    assert "single_method_fragile" in reason


def test_classify_lc_reliability_status_flags_method_conflict() -> None:
    point = TemperaturePointResult(
        temperature_C=170.0,
        L_nm=10.0,
        lc_nm=3.0,
        la_nm=7.0,
        Q_star=3.0,
        lc_confidence=0.72,
        melting_window_status="outside_window",
        lc_tangent_nm=2.0,
        lc_idf_nm=4.0,
        lc_gamma_min_nm=6.0,
    )

    status, reason = classify_lc_reliability_status(point)

    assert status == "low_confidence"
    assert "method_conflict" in reason


def test_analyze_temperature_series_assigns_frame_statuses(monkeypatch: pytest.MonkeyPatch) -> None:
    import polynexus.core.saxs_engine.saxs_temperature as saxs_temperature

    q = np.asarray([0.50, 0.62831853, 0.80], dtype=float)
    q_list = [q, q, q, q]
    i_list = [
        np.asarray([5.0, 100.0, 2.0], dtype=float),
        np.asarray([5.0, 96.0, 2.0], dtype=float),
        np.asarray([5.0, 40.0, 2.0], dtype=float),
        np.asarray([5.0, 0.5, 2.0], dtype=float),
    ]
    temperatures = [170.0, 185.0, 195.0, 220.0]

    confidence_by_temp = {
        170.0: 0.72,
        185.0: 0.55,
        195.0: 0.18,
        220.0: 0.10,
    }

    def fake_analyze_single(q_arr, i_arr, cfg):
        temp = temperatures[len([item for item in getattr(fake_analyze_single, "calls", [])])]
        calls = getattr(fake_analyze_single, "calls", [])
        calls.append(temp)
        fake_analyze_single.calls = calls
        conf = confidence_by_temp[temp]
        return SAXSResult(
            long_period=LongPeriodResult(L_best=10.0, L_confidence=0.65, method_used="bragg"),
            structure=StructureParams(L=10.0, lc=3.0 if temp < 195.0 else 1.0, la=7.0 if temp < 195.0 else 9.0, phi_c=0.3 if temp < 195.0 else 0.1, confidence_lc=conf),
        )

    monkeypatch.setattr(saxs_temperature, "analyze_single", fake_analyze_single)
    monkeypatch.setattr(saxs_temperature, "scattering_invariant", lambda q_arr, i_arr, cfg=None: float(np.nanmax(i_arr)))
    monkeypatch.setattr(saxs_temperature, "bragg_long_period", lambda q_arr, i_arr: (10.0, float(2 * np.pi / 10.0), {}))

    result = analyze_temperature_series(temperatures, q_list, i_list, cfg=SAXSConfig())

    assert result.Tm_onset == 195.0
    assert result.Tm_end == 220.0
    assert result.temp_points[0].melting_window_status == "outside_window"
    assert result.temp_points[2].melting_window_status == "near_onset"
    assert result.temp_points[3].melting_window_status == "within_window"
    assert result.temp_points[2].lc_reliability_status == "diagnostic_only"
    assert "low_lc_confidence" in result.temp_points[2].lc_reliability_reason


def test_analyze_temperature_series_marks_pre_onset_instability_as_diagnostic(monkeypatch: pytest.MonkeyPatch) -> None:
    import polynexus.core.saxs_engine.saxs_temperature as saxs_temperature

    q = np.asarray([0.50, 0.62831853, 0.80], dtype=float)
    q_list = [q, q, q, q]
    i_list = [
        np.asarray([5.0, 100.0, 2.0], dtype=float),
        np.asarray([5.0, 94.0, 2.0], dtype=float),
        np.asarray([5.0, 97.0, 2.0], dtype=float),
        np.asarray([5.0, 8.0, 2.0], dtype=float),
    ]
    temperatures = [170.0, 185.0, 195.0, 205.0]

    def fake_analyze_single(q_arr, i_arr, cfg):
        temp = temperatures[len([item for item in getattr(fake_analyze_single, "calls", [])])]
        calls = getattr(fake_analyze_single, "calls", [])
        calls.append(temp)
        fake_analyze_single.calls = calls
        mapping = {
            170.0: (10.0, 3.2, 6.8, 0.32, 0.70),
            185.0: (9.8, 1.1, 8.7, 0.11, 0.31),
            195.0: (9.7, 3.0, 6.7, 0.31, 0.58),
            205.0: (9.6, 1.0, 8.6, 0.10, 0.18),
        }
        L, lc, la, phi_c, conf = mapping[temp]
        return SAXSResult(
            long_period=LongPeriodResult(L_best=L, L_confidence=0.60, method_used="bragg"),
            structure=StructureParams(L=L, lc=lc, la=la, phi_c=phi_c, confidence_lc=conf),
        )

    monkeypatch.setattr(saxs_temperature, "analyze_single", fake_analyze_single)
    monkeypatch.setattr(saxs_temperature, "scattering_invariant", lambda q_arr, i_arr, cfg=None: float(np.nanmax(i_arr)))
    monkeypatch.setattr(saxs_temperature, "bragg_long_period", lambda q_arr, i_arr: (10.0, float(2 * np.pi / 10.0), {}))

    result = analyze_temperature_series(temperatures, q_list, i_list, cfg=SAXSConfig())

    assert result.Tm_onset == 205.0
    assert result.temp_points[1].melting_window_status == "outside_window"
    assert result.temp_points[1].lc_reliability_status == "diagnostic_only"
    assert "melting_window_undetermined" not in result.temp_points[1].lc_reliability_reason
    assert "sequence_continuity_break" in result.temp_points[1].lc_reliability_reason


def test_temperature_pipeline_threads_status_fields_into_batch_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    import polynexus.core.saxs as saxs_module

    engine = get_engine("saxs", config=SAXSConfig(experiment_type="temperature"))
    assert engine is not None

    engine._q = np.asarray([0.5, 0.6], dtype=float)  # type: ignore[attr-defined]
    engine._q_list = [np.asarray([0.5, 0.6], dtype=float), np.asarray([0.5, 0.6], dtype=float)]  # type: ignore[attr-defined]
    engine._I_list = [np.asarray([10.0, 20.0], dtype=float), np.asarray([8.0, 12.0], dtype=float)]  # type: ignore[attr-defined]
    engine._conditions = [170.0, 195.0]  # type: ignore[attr-defined]
    engine._file_list = ["frame_170.edf", "frame_195.edf"]  # type: ignore[attr-defined]

    fake_results = {
        170.0: SAXSResult(
            long_period=LongPeriodResult(L_best=10.0, L_confidence=0.6, method_used="bragg"),
            structure=StructureParams(L=10.0, lc=3.4, la=6.6, phi_c=0.34, confidence_lc=0.66),
        ),
        195.0: SAXSResult(
            long_period=LongPeriodResult(L_best=9.6, L_confidence=0.4, method_used="bragg"),
            structure=StructureParams(L=9.6, lc=1.2, la=8.4, phi_c=0.125, confidence_lc=0.18),
        ),
    }

    def fake_analyze_single(q_arr, i_arr, cfg, q_anchor=None):
        idx = 0 if np.nanmax(i_arr) == 20.0 else 1
        temp = engine._conditions[idx]  # type: ignore[attr-defined]
        return fake_results[temp]

    temp_result = TempSeriesResult(
        temperatures=np.asarray([170.0, 195.0], dtype=float),
        lc_array=np.asarray([3.4, 1.2], dtype=float),
        L_array=np.asarray([10.0, 9.6], dtype=float),
        Q_star_array=np.asarray([20.0, 12.0], dtype=float),
        Xc_array=np.asarray([1.0, 0.6], dtype=float),
        Tm_onset=195.0,
        Tm_peak=195.0,
        Tm_end=np.nan,
        temp_points=[
            TemperaturePointResult(
                source_index=0,
                temperature_C=170.0,
                melting_window_status="outside_window",
                melting_window_reason="below_sequence_melting_onset",
                lc_reliability_status="usable",
                lc_reliability_reason="stable_structure_support",
            ),
            TemperaturePointResult(
                source_index=1,
                temperature_C=195.0,
                melting_window_status="near_onset",
                melting_window_reason="near_sequence_melting_onset",
                lc_reliability_status="diagnostic_only",
                lc_reliability_reason="low_lc_confidence|near_melting_onset",
            ),
        ],
    )

    monkeypatch.setattr(saxs_module, "analyze_single", fake_analyze_single)
    monkeypatch.setattr(saxs_module, "analyze_temperature_series", lambda temperatures, q_list, I_list, cfg: temp_result)

    assert engine._run_temperature_pipeline() is True  # type: ignore[attr-defined]

    batch_rows = engine.get_parameters()["_batch_data"]
    assert batch_rows[0]["melting_window_status"] == "outside_window"
    assert batch_rows[0]["lc_reliability_status"] == "usable"
    assert batch_rows[1]["melting_window_status"] == "near_onset"
    assert batch_rows[1]["lc_reliability_status"] == "diagnostic_only"
    assert batch_rows[1]["lc_reliability_reason"] == "low_lc_confidence|near_melting_onset"
    assert engine.get_parameters()["Tm_onset_C"] == 195.0
