from __future__ import annotations

import json
from dataclasses import FrozenInstanceError

import pytest

from polynexus.core.saxs_engine.saxs_orientation_tracking import (
    OrientationFeatureObservation,
    OrientationFeatureTrack,
    track_orientation_features,
)


def _bin(q_bin_id: str, numerator: float, denominator: float = 10.0) -> dict:
    return {
        "q_bin_id": q_bin_id,
        "harmonic_numerator_real": numerator,
        "harmonic_numerator_imag": 0.0,
        "intensity_denominator": denominator,
        "f_reference": 0.25 + 0.75 * numerator / denominator,
        "stability_interval": {
            "f_reference_low": 0.30,
            "f_reference_high": 0.50,
        },
    }


def _frame(source_index: int, condition: float, *bands: dict) -> dict:
    candidates = []
    q_bins = []
    for band in bands:
        q_bins.extend(_bin(q_bin_id, numerator) for q_bin_id, numerator in band["bins"])
        candidates.append({
            "candidate_id": band["candidate_id"],
            "feature_kind": "q_band",
            "q_min_nm1": band["q_min_nm1"],
            "q_max_nm1": band["q_max_nm1"],
            "q_center_nm1": band["q_center_nm1"],
            "supported_q_bin_ids": tuple(q_bin_id for q_bin_id, _ in band["bins"]),
            "principal_axis_deg": band.get("principal_axis_deg", 0.0),
            "f_reference": band.get("f_reference", 0.4),
            "f_principal_raw": band.get("f_principal_raw", 0.4),
            "level": band.get("level", "Trend"),
        })
    return {
        "frame_source_index": source_index,
        "condition_value": condition,
        "q_resolved_orientation_evidence": {
            "convention": "detector_plane_2d_v1",
            "reference_axis_kind": "tensile_axis",
            "reference_axis_deg": 0.0,
            "reliability_policy_digest": "policy-sha256",
            "reliability_status": "usable",
            "q_band_candidates": candidates,
            "q_bins": q_bins,
        },
    }


def _band(candidate_id: str, low: float, high: float, prefix: str = "q") -> dict:
    return {
        "candidate_id": candidate_id,
        "q_min_nm1": low,
        "q_max_nm1": high,
        "q_center_nm1": (low + high) / 2.0,
        "bins": [(f"{prefix}-{index}", 2.0) for index in range(3)],
    }


def test_orientation_track_is_immutable_and_strict_json_safe() -> None:
    observation = OrientationFeatureObservation(
        frame_source_index=0,
        condition_value=0.0,
        candidate_id="frame-000-band-001",
        q_range_nm1=(0.20, 0.30),
        common_q_bin_ids=("q-0200-0233", "q-0233-0266", "q-0266-0300"),
        q_center_nm1=0.25,
        f_principal_raw=0.40,
        f_reference=None,
        delta_f_from_zero=None,
        delta_stability_interval={},
        reliability_status="diagnostic",
        reason_codes=("tensile_axis_unknown",),
    )
    track = OrientationFeatureTrack(
        track_id="orientation-track-001",
        feature_kind="q_band",
        convention="detector_plane_2d_v1",
        reference_axis_kind="unknown",
        reference_axis_deg=None,
        reliability_policy_digest="policy-sha256",
        observations=(observation,),
        reliability_status="diagnostic",
        reason_codes=("tensile_axis_unknown",),
    )

    json.dumps(track.to_dict(), allow_nan=False)
    with pytest.raises(FrozenInstanceError):
        track.track_id = "changed"  # type: ignore[misc]


def test_mutually_unique_overlapping_bands_keep_one_track() -> None:
    left = _band("a", 0.20, 0.35)
    right = _band("b", 0.22, 0.34)
    sequence = track_orientation_features([_frame(0, 0.0, left), _frame(1, 5.0, right)])

    assert len(sequence.tracks) == 1
    assert tuple(item.candidate_id for item in sequence.tracks[0].observations) == ("a", "b")


def test_ambiguous_fork_splits_instead_of_selecting_lowest_cost() -> None:
    source = _band("a", 0.20, 0.35, prefix="shared")
    first = _band("b", 0.20, 0.28, prefix="shared")
    second = _band("c", 0.25, 0.35, prefix="shared")
    sequence = track_orientation_features([_frame(0, 0.0, source), _frame(1, 5.0, first, second)])

    assert sequence.ambiguous_match_count == 1
    assert "feature_match_ambiguous" in sequence.reason_codes
    assert all(
        tuple(item.candidate_id for item in track.observations) != ("a", "b")
        for track in sequence.tracks
    )


def test_unique_zero_delta_uses_common_additive_q_bins() -> None:
    zero = _band("zero", 0.20, 0.35, prefix="common")
    five = _band("five", 0.20, 0.35, prefix="common")
    zero["bins"] = [(f"common-{index}", 2.0) for index in range(3)]
    five["bins"] = [(f"common-{index}", 4.0) for index in range(3)]
    sequence = track_orientation_features([_frame(0, 0.0, zero), _frame(1, 5.0, five)])

    observation = sequence.tracks[0].observations[-1]
    assert observation.delta_f_from_zero == pytest.approx(0.15)
    assert observation.common_q_bin_ids == ("common-0", "common-1", "common-2")


@pytest.mark.parametrize(
    "conditions, reason",
    [((5.0, 60.0), "zero_reference_missing"), ((0.0, 0.0, 5.0), "zero_reference_ambiguous")],
)
def test_delta_is_unavailable_without_a_unique_zero_reference(conditions, reason) -> None:
    frames = [_frame(index, condition, _band(str(index), 0.20, 0.35, prefix=str(index))) for index, condition in enumerate(conditions)]
    sequence = track_orientation_features(frames)

    assert sequence.zero_reference_source_index is None
    assert reason in sequence.reason_codes
    assert all(
        item.delta_f_from_zero is None
        for track in sequence.tracks
        for item in track.observations
    )


def test_one_source_gap_is_reported_and_not_silently_fabricated() -> None:
    frames = [
        _frame(0, 0.0, _band("a", 0.20, 0.35, prefix="a")),
        _frame(2, 5.0, _band("b", 0.20, 0.35, prefix="b")),
    ]
    sequence = track_orientation_features(frames)

    assert sequence.missing_frame_indices == (1,)
    assert "missing_frame_gap" in sequence.reason_codes
