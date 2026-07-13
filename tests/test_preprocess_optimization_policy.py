from __future__ import annotations

from dataclasses import replace

import pytest

from polynexus.core.preprocess_optimization import PreprocessIntent, get_preprocess_policy
from polynexus.core.preprocess_optimization.policy import (
    ParameterRule,
    PolicyValidationError,
    PreprocessPolicy,
)


def _intent(technique: str = "DSC") -> PreprocessIntent:
    return PreprocessIntent(
        schema_version="1.0",
        analysis_id="case-1",
        technique=technique,
        target="both",
        direction="strengthen",
        desired_effect="medium",
        protected_features=("weak_peaks", "integrated_area"),
        target_symptoms=("noise_dominant",),
        rationale_code="noise",
        human_summary="Reduce noise without losing signal.",
    )


def test_default_profiles_are_shadow_and_uncalibrated() -> None:
    for technique in ("DSC", "IR", "WAXS", "SAXS", "NMR"):
        policy = get_preprocess_policy(technique)

        assert policy.automation_state == "shadow"
        assert policy.calibrated is False
        assert policy.max_candidates >= 2
        assert "evidence_coverage_min" in policy.hard_limits
        assert policy.technique == technique


def test_policy_lookup_is_case_insensitive_but_rejects_unknown_techniques() -> None:
    assert get_preprocess_policy("dsc").technique == "DSC"
    with pytest.raises(PolicyValidationError, match="Unknown preprocessing technique"):
        get_preprocess_policy("joint")


def test_uncalibrated_policy_cannot_enable_tiered_auto() -> None:
    policy = get_preprocess_policy("DSC")

    with pytest.raises(PolicyValidationError, match="calibrated"):
        policy.with_automation_state("tiered_auto")


def test_calibrated_policy_can_enable_tiered_auto() -> None:
    policy = replace(get_preprocess_policy("DSC"), calibrated=True)

    enabled = policy.with_automation_state("tiered_auto")

    assert enabled.automation_state == "tiered_auto"
    assert enabled.calibrated is True


def test_policy_rejects_parameter_not_in_local_map() -> None:
    policy = get_preprocess_policy("DSC")

    with pytest.raises(PolicyValidationError, match="unknown parameter"):
        policy.validate_delta({"temperature_calibration": {"a": 99}})


@pytest.mark.parametrize("value", [True, False])
def test_numeric_parameter_rule_rejects_bool(value: bool) -> None:
    rule = ParameterRule("smooth_window", int, minimum=3, maximum=31)

    with pytest.raises(PolicyValidationError, match="bool"):
        rule.validate(value)


def test_policy_validates_intent_technique_and_protected_features() -> None:
    policy = get_preprocess_policy("DSC")
    policy.validate_intent(_intent("DSC"))

    with pytest.raises(PolicyValidationError, match="technique"):
        policy.validate_intent(_intent("IR"))

    unknown_feature = replace(_intent("DSC"), protected_features=("invented_feature",))
    with pytest.raises(PolicyValidationError, match="protected feature"):
        policy.validate_intent(unknown_feature)


def test_policy_rejects_invalid_threshold_order() -> None:
    base = get_preprocess_policy("DSC")

    with pytest.raises(PolicyValidationError, match="threshold"):
        PreprocessPolicy(
            **{
                **base.to_dict(),
                "medium_threshold": 0.9,
                "high_threshold": 0.8,
            }
        )
