from __future__ import annotations

from tests.eval.preprocess.synthetic_signals import run_synthetic_case


def test_saxs_segment_boundary_is_not_smoothed_across() -> None:
    result = run_synthetic_case(
        {
            "case_id": "saxs-mask-boundary",
            "technique": "SAXS",
            "scenario": "noise",
            "input_mode": "processed",
            "seed": 23,
            "intent": {"target": "smoothing", "desired_effect": "medium"},
            "expected": {"min_weak_peak_retention": 0.70},
        }
    )

    assert result["cross_boundary_smoothing"] is False


def test_nmr_fid_candidate_keeps_zero_fill_fixed() -> None:
    result = run_synthetic_case(
        {
            "case_id": "nmr-fid-noise",
            "technique": "NMR",
            "scenario": "noise",
            "input_mode": "fid",
            "seed": 29,
            "intent": {"target": "smoothing", "desired_effect": "medium"},
            "expected": {"min_weak_peak_retention": 0.75},
        }
    )

    assert result["zero_fill_unchanged"] is True
