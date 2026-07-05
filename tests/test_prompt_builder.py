from __future__ import annotations

from polynexus.core.analysis_evidence import build_analysis_evidence
from polynexus.orchestrator import RoundRecord
from rag.polymer_knowledge import load_polymer_knowledge
from rag.prompt_builder import PromptBuilder


def _round_record(
    round_num: int,
    before: float,
    after: float,
    changes: dict[str, object],
    accepted: bool,
) -> RoundRecord:
    return RoundRecord(
        round_num=round_num,
        config_snapshot={},
        output_parameters={"r_squared": after},
        residuals_pattern={},
        analysis_evidence={},
        polymer_knowledge={},
        r_squared=after,
        eval_score=after,
        llm_advice={"changes": changes},
        round_idx=round_num,
        r_squared_before=before,
        r_squared_after=after,
        changes=changes,
        accepted=accepted,
    )


def test_format_history_marks_accepted_and_rolled_back_rounds() -> None:
    builder = PromptBuilder()
    rolled_back = _round_record(2, 0.9366, 0.9290, {"peak_function": "pseudo_voigt"}, False)
    rolled_back.target_symptom = "peak_window_mismatch"
    rolled_back.symptom_summary = "peak_window_mismatch: Bragg peak window looks unstable."
    rolled_back.rollback_detail = "Target symptom peak_window_mismatch did not improve enough to keep the change."
    history = builder.format_history(
        [
            _round_record(1, 0.9296, 0.9366, {"peak_function": "gaussian"}, True),
            rolled_back,
        ]
    )

    assert "✅ 有效（已保留）" in history
    assert "❌ 无效（已回滚）" in history
    assert "0.9296 → 0.9366" in history
    assert "pseudo_voigt" in history
    assert "target_symptom: peak_window_mismatch" in history
    assert "rollback: Target symptom peak_window_mismatch did not improve enough to keep the change." in history


def test_build_prompt_with_history_contains_rules_and_priority() -> None:
    builder = PromptBuilder()
    prompt = builder.build_prompt(
        {
            "technique": "WAXS",
            "polymer_name": "PA6",
            "params": {"Xc_pct": 69.6},
            "current_config": {"peak_function": "gaussian"},
            "r_squared": 0.9366,
            "residuals_pattern": "在 2θ=19.3° 附近存在系统性正残差。",
            "residual_pattern": {
                "max_residual_region": "2θ=19.3°",
                "residual_type": "systematic_peak",
            },
            "polymer_knowledge": load_polymer_knowledge("PA6"),
        },
        [],
        history=[
            _round_record(1, 0.9296, 0.9366, {"peak_function": "gaussian"}, True),
            _round_record(2, 0.9366, 0.9290, {"peak_function": "pseudo_voigt"}, False),
        ],
    )

    assert "禁止重复建议" in prompt
    assert "调参优先级" in prompt
    assert "历史轮次" in prompt
    assert "❌ 无效（已回滚）" in prompt
    assert "标准 Xc 范围：35-55%" in prompt


def test_format_history_empty_rounds_returns_first_round_hint() -> None:
    assert PromptBuilder().format_history([]) == "（本轮为第一轮，无历史记录）"


def test_build_prompt_surfaces_symptom_bridge_from_evidence() -> None:
    builder = PromptBuilder()
    prompt = builder.build_prompt(
        {
            "technique": "WAXS",
            "polymer_name": "PA6",
            "params": {"r_squared": 0.92, "Xc_pct": 45.0},
            "current_config": {"peak_function": "gaussian"},
            "r_squared": 0.92,
            "residual_pattern": {
                "max_residual_region": "2θ=19.3°",
                "residual_type": "peak_mismatch",
            },
            "analysis_evidence": {
                "actionable_symptoms": [
                    "peak_mismatch -> peak_function / peak_distance / two_theta_offset",
                    "expected evidence change: residual_type should move toward random",
                ],
            },
            "polymer_knowledge": load_polymer_knowledge("PA6"),
        },
        [],
    )

    assert "## Symptom bridge" in prompt
    assert "peak_function" in prompt
    assert "## Response contract" in prompt


