from __future__ import annotations

from polynexus.core.preprocess_optimization.peak_metrics import compare_peak_sets
from polynexus.core.preprocess_optimization.snapshot import AnalysisSnapshot


def test_peak_matching_is_one_to_one_and_order_independent() -> None:
    control = [
        {"center": 10.0, "fwhm": 1.0, "area": 100.0, "height": 10.0},
        {"center": 20.0, "fwhm": 2.0, "area": 25.0, "height": 2.0},
    ]
    candidate = [
        {"center": 20.05, "fwhm": 2.1, "area": 24.0, "height": 1.9},
        {"center": 10.02, "fwhm": 1.0, "area": 99.0, "height": 10.1},
    ]

    metrics = compare_peak_sets(control, candidate, center_tolerance=0.20)

    assert metrics.matched_count == 2
    assert metrics.max_peak_shift == 0.05
    assert metrics.max_fwhm_change == 0.05
    assert metrics.weak_peak_retention == 1.0
    assert metrics.coverage == 1.0


def test_missing_weak_peak_is_visible_even_when_strong_peak_survives() -> None:
    control = [
        {"center": 10.0, "area": 100.0, "height": 10.0},
        {"center": 20.0, "area": 5.0, "height": 0.5},
    ]
    candidate = [{"center": 10.0, "area": 100.0, "height": 10.0}]

    metrics = compare_peak_sets(control, candidate, center_tolerance=0.20)

    assert metrics.matched_count == 1
    assert metrics.weak_peak_retention == 0.0
    assert metrics.integrated_area_change > 0.0
    assert metrics.coverage == 0.5


def test_matching_uses_nearest_candidate_without_reuse() -> None:
    control = [{"center": 10.0, "area": 2.0}, {"center": 10.3, "area": 1.0}]
    candidate = [{"center": 10.1, "area": 2.0}, {"center": 10.35, "area": 1.0}]

    metrics = compare_peak_sets(control, candidate, center_tolerance=0.25)

    assert metrics.matched_count == 2
    assert metrics.max_peak_shift == 0.1


def test_empty_control_is_incomplete_not_perfect() -> None:
    metrics = compare_peak_sets([], [{"center": 1.0, "area": 1.0}], center_tolerance=0.1)

    assert metrics.coverage == 0.0
    assert metrics.matched_count == 0
    assert metrics.max_peak_shift is None
    assert metrics.integrated_area_change is None


def test_snapshot_copies_inputs_and_derives_stable_config_hash() -> None:
    config = {"smooth_window": 7}
    output = {"peaks": [{"center": 1.0}]}

    snapshot = AnalysisSnapshot.from_parts(
        config=config,
        output_parameters=output,
        residual_pattern={"rmse": 0.2},
        analysis_evidence={"summary": "ok"},
    )
    config["smooth_window"] = 99
    output["peaks"][0]["center"] = 9.0

    assert snapshot.config == {"smooth_window": 7}
    assert snapshot.output_parameters["peaks"][0]["center"] == 1.0
    assert len(snapshot.config_hash) == 64
