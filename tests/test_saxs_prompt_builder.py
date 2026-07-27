from __future__ import annotations

from rag.prompt_builder import PromptBuilder
from polynexus.core.preprocess_optimization import get_preprocess_policy


def test_saxs_prompt_marks_savgol_window_as_high_priority() -> None:
    prompt = PromptBuilder().build_prompt(
        {
            "technique": "SAXS",
            "polymer_name": "PA6",
            "params": {"r_squared": 0.817, "Xc_pct": 10.9},
            "current_config": {"savgol_window": 7, "savgol_order": 2},
            "r_squared": 0.817,
            "residuals_pattern": "SAXS peak-region residual mismatch.",
            "residual_pattern": {
                "max_residual_region": "q=0.898 nm^-1",
                "residual_type": "peak_mismatch",
            },
        },
        [],
    )

    assert "savgol_window" in prompt
    assert "High-priority SAXS smoothing parameter" in prompt
    assert "directly affects Bragg peak-region r_squared" in prompt


def test_saxs_preprocess_prompt_lists_every_required_protected_feature() -> None:
    prompt = PromptBuilder().build(
        {
            "technique": "SAXS",
            "polymer_name": "PA6",
            "params": {"L_nm": 12.0},
            "current_config": {"savgol_window": 7, "savgol_order": 2},
            "analysis_evidence": {
                "symptoms": [
                    {"name": "noise_dominant", "severity": "warning"},
                ],
            },
            "allowed_actions": [{"name": "reduce_profile_noise"}],
        },
        [],
        [],
    )
    policy = get_preprocess_policy("SAXS")

    for feature in policy.allowed_protected_features:
        assert feature in prompt
    assert "For SAXS, include every listed protected feature" in prompt