def test_build_prompt_surfaces_waxs_background_and_phase_evidence() -> None:
    builder = PromptBuilder()
    prompt = builder.build_prompt(
        {
            "technique": "WAXS",
            "polymer_name": "PA6",
            "params": {"Xc_pct": 69.6},
            "current_config": {"two_theta_offset": 0.08},
            "r_squared": 0.93,
            "residual_pattern": {"residual_type": "random"},
            "analysis_evidence": {
                "background_evidence": {
                    "background_method": "polynomial",
                    "amorphous_subtraction": "polynomial",
                    "amorphous_n_peaks": 2,
                    "two_theta_offset": 0.08,
                },
                "phase_evidence": {
                    "crystallinity_method": "peak_deconvolution",
                    "crystal_system": "unknown",
                    "unit_cell_params_present": True,
                    "D_Scherrer_nm": 8.3,
                },
            },
            "polymer_knowledge": load_polymer_knowledge("PA6"),
        },
        [],
    )

    assert "background_evidence" in prompt
    assert "phase_evidence" in prompt
    assert "two_theta_offset" in prompt
    assert "D_Scherrer_nm" in prompt


def test_build_ir_prompt_surfaces_reference_bands_and_assignment_status() -> None:
    builder = PromptBuilder()
    prompt = builder.build_prompt(
        {
            "technique": "IR",
            "polymer_name": "PA6",
            "params": {
                "n_peaks": 5,
                "polymer_score": 0.74,
                "assignment_confidence": 0.68,
                "Xc_pct": 0.41,
            },
            "current_config": {"baseline_method": "rubberband", "smooth_window": 7},
            "r_squared": 0.89,
            "residual_pattern": {"residual_type": "peak_mismatch", "summary": "band mismatch remains"},
            "analysis_evidence": {
                "feature_evidence": {
                    "reference_evidence": {
                        "band_count": 3,
                        "hit_count": 2,
                        "missing_count": 1,
                        "bands": [
                            {"wavenumber": 3298, "assignment": "N-H stretch", "crystallinity_sensitive": False},
                            {"wavenumber": 1637, "assignment": "amide I", "crystallinity_sensitive": False},
                        ],
                    },
                    "assignment_evidence": {
                        "assignment_confidence": 0.68,
                        "key_band_hit_count": 2,
                        "key_band_missing_count": 1,
                    },
                    "structure_evidence": {"paper_conclusion_ready": False},
                },
            },
            "ir_reference_bands": {
                "polymer_name": "PA6",
                "band_count": 3,
                "source": "IRConfig.polymer_peaks_db",
                "bands": [
                    {"wavenumber": 3298, "assignment": "N-H stretch", "crystallinity_sensitive": False},
                    {"wavenumber": 1637, "assignment": "amide I", "crystallinity_sensitive": False},
                    {"wavenumber": 1541, "assignment": "amide II", "crystallinity_sensitive": False},
                ],
            },
            "polymer_knowledge": load_polymer_knowledge("PA6"),
        },
        [],
    )

    assert "IR 参考带" in prompt
    assert "参考带总数：3" in prompt
    assert "命中情况：" in prompt
    assert "confidence=0.68" in prompt
    assert "论文候选：否" in prompt
    assert "IR 强特征带" in prompt


def test_ir_prompt_strategy_handles_specialized_residual_types() -> None:
    builder = PromptBuilder()
    prompt = builder.build_prompt(
        {
            "technique": "IR",
            "polymer_name": "PA6",
            "params": {"n_peaks": 8, "polymer_score": 0.74},
            "current_config": {"baseline_method": "rubberband", "smooth_window": 7},
            "r_squared": 0.89,
            "residual_pattern": {
                "residual_type": "crowded_band_underfit",
                "summary": "Crowded amide bands remain underfit.",
            },
            "polymer_knowledge": load_polymer_knowledge("PA6"),
        },
        [],
    )

    assert "crowded_band_underfit" in prompt
    assert "peak_distance" in prompt
    assert "lineshape" in prompt


