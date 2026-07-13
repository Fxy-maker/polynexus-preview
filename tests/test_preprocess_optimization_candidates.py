from __future__ import annotations

from dataclasses import replace

from polynexus.core.preprocess_optimization import PreprocessIntent, get_preprocess_policy
from polynexus.core.preprocess_optimization.candidates import (
    generate_preprocess_candidates,
    stable_config_hash,
)


class StubAdapter:
    name = "stub"
    version = "1"

    def baseline_deltas(self, intent, base_config):
        return [
            {"baseline_type": "linear"},
            {"baseline_type": "spline"},
            {"baseline_type": "linear"},
        ]

    def smoothing_deltas(self, intent, base_config):
        return [
            {"smooth_window": 9},
            {"smooth_window": 13},
            {"smooth_window": 10},
            {"unknown": 1},
        ]


def _intent(target: str = "both") -> PreprocessIntent:
    return PreprocessIntent(
        schema_version="1.0",
        analysis_id="case-1",
        technique="DSC",
        target=target,
        direction="strengthen",
        desired_effect="medium",
        protected_features=("integrated_area", "weak_peaks"),
        target_symptoms=("noise_dominant",),
        rationale_code="noise",
        human_summary="Reduce noise without losing events.",
    )


def test_generation_is_stable_bounded_and_control_first() -> None:
    policy = get_preprocess_policy("DSC")
    base = {"baseline_corr": "auto", "smooth_window": 11, "smooth_order": 3}

    left = generate_preprocess_candidates(_intent(), base, policy, StubAdapter())
    right = generate_preprocess_candidates(_intent(), base, policy, StubAdapter())

    assert left == right
    assert left[0].config_delta == {}
    assert left[0].generation_reason == "control"
    assert len(left) <= policy.max_candidates
    assert len({item.candidate_id for item in left}) == len(left)
    assert base == {"baseline_corr": "auto", "smooth_window": 11, "smooth_order": 3}


def test_both_target_stages_baseline_before_smoothing_without_cartesian_product() -> None:
    candidates = generate_preprocess_candidates(
        _intent("both"),
        {"baseline_corr": "auto", "smooth_window": 11, "smooth_order": 3},
        get_preprocess_policy("DSC"),
        StubAdapter(),
    )

    assert [item.generation_reason for item in candidates] == [
        "control",
        "baseline",
        "baseline",
        "smoothing",
        "smoothing",
    ]
    assert all(len(item.config_delta) <= 1 for item in candidates)


def test_target_filters_the_other_lane() -> None:
    base = {"baseline_corr": "auto", "smooth_window": 11, "smooth_order": 3}

    baseline = generate_preprocess_candidates(
        _intent("baseline"), base, get_preprocess_policy("DSC"), StubAdapter()
    )
    smoothing = generate_preprocess_candidates(
        _intent("smoothing"), base, get_preprocess_policy("DSC"), StubAdapter()
    )

    assert {item.generation_reason for item in baseline} == {"control", "baseline"}
    assert {item.generation_reason for item in smoothing} == {"control", "smoothing"}


def test_scoped_experience_is_ranked_before_generated_candidates() -> None:
    candidates = generate_preprocess_candidates(
        _intent("both"),
        {"baseline_corr": "auto", "smooth_window": 11, "smooth_order": 3},
        get_preprocess_policy("DSC"),
        StubAdapter(),
        experience_deltas=({"smooth_window": 7},),
    )

    assert candidates[1].generation_reason == "experience"
    assert candidates[1].config_delta == {"smooth_window": 7}


def test_candidate_limit_includes_control_and_is_deterministic() -> None:
    policy = replace(get_preprocess_policy("DSC"), max_candidates=3)

    candidates = generate_preprocess_candidates(
        _intent(),
        {"baseline_corr": "auto", "smooth_window": 11, "smooth_order": 3},
        policy,
        StubAdapter(),
    )

    assert len(candidates) == 3
    assert [item.generation_reason for item in candidates] == ["control", "baseline", "baseline"]


def test_stable_config_hash_ignores_mapping_order() -> None:
    assert stable_config_hash({"a": 1, "b": [2, 3]}) == stable_config_hash(
        {"b": [2, 3], "a": 1}
    )
