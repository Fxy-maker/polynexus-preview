from __future__ import annotations

from rag.prompt_builder import PromptBuilder
from polynexus.core.preprocess_optimization import get_preprocess_policy


def test_saxs_prompt_renders_summary_only_context_boundary() -> None:
    prompt = PromptBuilder().build_prompt(
        {
            "technique": "SAXS",
            "params": {"Rg_nm": 4.2},
            "current_config": {},
            "saxs_ai_context": {
                "technique": "SAXS",
                "mode": "temperature",
                "status": "available",
                "quality_gate_status": "passed",
                "physical_gate_status": "passed",
                "candidate_only": True,
                "raw_profile_included": False,
                "raw_detector_data_included": False,
                "frames": [],
            },
        },
        [],
    )

    assert "SAXS AI summary context" in prompt
    assert "raw_profile_included" in prompt
    assert "candidate_only" in prompt
    assert "return only the existing SAXS preprocess intent" in prompt


def test_saxs_prompt_drops_untrusted_raw_fields_from_context() -> None:
    prompt = PromptBuilder().build_prompt(
        {
            "technique": "SAXS",
            "params": {},
            "current_config": {},
            "saxs_ai_context": {
                "technique": "SAXS",
                "mode": "static",
                "candidate_only": True,
                "raw_profile_included": False,
                "raw_detector_data_included": False,
                "frames": [{"source_index": 0, "raw_q": [0.01], "raw_I": [1.0]}],
                "q_values": [0.01],
                "intensity_values": [1.0],
                "detector_pixels": [[1]],
            },
        },
        [],
    )

    assert "raw_q" not in prompt
    assert "raw_I" not in prompt
    assert "q_values" not in prompt
    assert "intensity_values" not in prompt
    assert "detector_pixels" not in prompt


def test_saxs_prompt_contracts_existing_candidate_references_as_diagnostic_only() -> None:
    prompt = PromptBuilder().build_prompt(
        {
            "technique": "SAXS",
            "params": {},
            "saxs_ai_context": {
                "technique": "SAXS",
                "mode": "temperature",
                "status": "available",
                "candidate_only": True,
                "physical_validation_required": True,
                "series": {
                    "sequence_rescue_candidates": [
                        {"candidate_id": "temperature-frame-0-lc-tangent"}
                    ]
                },
            },
        },
        [],
        [],
    )

    assert "saxs_candidate_references" in prompt
    assert "exact IDs" in prompt or "exact candidate IDs" in prompt
    assert "diagnostic-only" in prompt
    assert "never execute" in prompt or "cannot execute" in prompt
    assert "rerun" in prompt
    assert "configuration" in prompt


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