def test_build_ir_temperature_2d_prompt_surfaces_sequence_and_cos_language() -> None:
    builder = PromptBuilder()
    prompt = builder.build_prompt(
        {
            "technique": "IR",
            "submodule": "ir.temperature_2d",
            "polymer_name": "PA6",
            "params": {
                "n_frames": 48,
                "T_range_C": "30-250",
                "sync_cross_peak_count": 12,
                "async_cross_peak_count": 12,
                "neg_fraction": 0.339,
                "transition_count": 1,
            },
            "current_config": {"baseline_method": "mute_zone", "smooth_window": 7},
            "r_squared": 0.81,
            "residual_pattern": {
                "residual_type": "random",
                "summary": "temperature sequence is usable but matrix quality still needs review",
            },
            "analysis_evidence": {
                "feature_evidence": {
                    "temperature_2d_evidence": {
                        "sequence_axis_score": 0.89,
                        "matrix_quality_score": 0.68,
                        "cos_signal_score": 0.75,
                        "interpretation_ready": True,
                        "paper_conclusion_ready": False,
                    }
                }
            },
            "polymer_knowledge": load_polymer_knowledge("PA6"),
        },
        [],
    )

    assert "2D-COS" in prompt
    assert "序列" in prompt or "sequence axis" in prompt
    assert "同步交叉峰" in prompt or "sync" in prompt
    assert "负值比例" in prompt
    assert "matrix_quality_score" in prompt or "matrix quality" in prompt
    assert "band tracking" in prompt.lower() or "带指数支撑数" in prompt


def test_build_ir_temperature_2d_prompt_surfaces_real_band_tracking_language() -> None:
    from pathlib import Path
    from polynexus.core.analysis_evidence import build_analysis_evidence
    from polynexus.core.ir_engine import IRConfig, analyze_temperature_2d_series, load_project, preprocess_pipeline

    builder = PromptBuilder()
    cfg = IRConfig(
        peak_height_min=0.03,
        peak_prominence_min=0.02,
        peak_distance=18.0,
        polymer_name="PA6",
    )
    spectra = load_project(
        str(Path(__file__).resolve().parents[1] / "娴嬭瘯鏁版嵁" / "IR" / "鍘熶綅鍙樻俯绾㈠"),
        cfg.wavenumber_range,
    )
    processed = [preprocess_pipeline(s, cfg) for s in spectra]
    result = analyze_temperature_2d_series(processed, cfg)
    evidence = build_analysis_evidence(
        "IR",
        output_parameters=result.parameters,
        residual_pattern={"residual_type": "random", "summary": "2D sequence is stable enough for review"},
        validation_context={"config_snapshot": cfg.to_dict(), "submodule_id": "ir.temperature_2d"},
    ).to_dict()

    prompt = builder.build_prompt(
        {
            "technique": "IR",
            "submodule": "ir.temperature_2d",
            "polymer_name": "PA6",
            "params": result.parameters,
            "current_config": cfg.to_dict(),
            "r_squared": 0.81,
            "residual_pattern": {"residual_type": "random", "summary": "real sequence review"},
            "analysis_evidence": evidence,
            "polymer_knowledge": {},
        },
        [],
    )

    assert "band tracking" in prompt.lower() or "带指数支撑数" in prompt
    assert "sequence axis" in prompt.lower() or "序列轴" in prompt
    assert "2D-COS" in prompt


def test_build_dsc_prompt_surfaces_residual_bridge_and_search_windows() -> None:
    builder = PromptBuilder()
    evidence = build_analysis_evidence(
        "DSC",
        output_parameters={
            "quality_score": 0.62,
            "Tm_peak_C": 224.0,
            "Tcc_peak_C": 176.0,
            "Xc_pct": 12.1,
        },
        residual_pattern={
            "residual_type": "peak_shift",
            "summary": "Tm peak shifted high",
            "max_residual_region": "T=224C",
        },
    ).to_dict()

    prompt = builder.build_prompt(
        {
            "technique": "DSC",
            "polymer_name": "PA6",
            "params": {
                "Tm_peak_C": 224.0,
                "Tcc_peak_C": 176.0,
                "Xc_pct": 12.1,
            },
            "current_config": {
                "baseline_type": "auto",
                "Tm_search_low_C": 100.0,
                "Tm_search_high_C": 260.0,
                "Tc_search_low_C": 100.0,
                "Tc_search_high_C": 240.0,
                "peak_function": "gaussian",
                "smooth_window": 11,
            },
            "r_squared": 0.62,
            "residual_pattern": {
                "residual_type": "peak_shift",
                "summary": "Tm peak shifted high",
                "max_residual_region": "T=224C",
            },
            "analysis_evidence": evidence,
            "polymer_knowledge": {},
        },
        [],
    )

    assert "## Symptom bridge" in prompt
    assert "peak_shift" in prompt
    assert "Tm_search_low_C" in prompt
    assert "Tm_search_high_C" in prompt
    assert "peak_function" in prompt
    assert "baseline_type" in prompt
    assert "expected evidence change" in prompt


