from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pytest

from polynexus.core.saxs_batch_helpers import copy_saxs_quality_evidence
from polynexus.core.saxs import SAXSEngine
from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.saxs_strain import (
    StrainSeriesResult,
    analyze_strain_series,
)


def _tracking_payload() -> dict:
    return {
        "tracks": [
            {
                "track_id": "orientation-track-a",
                "feature_kind": "q_band",
                "observations": [],
            },
            {
                "track_id": "orientation-track-b",
                "feature_kind": "q_band",
                "observations": [],
            },
        ],
        "level": "Diagnostic",
        "reason_codes": ["feature_match_ambiguous"],
    }


def test_strain_result_reserves_detached_orientation_tracking_evidence() -> None:
    result = StrainSeriesResult()

    assert hasattr(result, "orientation_tracking_evidence")
    payload = result.orientation_tracking_evidence
    json.dumps(payload, allow_nan=False)


def test_tracking_transport_does_not_replace_legacy_scalar_fields() -> None:
    result = StrainSeriesResult()
    result.f_herman_array = np.asarray([0.2, 0.1])
    result.orientation_tracking_evidence = {
        "tracks": [],
        "level": "Diagnostic",
        "reason_codes": ["zero_reference_missing"],
    }

    assert result.f_herman_array.tolist() == [0.2, 0.1]
    assert result.orientation_tracking_evidence["tracks"] == []


def test_batch_quality_copy_keeps_detached_tracking_payload() -> None:
    result = StrainSeriesResult(
        orientation_tracking_evidence=_tracking_payload()
    )

    copied = copy_saxs_quality_evidence(result)

    assert copied["orientation_tracking_evidence"]["tracks"][0]["track_id"] == (
        "orientation-track-a"
    )
    assert copied["orientation_tracking_evidence"] is not result.orientation_tracking_evidence


def test_strain_parameters_transport_whole_tracking_payload_without_primary_track() -> None:
    engine = SAXSEngine(SAXSConfig())
    payload = _tracking_payload()
    series = StrainSeriesResult(
        strains=np.asarray([0.0, 5.0]),
        L_array=np.asarray([10.0, 10.1]),
        Q_star_array=np.asarray([1.0, 1.1]),
        Q_star_rel_array=np.asarray([1.0, 1.1]),
        phi_void_array=np.asarray([0.0, 0.0]),
        f_herman_array=np.asarray([0.30, 0.35]),
        strain_points=[
            SimpleNamespace(f_herman=0.30, f_herman_raw=0.31),
            SimpleNamespace(f_herman=0.35, f_herman_raw=0.36),
        ],
        orientation_tracking_evidence=payload,
    )
    engine._strain_result = series
    engine._batch_params = [{"strain_pct": 0.0}, {"strain_pct": 5.0}]

    params = engine.get_parameters()

    transported = params["orientation_tracking_evidence"]
    assert transported == payload
    assert transported is not payload
    assert "track_id" not in transported
    assert [track["track_id"] for track in transported["tracks"]] == [
        "orientation-track-a",
        "orientation-track-b",
    ]
    assert params["f_Herman_mean"] == pytest.approx(0.325)
    assert params["f_Herman_raw_mean"] == pytest.approx(0.335)
    json.dumps(transported, allow_nan=False)


def _q_tracking_evidence() -> dict:
    return {
        "convention": "detector_plane_2d_v1",
        "reference_axis_kind": "tensile_axis",
        "reference_axis_deg": 0.0,
        "reliability_policy_digest": "policy-sha256",
        "reliability_status": "usable",
        "q_band_candidates": [],
        "q_bins": [],
    }


def _patch_strain_tracking_inputs(monkeypatch) -> None:
    import polynexus.core.saxs_engine.saxs_strain as module

    monkeypatch.setattr(
        module,
        "analyze_single",
        lambda q, intensity, cfg: SimpleNamespace(
            long_period=SimpleNamespace(L_best=10.0, L_confidence=0.8, method_used="bragg"),
            structure=SimpleNamespace(lc=3.0, la=7.0, phi_c=0.3),
            data_quality_report={},
            metric_evidence={},
            detector_quality_report=None,
            orientation_evidence=None,
        ),
    )
    monkeypatch.setattr(module, "scattering_invariant", lambda q, intensity, *, cfg: 2.0)
    monkeypatch.setattr(
        module,
        "detect_strain_phase",
        lambda strain, q_star, q_ref, q, intensity, cfg: module.StrainPhase.ELASTIC,
    )
    monkeypatch.setattr(
        module,
        "detect_voids",
        lambda q, intensity, cfg: {
            "has_voids": False,
            "phi_void": np.nan,
            "void_ar": np.nan,
        },
    )
    monkeypatch.setattr(
        module,
        "herman_from_sector_data",
        lambda sector_data, **kwargs: {
            "f": 0.4,
            "f_raw": 0.4,
            "f_sub": np.nan,
            "f_eq": np.nan,
            "detector_quality_report": None,
            "raw_detector_quality_report": None,
            "orientation_evidence": None,
            "q_resolved_orientation_evidence": _q_tracking_evidence(),
        },
    )


@pytest.mark.parametrize("source_indices", ([0, "bad"], [0, 0]))
def test_strain_tracking_rejects_invalid_source_mapping_without_position_inference(
    monkeypatch, source_indices
) -> None:
    _patch_strain_tracking_inputs(monkeypatch)
    q = np.asarray([0.02, 0.03, 0.04])
    intensity = np.asarray([2.0, 3.0, 4.0])

    result = analyze_strain_series(
        [0.0, 5.0],
        [q, q],
        [intensity, intensity],
        sector_data_list=[
            {"frame_source_index": 10},
            {"frame_source_index": 11},
        ],
        frame_source_indices=source_indices,
        cfg=SAXSConfig(),
    )

    tracking = result.orientation_tracking_evidence
    assert tracking["level"] == "Unusable"
    assert "source_index_mapping_invalid" in tracking["reason_codes"]
    assert tracking["tracks"] == []


def test_strain_tracking_missing_source_index_does_not_infer_list_position(monkeypatch) -> None:
    _patch_strain_tracking_inputs(monkeypatch)
    q = np.asarray([0.02, 0.03, 0.04])
    intensity = np.asarray([2.0, 3.0, 4.0])

    result = analyze_strain_series(
        [0.0, 5.0],
        [q, q],
        [intensity, intensity],
        sector_data_list=[{}, {}],
        cfg=SAXSConfig(),
    )

    tracking = result.orientation_tracking_evidence
    assert tracking["level"] == "Unusable"
    assert "source_index_mapping_invalid" in tracking["reason_codes"]
    assert tracking["tracks"] == []
