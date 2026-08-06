from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from polynexus.core import get_engine
from polynexus.core.analysis_evidence import build_analysis_evidence
from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.core import bragg_long_period
from polynexus.core.saxs_engine.core import LongPeriodResult, SAXSResult, StructureParams
from polynexus.core.saxs_engine.saxs_strain import (
    StrainPhase,
    StrainPointResult,
    StrainSeriesResult,
    analyze_strain_series,
)


def _gaussian(
    q: np.ndarray,
    center: float,
    amplitude: float,
    width: float = 0.018,
) -> np.ndarray:
    return amplitude * np.exp(-0.5 * ((q - center) / width) ** 2)


def _sector_payload(q: np.ndarray, radial: np.ndarray, source_index: int) -> dict:
    chi = np.linspace(-np.pi, np.pi, 72, endpoint=False)
    angular = 1.0 + 1.8 * np.cos(chi) ** 2
    return {
        "I_2d": np.outer(angular, radial),
        "q_2d": q,
        "q": q,
        "chi_rad": chi,
        "I_full": radial,
        "I_merid": radial,
        "I_equat": radial,
        "support_count": np.ones((chi.size, q.size), dtype=float),
        "frame_source_index": source_index,
    }


def test_strain_tracking_loss_blocks_orientation_and_later_peak_restart() -> None:
    q = np.linspace(0.20, 1.20, 600)
    seeded = 0.02 + _gaussian(q, 0.72, 12.0)
    missing = 0.02 + _gaussian(q, 0.45, 20.0)
    reappeared = 0.02 + _gaussian(q, 0.73, 12.0)

    result = analyze_strain_series(
        strains=[0.0, 20.0, 40.0],
        q_list=[q, q, q],
        I_list=[seeded, missing, reappeared],
        sector_data_list=[
            _sector_payload(q, seeded, 0),
            _sector_payload(q, missing, 1),
            _sector_payload(q, reappeared, 2),
        ],
        frame_source_indices=[0, 1, 2],
        cfg=SAXSConfig(
            smooth_method="none",
            q_min=0.20,
            q_bragg_min=0.30,
            q_bragg_max=1.00,
            tensile_axis_deg=0.0,
        ),
    )

    first, lost, locked = result.strain_points
    assert first.feature_tracking_status == "seeded"
    assert lost.feature_tracking_status == "tracking_lost"
    assert locked.feature_tracking_status == "tracking_lost"
    assert "tracking_already_lost" in locked.feature_tracking_reason_codes
    assert np.isnan(lost.q_peak_total_nm1)
    assert np.isnan(locked.q_peak_total_nm1)
    assert np.isnan(lost.f_herman)
    assert np.isnan(locked.f_herman)
    assert "tracked_feature_unavailable" in lost.orientation_evidence["reason_codes"]
    assert "tracked_feature_unavailable" in locked.orientation_evidence["reason_codes"]
    assert np.isnan(lost.analysis_result.long_period.q_peak_nm1)
    assert np.isnan(locked.analysis_result.long_period.q_peak_nm1)