def test_build_prompt_surfaces_structured_symptoms_when_present() -> None:
    builder = PromptBuilder()
    prompt = builder.build_prompt(
        {
            "technique": "SAXS",
            "polymer_name": "PA6",
            "params": {"L_nm": 12.0},
            "current_config": {"q_bragg_min": 0.05},
            "r_squared": 0.91,
            "residual_pattern": {"residual_type": "noise"},
            "analysis_evidence": {
                "symptoms": [
                    {
                        "name": "beamstop_or_low_q_contamination",
                        "severity": "error",
                        "summary": "Low-q evidence is contaminated or truncated.",
                        "target_params": ["q_bragg_min", "q_corr_min"],
                    }
                ],
            },
            "polymer_knowledge": load_polymer_knowledge("PA6"),
        },
        [],
    )

    assert "## Symptom bridge" in prompt
    assert "beamstop_or_low_q_contamination" in prompt
    assert "q_bragg_min / q_corr_min" in prompt


def test_build_prompt_surfaces_allowed_actions_and_changes() -> None:
    builder = PromptBuilder()
    prompt = builder.build_prompt(
        {
            "technique": "SAXS",
            "polymer_name": "PA6",
            "params": {"L_nm": 12.0},
            "current_config": {"q_bragg_min": 0.05},
            "r_squared": 0.91,
            "residual_pattern": {"residual_type": "peak_mismatch"},
            "analysis_evidence": {
                "symptoms": [
                    {
                        "name": "peak_window_mismatch",
                        "summary": "Bragg peak window is unstable.",
                        "target_params": ["q_bragg_min", "q_bragg_max"],
                    }
                ],
            },
            "allowed_actions": [
                {
                    "name": "adjust_peak_window",
                    "allowed_params": ["q_bragg_min", "q_bragg_max", "savgol_window"],
                }
            ],
            "allowed_changes": {
                "q_bragg_min": [0.05, 0.6],
                "q_bragg_max": [0.3, 2.0],
            },
            "polymer_knowledge": load_polymer_knowledge("PA6"),
        },
        [],
    )

    assert "## Allowed actions" in prompt
    assert "adjust_peak_window" in prompt
    assert "## Allowed changes" in prompt
    assert '"q_bragg_min"' in prompt
    assert "recommended_actions" in prompt
    assert "diagnosis" in prompt


def test_build_prompt_surfaces_cross_tech_context() -> None:
    builder = PromptBuilder()
    prompt = builder.build_prompt(
        {
            "technique": "SAXS",
            "polymer_name": "PA6",
            "params": {"L_nm": 12.0},
            "current_config": {"q_bragg_min": 0.05},
            "r_squared": 0.91,
            "residual_pattern": {},
            "analysis_evidence": {},
            "polymer_knowledge": load_polymer_knowledge("PA6"),
            "workspace_context": {
                "summary": "Workspace summary",
                "joint_ai_context": {
                    "summary": "Cross-tech consistency for PA6: 1 errors, 2 warnings; focus on phi_c inconsistency",
                    "scope": "PA6",
                    "issue_count": 3,
                    "warning_count": 2,
                    "error_count": 1,
                    "issue_families": ["phi_c inconsistency", "L consistency unstable"],
                    "highlights": [
                        "ERROR | PA6 | annealed | phi_c_DSC_vs_WAXS | phi_c(DSC)=0.420 vs phi_c(WAXS)=0.100 diff=0.320 (55.2%)",
                    ],
                },
            },
        },
        [],
    )

    assert "Cross-tech context:" in prompt
    assert "issue_families=phi_c inconsistency, L consistency unstable" in prompt
    assert "Cross-tech highlights:" in prompt
    assert "phi_c(DSC)=0.420" in prompt


def test_build_prompt_surfaces_tuning_goal_in_workspace_context() -> None:
    builder = PromptBuilder()
    prompt = builder.build_prompt(
        {
            "technique": "SAXS",
            "polymer_name": "PA6",
            "params": {"L_nm": 12.0},
            "current_config": {"q_bragg_min": 0.05},
            "r_squared": 0.91,
            "residual_pattern": {},
            "analysis_evidence": {},
            "polymer_knowledge": load_polymer_knowledge("PA6"),
            "workspace_context": {
                "summary": "Workspace summary",
                "tuning_goal": "joint",
                "tuning_goal_label": "缓解联合冲突",
                "tuning_context": {
                    "summary": "Previous round summary",
                    "tuning_goal": "joint",
                    "tuning_goal_label": "缓解联合冲突",
                },
            },
        },
        [],
    )

    assert "Goal: 缓解联合冲突" in prompt
    assert "goal=缓解联合冲突" in prompt


def test_build_prompt_surfaces_joint_priority_in_tunable_params() -> None:
    builder = PromptBuilder()
    prompt = builder.build_prompt(
        {
            "technique": "WAXS",
            "polymer_name": "PA6",
            "params": {"Xc_pct": 45.0},
            "current_config": {"peak_function": "gaussian"},
            "r_squared": 0.94,
            "residual_pattern": {},
            "analysis_evidence": {},
            "tunable_params": [
                {
                    "name": "peak_function",
                    "config_field": "peak_function",
                    "current_value": "gaussian",
                    "constraint": ["gaussian", "pseudo_voigt"],
                    "type": "str",
                    "joint_priority": 3,
                    "joint_priority_reason": "tighten crystallinity partitioning before trusting phi_c",
                    "joint_priority_families": ["phi_c inconsistency"],
                }
            ],
            "polymer_knowledge": load_polymer_knowledge("PA6"),
        },
        [],
    )

    assert "joint_priority=3" in prompt
    assert "joint_reason=tighten crystallinity partitioning before trusting phi_c" in prompt
    assert "joint_families=phi_c inconsistency" in prompt


def test_build_prompt_surfaces_tuning_chain_in_workspace_context() -> None:
    builder = PromptBuilder()
    prompt = builder.build_prompt(
        {
            "technique": "SAXS",
            "polymer_name": "PA6",
            "params": {"L_nm": 12.0},
            "current_config": {"q_bragg_min": 0.05},
            "r_squared": 0.91,
            "residual_pattern": {},
            "analysis_evidence": {},
            "polymer_knowledge": load_polymer_knowledge("PA6"),
            "workspace_context": {
                "summary": "Workspace summary",
                "tuning_context": {
                    "summary": "Previous round summary: accepted 3 rounds",
                    "accepted_summary": "accepted 3 rounds",
                    "benchmark_text": "Benchmark: objective delta +0.018, accept 50.0%, rollback 50.0%, constraint hit 33.3%, symptom hit 75.0%.",
                    "benchmark_summary": {"average_objective_delta": 0.018},
                    "stop_reason": "quality guard reached",
                    "remaining_risks": "low-q coverage limited",
                    "next_goal": "keep q_bragg_min stable",
                    "history": [
                        {"round_num": 1, "accepted": True, "r_squared_after": 0.91},
                        {
                            "round_num": 2,
                            "accepted": False,
                            "r_squared_after": 0.93,
                            "llm_advice": {"rollback_reason": "symptom mismatch"},
                        },
                        {"round_num": 3, "accepted": True, "r_squared_after": 0.95},
                    ],
                },
            },
        },
        [],
    )

    assert "Tuning context:" in prompt
    assert "chain=baseline delta +0.018" in prompt
    assert "accepted 2 rounds, rolled back 1 rounds" in prompt
    assert "best candidate round 3" in prompt
    assert "remaining risks: symptom mismatch" in prompt


def test_build_prompt_surfaces_goal_priority_in_tunable_params() -> None:
    builder = PromptBuilder()
    prompt = builder.build_prompt(
        {
            "technique": "WAXS",
            "polymer_name": "PA6",
            "params": {"Xc_pct": 45.0},
            "current_config": {"peak_function": "gaussian"},
            "r_squared": 0.94,
            "residual_pattern": {},
            "analysis_evidence": {},
            "tunable_params": [
                {
                    "name": "background_method",
                    "config_field": "background_method",
                    "current_value": "linear",
                    "constraint": ["linear", "polynomial", "spline", "chebyshev"],
                    "type": "str",
                    "goal_priority": 4,
                    "goal_priority_reason": "reduce background risk before widening the interpretation",
                    "goal_priority_goals": ["risk"],
                }
            ],
            "polymer_knowledge": load_polymer_knowledge("PA6"),
        },
        [],
    )

    assert "goal_priority=4" in prompt
    assert "goal_reason=reduce background risk before widening the interpretation" in prompt
    assert "goal_tags=risk" in prompt