def test_strain_core_exception_after_seed_irreversibly_loses_tracking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import polynexus.core.saxs_engine.saxs_strain as strain_module

    q = np.linspace(0.20, 1.20, 600)
    seeded = 0.02 + _gaussian(q, 0.72, 12.0)
    reappeared = 0.02 + _gaussian(q, 0.73, 12.0)
    real_analyze_single = strain_module.analyze_single
    call_count = 0

    def _raise_on_middle_frame(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise RuntimeError("synthetic middle-frame failure")
        return real_analyze_single(*args, **kwargs)

    monkeypatch.setattr(strain_module, "analyze_single", _raise_on_middle_frame)

    result = analyze_strain_series(
        strains=[0.0, 20.0, 40.0],
        q_list=[q, q, q],
        I_list=[seeded, seeded, reappeared],
        frame_source_indices=[0, 1, 2],
        cfg=SAXSConfig(
            smooth_method="none",
            q_min=0.20,
            q_bragg_min=0.30,
            q_bragg_max=1.00,
        ),
    )

    first, failed, locked = result.strain_points
    assert first.feature_tracking_status == "seeded"
    assert failed.feature_tracking_status == "tracking_lost"
    assert failed.analysis_result is not None
    assert failed.analysis_result.validation_summary.startswith(
        "strain_core_analysis_failed:"
    )
    assert "core_analysis_failed" in failed.feature_tracking_reason_codes
    assert locked.feature_tracking_status == "tracking_lost"
    assert "tracking_already_lost" in locked.feature_tracking_reason_codes
    assert np.isnan(locked.q_peak_total_nm1)


def test_unseeded_and_lost_frames_do_not_publish_lamellar_structure() -> None:
    q = np.linspace(0.20, 1.20, 600)
    no_peak = np.exp(q)
    seeded = 0.02 + _gaussian(q, 0.72, 12.0)
    lost = 0.02 + _gaussian(q, 0.45, 20.0)

    result = analyze_strain_series(
        strains=[0.0, 20.0, 40.0],
        q_list=[q, q, q],
        I_list=[no_peak, seeded, lost],
        frame_source_indices=[0, 1, 2],
        cfg=SAXSConfig(
            smooth_method="none",
            q_min=0.20,
            q_bragg_min=0.30,
            q_bragg_max=1.00,
        ),
    )

    for point in (result.strain_points[0], result.strain_points[2]):
        assert point.feature_tracking_status in {"unseeded", "tracking_lost"}
        assert np.isnan(point.L_nm)
        assert np.isnan(point.lc_nm)
        assert np.isnan(point.la_nm)
        assert np.isnan(point.phi_c)
        assert point.confidence == 0.0
        structure = point.analysis_result.structure
        assert point.analysis_result.long_period.L_confidence == 0.0
        assert np.isnan(structure.L)
        assert np.isnan(structure.lc)
        assert np.isnan(structure.la)
        assert np.isnan(structure.phi_c)
        lamellar = point.analysis_result.metric_evidence["lamellar"]
        assert lamellar["applicable"] is False
        assert "tracked_feature_unavailable" in lamellar["reason_codes"]


def _engine_with_tracking_loss(monkeypatch: pytest.MonkeyPatch):
    from polynexus.core import saxs as saxs_module

    q = np.linspace(0.20, 1.20, 120)
    intensity = 0.02 + _gaussian(q, 0.72, 12.0)
    analyses = [
        SAXSResult(
            long_period=LongPeriodResult(L_best=8.7, q_peak_nm1=0.72),
            structure=StructureParams(L=8.7, lc=3.0, la=5.7, phi_c=0.34),
            porod={"slope": -4.0},
        ),
        SAXSResult(
            long_period=LongPeriodResult(),
            structure=StructureParams(),
            porod={"slope": -4.0},
        ),
        SAXSResult(
            long_period=LongPeriodResult(),
            structure=StructureParams(),
            porod={"slope": -4.0},
        ),
    ]
    points = [
        StrainPointResult(
            strain_pct=0.0,
            phase=StrainPhase.ELASTIC,
            L_nm=8.7,
            q_peak_total_nm1=0.72,
            feature_tracking_status="seeded",
            invariant_Q=4.0,
            invariant_Q_rel=1.0,
            analysis_result=analyses[0],
        ),
        StrainPointResult(
            strain_pct=20.0,
            phase=StrainPhase.ELASTIC,
            feature_tracking_status="tracking_lost",
            invariant_Q=3.8,
            invariant_Q_rel=0.95,
            analysis_result=analyses[1],
        ),
        StrainPointResult(
            strain_pct=40.0,
            phase=StrainPhase.ELASTIC,
            feature_tracking_status="tracking_lost",
            invariant_Q=3.6,
            invariant_Q_rel=0.90,
            analysis_result=analyses[2],
        ),
    ]
    series = StrainSeriesResult(
        strain_points=points,
        strains=np.asarray([0.0, 20.0, 40.0]),
        L_array=np.asarray([8.7, np.nan, np.nan]),
        lc_array=np.asarray([3.0, np.nan, np.nan]),
        la_array=np.asarray([5.7, np.nan, np.nan]),
        invariant_Q_array=np.asarray([4.0, 3.8, 3.6]),
        invariant_Q_rel_array=np.asarray([1.0, 0.95, 0.90]),
        f_herman_array=np.full(3, np.nan),
        phi_void_array=np.full(3, np.nan),
    )
    monkeypatch.setattr(saxs_module, "analyze_strain_series", lambda **_kwargs: series)
    engine = saxs_module.SAXSEngine(
        config=saxs_module.SAXSConfig(experiment_type="strain")
    )
    engine._q_list = [q, q, q]  # type: ignore[attr-defined]
    engine._I_list = [intensity, intensity, intensity]  # type: ignore[attr-defined]
    engine._I_merid_list = [None, None, None]  # type: ignore[attr-defined]
    engine._I_equat_list = [None, None, None]  # type: ignore[attr-defined]
    engine._q_pyfai_list = [np.array([])] * 3  # type: ignore[attr-defined]
    engine._I_pyfai_list = [np.array([])] * 3  # type: ignore[attr-defined]
    engine._conditions = [0.0, 20.0, 40.0]  # type: ignore[attr-defined]
    engine._condition_confidences = [1.0, 1.0, 1.0]  # type: ignore[attr-defined]
    engine._file_list = ["0.edf", "20.edf", "40.edf"]  # type: ignore[attr-defined]
    engine._sector_data_list = [None, None, None]  # type: ignore[attr-defined]
    return engine, analyses


def test_engine_keeps_rows_aligned_when_tracking_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, analyses = _engine_with_tracking_loss(monkeypatch)

    assert engine._run_strain_pipeline() is True  # type: ignore[attr-defined]
    assert len(engine._batch_params) == len(engine._batch_results) == 3  # type: ignore[attr-defined]
    assert engine._batch_results == analyses  # type: ignore[attr-defined]
    for row in engine._batch_params[1:]:  # type: ignore[attr-defined]
        assert row["L_nm"] is None
        assert row["lc_nm"] is None
        assert row["la_nm"] is None
        assert row["Xc"] is None


def test_engine_never_runs_sasmodels_after_tracking_loss(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, _analyses = _engine_with_tracking_loss(monkeypatch)
    calls: list[float] = []

    def _fit(_q, _intensity, long_period, _structure):
        calls.append(float(long_period))
        return 3.0, 6.0, 0.333, "sasmodels", "lamellar", 0.95

    monkeypatch.setattr(engine, "_try_sasmodels_lc", _fit)

    assert engine._run_strain_pipeline() is True  # type: ignore[attr-defined]
    assert calls == [pytest.approx(8.7)]
    for row in engine._batch_params[1:]:  # type: ignore[attr-defined]
        assert row["lc_nm"] is None
        assert row["la_nm"] is None
        assert row["Xc"] is None


def test_missing_reference_invariant_does_not_fabricate_relative_unity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import polynexus.core.saxs_engine.saxs_strain as strain_module

    q = np.asarray([0.2], dtype=float)
    intensity = np.asarray([1.0], dtype=float)
    monkeypatch.setattr(
        strain_module,
        "scattering_invariant",
        lambda *_args, **_kwargs: np.nan,
    )

    result = analyze_strain_series(
        strains=[0.0, 20.0],
        q_list=[q, q],
        I_list=[intensity, intensity],
        cfg=SAXSConfig(smooth_method="none", q_min=0.2),
    )

    assert np.all(np.isnan(result.invariant_Q_array))
    assert np.all(np.isnan(result.invariant_Q_rel_array))
    assert all(np.isnan(point.invariant_Q_rel) for point in result.strain_points)


def test_strain_new_outputs_use_invariant_names() -> None:
    q = np.linspace(0.20, 1.20, 600)
    first = 0.02 + _gaussian(q, 0.72, 12.0)
    second = 0.02 + _gaussian(q, 0.73, 12.0)
    result = analyze_strain_series(
        strains=[0.0, 20.0],
        q_list=[q, q],
        I_list=[first, second],
        frame_source_indices=[0, 1],
        cfg=SAXSConfig(
            smooth_method="none",
            q_min=0.20,
            q_bragg_min=0.30,
            q_bragg_max=1.00,
        ),
    )

    assert np.isfinite(result.strain_points[0].invariant_Q)
    assert result.strain_points[0].invariant_Q_rel == 1.0
    assert np.isnan(result.strain_points[0].Q_star)
    assert np.isnan(result.strain_points[0].Q_star_rel)
    assert result.Q_star_array is None
    assert result.Q_star_rel_array is None
    np.testing.assert_allclose(
        result.invariant_Q_array,
        [point.invariant_Q for point in result.strain_points],
    )
    np.testing.assert_allclose(
        result.invariant_Q_rel_array,
        [point.invariant_Q_rel for point in result.strain_points],
    )
    frame = result.to_dataframe()
    assert "invariant_Q" in frame.columns
    assert "invariant_Q_rel" in frame.columns
    assert "Q_star" not in frame.columns
    assert "Q_star_rel" not in frame.columns

    engine = get_engine("saxs", submodule_id="saxs.strain")
    assert engine is not None
    engine._strain_result = result  # type: ignore[attr-defined]
    engine._conditions = [0.0, 20.0]  # type: ignore[attr-defined]
    engine._condition_confidences = [1.0, 1.0]  # type: ignore[attr-defined]
    parameters = engine.get_parameters()
    assert "invariant_Q_range" in parameters
    assert "invariant_Q_rel_mean" in parameters
    assert "Q_star_range" not in parameters
    assert "Q_star_rel_mean" not in parameters


def test_saxs_evidence_reader_accepts_canonical_invariant_names() -> None:
    evidence = build_analysis_evidence(
        "SAXS",
        output_parameters={
            "condition_label": "strain",
            "invariant_Q_rel_mean": 1.08,
            "invariant_Q_rel_span": 0.11,
            "L_bragg": 11.8,
            "L_corr_peak": 9.9,
            "L_best": 12.1,
            "has_voids": True,
            "phi_void_mean": 0.034,
        },
    ).to_dict()

    assert evidence["structure_evidence"]["invariant_Q_rel_mean"] == 1.08
    assert evidence["structure_evidence"]["invariant_Q_rel_span"] == 0.11
    assert not any(
        key.startswith("Q_star") for key in evidence["structure_evidence"]
    )
    assert (
        evidence["feature_evidence"]["strain_structure_evidence"][
            "invariant_Q_rel_mean"
        ]
        == 1.08
    )
    conflict = next(
        item
        for item in evidence["constraints"]
        if item["name"] == "strain_void_lamellar_conflict"
    )
    assert conflict["observed"]["invariant_Q_rel"] == 1.08
    assert conflict["observed"]["invariant_Q_rel_span"] == 0.11


def test_anchored_bragg_rejects_low_snr_and_no_peak_fallbacks() -> None:
    q = np.linspace(0.30, 1.00, 500)
    low_snr = 1.0 + 0.002 * np.sin(q * 20.0)
    no_peak = np.exp(q)

    for intensity in (low_snr, no_peak):
        length, q_peak, info = bragg_long_period(
            q,
            intensity,
            q_min=0.30,
            q_max=1.00,
            q_anchor=0.72,
            max_anchor_relative_shift=0.25,
        )
        assert np.isnan(length)
        assert np.isnan(q_peak)
        assert info["selected_reason"] == "anchor_tracking_lost"


def test_strain_seed_requires_a_formal_peak_and_step_cap_cannot_be_relaxed() -> None:
    q = np.linspace(0.20, 1.20, 600)
    no_peak = np.exp(q)
    seed = 0.02 + _gaussian(q, 0.72, 12.0)
    distant = 0.02 + _gaussian(q, 0.45, 20.0)

    late_seed = analyze_strain_series(
        strains=[0.0, 5.0],
        q_list=[q, q],
        I_list=[no_peak, seed],
        frame_source_indices=[0, 1],
        cfg=SAXSConfig(
            smooth_method="none",
            q_min=0.20,
            q_bragg_min=0.30,
            q_bragg_max=1.00,
        ),
    )
    assert late_seed.strain_points[0].feature_tracking_status == "unseeded"
    assert np.isnan(late_seed.strain_points[0].q_peak_total_nm1)
    assert late_seed.strain_points[1].feature_tracking_status == "seeded"

    q_with_low = np.linspace(0.10, 1.20, 700)
    low_q_only = 0.02 + _gaussian(q_with_low, 0.20, 20.0)
    credible = 0.02 + _gaussian(q_with_low, 0.72, 12.0)
    rejected_fallback = analyze_strain_series(
        strains=[0.0, 5.0],
        q_list=[q_with_low, q_with_low],
        I_list=[low_q_only, credible],
        frame_source_indices=[0, 1],
        cfg=SAXSConfig(
            smooth_method="none",
            q_min=0.10,
            q_bragg_min=0.15,
            q_bragg_max=1.00,
        ),
    )
    assert rejected_fallback.strain_points[0].feature_tracking_status == (
        "unseeded"
    )
    assert np.isnan(rejected_fallback.strain_points[0].q_peak_total_nm1)
    assert rejected_fallback.strain_points[1].feature_tracking_status == "seeded"

    capped = analyze_strain_series(
        strains=[0.0, 5.0],
        q_list=[q, q],
        I_list=[seed, distant],
        frame_source_indices=[0, 1],
        cfg=SAXSConfig(
            smooth_method="none",
            q_min=0.20,
            q_bragg_min=0.30,
            q_bragg_max=1.00,
            strain_peak_max_relative_step=0.90,
        ),
    )
    assert capped.strain_points[1].feature_tracking_status == "tracking_lost"
    assert np.isnan(capped.strain_points[1].q_peak_total_nm1)


def test_real_edf8_keeps_one_feature_across_core_orientation_and_gui() -> None:
    source = Path.home() / "Desktop" / "edf" / "8"
    edf_files = sorted(source.glob("*.edf")) if source.exists() else []
    if len(edf_files) != 5:
        pytest.skip(f"external five-frame EDF 8 fixture unavailable: {source}")
    mtimes_before = {path: path.stat().st_mtime_ns for path in edf_files}

    engine = get_engine("saxs", submodule_id="saxs.strain")
    assert engine is not None
    assert engine.load(str(source)) is True
    assert engine.preprocess() is True
    assert engine.analyze() is True

    series = engine._strain_result  # type: ignore[attr-defined]
    rows = engine._batch_params  # type: ignore[attr-defined]
    assert series is not None
    assert [point.strain_pct for point in series.strain_points] == [
        0.0,
        5.0,
        60.0,
        200.0,
        400.0,
    ]
    assert len(rows) == len(series.strain_points) == 5
    for point, row in zip(series.strain_points, rows):
        fit = (point.orientation_evidence or {}).get("fit_evidence") or {}
        assert point.feature_tracking_status in {"seeded", "tracked"}
        assert fit["q_star_candidate"] == pytest.approx(point.q_peak_total_nm1)
        assert row["q_peak_total_nm1"] == pytest.approx(point.q_peak_total_nm1)
        assert row["L_nm"] == pytest.approx(round(point.L_nm, 2))
        assert np.isfinite(point.q_peak_meridional_nm1)
        assert np.isfinite(point.q_peak_equatorial_nm1)

    five_percent = series.strain_points[1]
    assert five_percent.q_peak_total_nm1 != pytest.approx(0.8155, abs=0.02)
    tracking_text = json.dumps(
        series.orientation_tracking_evidence,
        allow_nan=False,
        sort_keys=True,
    )
    assert "source_index_mapping_invalid" not in tracking_text
    assert "frame_source_index_missing" not in tracking_text
    assert {path: path.stat().st_mtime_ns for path in edf_files} == mtimes_before
