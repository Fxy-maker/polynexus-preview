from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any

from polynexus.config_bridge import DSC_PARAM_MAP, IR_PARAM_MAP, NMR_PARAM_MAP, SAXS_PARAM_MAP, WAXS_PARAM_MAP
from polynexus.core.preprocess_optimization import get_preprocess_policy
from rag.preprocess_intent import PREPROCESS_ACTION_NAMES
from rag.polymer_knowledge import format_polymer_knowledge


class PromptBuilder:
    def build(
        self,
        current_sample: dict[str, Any],
        retrieved_cases: list[dict[str, Any]],
        history: list[Any] | None = None,
        workspace_context: dict[str, Any] | None = None,
    ) -> str:
        return self.build_prompt(current_sample, retrieved_cases, history, workspace_context=workspace_context)

    def build_prompt(
        self,
        current_sample: dict[str, Any],
        retrieved_cases: list[dict[str, Any]],
        history: list[Any] | None = None,
        workspace_context: dict[str, Any] | None = None,
    ) -> str:
        workspace_context = workspace_context or current_sample.get("workspace_context", {})
        technique = str(current_sample.get("technique", "WAXS") or "WAXS").strip().upper()

        if technique == "DSC":
            prompt = self._build_dsc_prompt(current_sample, retrieved_cases, history)
        elif technique == "SAXS":
            prompt = self._build_saxs_prompt(current_sample, retrieved_cases, history)
        elif technique == "IR":
            submodule = str(current_sample.get("submodule", current_sample.get("submodule_id", "")) or "").strip().lower()
            if submodule == "ir.temperature_2d":
                prompt = self._build_ir_temperature_2d_prompt(current_sample, retrieved_cases, history)
            else:
                prompt = self._build_ir_prompt(current_sample, retrieved_cases, history)
        elif technique == "NMR":
            prompt = self._build_nmr_prompt(current_sample, retrieved_cases, history)
        else:
            prompt = self._build_waxs_prompt(current_sample, retrieved_cases, history)

        prompt = self._append_analysis_evidence(prompt, current_sample)
        return self._append_workspace_context(prompt, workspace_context)

    def _build_waxs_prompt(
        self,
        current_sample: dict[str, Any],
        retrieved_cases: list[dict[str, Any]],
        history: list[Any] | None = None,
    ) -> str:
        retrieved_text = self._format_retrieved_cases(retrieved_cases)
        polymer_name = str(current_sample.get("polymer_name", "unknown"))
        params = current_sample.get("params", current_sample.get("output_parameters", {}))
        current_config = current_sample.get("current_config", {})
        r_squared = self._safe_float(current_sample.get("r_squared", 0.0))
        residual_summary = self._get_residual_summary(current_sample, "未提供残差分析。")
        residual_pattern = current_sample.get("residual_pattern", {})
        if not isinstance(residual_pattern, dict):
            residual_pattern = {}
        polymer_knowledge = current_sample.get("polymer_knowledge", {})
        if not isinstance(polymer_knowledge, dict):
            polymer_knowledge = {}
        tunable_params = current_sample.get("tunable_params") or self._default_tunable_params("WAXS", current_config)
        rounds = history if history is not None else current_sample.get("history", [])
        history_text = self.format_history(rounds)
        polymer_reference = format_polymer_knowledge(polymer_knowledge, params, technique="WAXS")
        xc_range_text = self._format_xc_range(polymer_knowledge, "WAXS")
        characteristic_peaks = self._format_reference_features(polymer_knowledge, "WAXS")
        strategy_hint = self._strategy_hint(polymer_knowledge, params, current_config, residual_pattern, "WAXS")
        params_text = self._json_dumps({"config": current_config, "extracted_parameters": params}, indent=2)
        tunable_text = self._format_tunable_params(tunable_params)
        current_xc = self._extract_xc(params)
        max_residual_region = str(residual_pattern.get("max_residual_region", "unknown"))
        residual_type = str(residual_pattern.get("residual_type", "unknown"))

        lines = [
            "[SYSTEM]",
            "你是一个 WAXS 谱图拟合参数优化专家。",
            "你的任务是根据当前拟合状态、历史轮次、参考知识和检索案例，给出下一轮最小幅度、可执行的参数调整建议，而不是替用户做最终科学判断。",
            "规则：",
            "- 每轮只改 1-2 个参数。",
            "- 禁止重复建议历史里已经回滚或验证无效的参数组合。",
            "- 只能从可调参数白名单中选择 changes。",
            "- 按调参优先级顺序尝试。",
            '- 如果判断已经收敛，输出 {"converge": true, "changes": {}}。',
            "",
            "[USER]",
            "## 当前状态",
            f"- 技术类型：{current_sample.get('technique', 'WAXS')}",
            f"- 聚合物：{polymer_name}",
            f"- 当前 r²：{r_squared:.4f}",
            f"- 当前 Xc：{current_xc}",
            "",
            "## 参考知识",
            polymer_reference,
            f"（标准 Xc 范围：{xc_range_text}；标准特征峰：{characteristic_peaks}）",
            "",
            "## 残差分析",
            residual_summary,
            f"（残差最大区域：{max_residual_region}，类型：{residual_type}）",
            "",
            "## 调参优先级",
            strategy_hint,
            "",
            "## 历史轮次",
            history_text,
            "",
            "## 当前参数",
            params_text,
            "",
            "## 可调参数白名单",
            tunable_text,
            "",
            "## 历史参考案例（RAG 检索结果）",
            retrieved_text,
            "",
            "## 任务",
            "根据以上信息，给出下一轮参数修改建议（JSON）。只改最可能提升 r² 的 1-2 个参数；若历史中已有 ❌ 回滚组合，不得重复建议。",
            "输出格式：",
            "{",
            '  "assessment": "PASS | WARN | FAIL",',
            '  "confidence": 0.85,',
            '  "reasoning": "...",',
            '  "changes": {',
            '    "peak_function": "pseudo_voigt"',
            "  },",
            '  "expected_improvement": {',
            '    "r_squared": "0.936 -> 0.940+"',
            "  },",
            '  "risk": "low | medium | high",',
            '  "suggestions": ["建议1", "建议2"],',
            '  "reference_cases": ["case_id_1", "case_id_2"],',
            '  "converge": false',
            "}",
            "只输出 JSON，不要有任何额外文字。",
        ]

        return "\n".join(lines)

    def _build_ir_temperature_2d_prompt(
        self,
        current_sample: dict[str, Any],
        retrieved_cases: list[dict[str, Any]],
        history: list[Any] | None = None,
    ) -> str:
        retrieved_text = self._format_retrieved_cases(retrieved_cases)
        params = current_sample.get("params", current_sample.get("output_parameters", {}))
        current_config = current_sample.get("current_config", {})
        r_squared = self._safe_float(current_sample.get("r_squared", 0.0))
        residual_summary = self._get_residual_summary(current_sample, "未提供二维 IR 残差分析。")
        residual_pattern = current_sample.get("residual_pattern", {})
        if not isinstance(residual_pattern, dict):
            residual_pattern = {}
        polymer_knowledge = current_sample.get("polymer_knowledge", {})
        if not isinstance(polymer_knowledge, dict):
            polymer_knowledge = {}
        tunable_params = current_sample.get("tunable_params") or self._default_tunable_params("IR", current_config)
        history_text = self.format_history(history if history is not None else current_sample.get("history", []))
        params_text = self._json_dumps({"config": current_config, "extracted_parameters": params}, indent=2)
        tunable_text = self._format_tunable_params(tunable_params)
        current_frames = self._metric(params, "n_frames")
        current_range = str(params.get("T_range_C", "unknown") or "unknown")
        current_sync = self._metric(params, "sync_cross_peak_count")
        current_async = self._metric(params, "async_cross_peak_count")
        current_neg = self._metric(params, "neg_fraction", precision=3)
        current_transition = self._metric(params, "transition_count")
        current_band_support = self._metric(params, "band_index_transition_support_band_count")
        current_band_spread = self._metric(params, "band_index_transition_frame_spread", precision=2)
        current_band_repro = self._metric(params, "band_index_transition_reproducible")
        polymer_reference = format_polymer_knowledge(polymer_knowledge, params, technique="IR")

        lines = [
            "[SYSTEM]",
            "你是一个原位变温二维 IR（2D-COS）分析与参数优化专家。",
            "你的任务是根据当前序列、矩阵质量、同步/异步交叉峰和历史轮次，给出下一轮最小幅度、可执行的参数调整建议，而不是替用户做最终判断。",
            "规则：",
            "- 每轮只改 1-2 个参数。",
            "- 先看 sequence axis 和 matrix quality，再看 sync/async cross peaks。",
            "- 先判断 band index 变化是不是被多带一致支撑，再判断 transition 是否值得继续保留。",
            "- 如果序列轴不稳、矩阵过度扣底或交叉峰很弱，优先修复 core 约束，不要硬抬结论。",
            "- 只允许围绕这些证据调整: 序列轴恢复 / matrix quality / wavenumber grid / frame scale / band tracking / 2D-COS cross-peak stability。",
            "- 只能从可调参数白名单中选择 changes。",
            "- 如果已经稳定收敛，输出 {\"converge\": true, \"changes\": {}}。",
            "",
            "[USER]",
            "## 当前状态",
            "- 技术类别: IR",
            "- 子模块: 原位变温二维 IR",
            f"- 当前 r²: {r_squared:.4f}",
            f"- 当前帧数: {current_frames}",
            f"- 温度范围: {current_range}",
            f"- 同步交叉峰: {current_sync}",
            f"- 异步交叉峰: {current_async}",
            f"- 负值比例: {current_neg}",
            f"- 转变候选数: {current_transition}",
            f"- 带指数支撑数: {current_band_support}",
            f"- 带指数帧扩散: {current_band_spread}",
            f"- 带指数趋势可重复: {current_band_repro}",
            "",
            "## 参考信息",
            polymer_reference,
            "",
            "## 残差分析",
            residual_summary,
            "",
            "## 历史轮次",
            history_text,
            "",
            "## 当前参数",
            params_text,
            "",
            "## 可调参数白名单",
            tunable_text,
            "",
            "## 历史参考案例（RAG 检索结果）",
            retrieved_text,
            "",
            "## 任务",
            "请基于上面的二维 IR 证据，输出下一轮参数修改建议（JSON）。优先让序列轴、矩阵质量和 2D-COS 交叉峰更可信；如果它们仍然不稳，不要为了追求漂亮结果而强行抬高结论。",
            "输出格式：",
            "{",
            '  "assessment": "PASS | WARN | FAIL",',
            '  "confidence": 0.85,',
            '  "reasoning": "...",',
            '  "changes": {',
            '    "smooth_window": 7',
            "  },",
            '  "expected_improvement": {',
            '    "matrix_quality_score": "0.62 -> 0.70+"',
            "  },",
            '  "risk": "low | medium | high",',
            '  "suggestions": ["建议1", "建议2"],',
            '  "reference_cases": ["case_id_1", "case_id_2"],',
            '  "converge": false',
            "}",
            "只输出 JSON，不要有任何额外文字。",
        ]

        return "\n".join(lines)

    def _build_dsc_prompt(
        self,
        current_sample: dict[str, Any],
        retrieved_cases: list[dict[str, Any]],
        history: list[Any] | None = None,
    ) -> str:
        retrieved_text = self._format_retrieved_cases(retrieved_cases)
        polymer_name = str(current_sample.get("polymer_name", "unknown"))
        params = current_sample.get("params", current_sample.get("output_parameters", {}))
        current_config = current_sample.get("current_config", {})
        r_squared = self._safe_float(current_sample.get("r_squared", 0.0))
        residual_summary = self._get_residual_summary(current_sample, "未提供 DSC 残差分析。")
        residual_pattern = current_sample.get("residual_pattern", {})
        if not isinstance(residual_pattern, dict):
            residual_pattern = {}
        polymer_knowledge = current_sample.get("polymer_knowledge", {})
        if not isinstance(polymer_knowledge, dict):
            polymer_knowledge = {}
        tunable_params = current_sample.get("tunable_params") or self._default_tunable_params("DSC", current_config)
        history_text = self.format_history(history if history is not None else current_sample.get("history", []))
        dsc_reference = self._format_dsc_reference(polymer_knowledge, params)
        dsc_strategy = self._dsc_strategy_hint(polymer_knowledge, params, current_config, residual_pattern)
        params_text = self._json_dumps({"config": current_config, "extracted_parameters": params}, indent=2)
        tunable_text = self._format_tunable_params(tunable_params)

        current_tm = self._metric(params, "Tm_peak_C")
        current_tc = self._metric(params, "Tc_peak_C")
        current_tg = self._metric(params, "Tg_C")
        current_dhm = self._metric(params, "DHm_Jg")
        current_xc = self._extract_xc(params)

        lines = [
            "[SYSTEM]",
            "你是一个 DSC（差示扫描量热）拟合参数优化专家。",
            "你的任务是根据当前曲线、历史轮次、参考知识和检索案例，给出下一轮最小幅度、可执行的参数调整建议，而不是直接做最终结论。",
            "规则：",
            "- 每轮只改 1-2 个参数。",
            "- 禁止重复建议历史里已经回滚或验证无效的参数组合。",
            "- 只能从可调参数白名单中选择 changes。",
            "- 按调参优先级顺序尝试。",
            '- 如果判断已经收敛，输出 {"converge": true, "changes": {}}。',
            "",
            "[USER]",
            "## 当前状态",
            "- 技术类型：DSC",
            f"- 聚合物：{polymer_name}",
            f"- 当前 r²：{r_squared:.4f}",
            f"- 当前 Tm：{current_tm} °C",
            f"- 当前 Tc：{current_tc} °C",
            f"- 当前 Tg：{current_tg} °C",
            f"- 当前 ΔHm：{current_dhm} J/g",
            f"- 当前 Xc：{current_xc}",
            "",
            "## 参考知识",
            dsc_reference,
            "",
            "## 残差分析",
            residual_summary,
            "",
            "## 调参优先级",
            dsc_strategy,
            "",
            "## 历史轮次",
            history_text,
            "",
            "## 当前参数",
            params_text,
            "",
            "## 可调参数白名单",
            tunable_text,
            "",
            "## 历史参考案例（RAG 检索结果）",
            retrieved_text,
            "",
            "## 任务",
            "根据以上信息，给出下一轮 DSC 参数修改建议（JSON）。只改最可能提升拟合质量的 1-2 个参数；若历史中已有 ❌ 回滚组合，不得重复建议。",
            "输出格式：",
            "{",
            '  "assessment": "PASS | WARN | FAIL",',
            '  "confidence": 0.85,',
            '  "reasoning": "...",',
            '  "changes": {',
            '    "baseline_type": "linear"',
            "  },",
            '  "expected_improvement": {',
            '    "r_squared": "0.920 -> 0.945+"',
            "  },",
            '  "risk": "low | medium | high",',
            '  "suggestions": ["建议1", "建议2"],',
            '  "reference_cases": ["case_id_1", "case_id_2"],',
            '  "converge": false',
            "}",
            "只输出 JSON，不要有任何额外文字。",
        ]

        return "\n".join(lines)

    def _build_saxs_prompt(
        self,
        current_sample: dict[str, Any],
        retrieved_cases: list[dict[str, Any]],
        history: list[Any] | None = None,
    ) -> str:
        retrieved_text = self._format_retrieved_cases(retrieved_cases)
        polymer_name = str(current_sample.get("polymer_name", "unknown"))
        params = current_sample.get("params", current_sample.get("output_parameters", {}))
        current_config = current_sample.get("current_config", {})
        r_squared = self._safe_float(current_sample.get("r_squared", 0.0))
        residual_summary = self._get_residual_summary(current_sample, "未提供 SAXS 残差分析。")
        residual_pattern = current_sample.get("residual_pattern", {})
        if not isinstance(residual_pattern, dict):
            residual_pattern = {}
        polymer_knowledge = current_sample.get("polymer_knowledge", {})
        if not isinstance(polymer_knowledge, dict):
            polymer_knowledge = {}
        tunable_params = current_sample.get("tunable_params") or self._default_tunable_params("SAXS", current_config)
        history_text = self.format_history(history if history is not None else current_sample.get("history", []))
        saxs_reference = self._format_saxs_reference(polymer_knowledge, params)
        saxs_strategy = self._saxs_strategy_hint(polymer_knowledge, params, current_config, residual_pattern)
        params_text = self._json_dumps({"config": current_config, "extracted_parameters": params}, indent=2)
        tunable_text = self._format_tunable_params(tunable_params)

        current_l = self._metric(params, "L_nm", precision=3)
        current_lc = self._metric(params, "lc_nm", precision=3)
        current_phi_c = self._metric(params, "phi_c", precision=3)
        current_rg = self._metric(params, "Rg_nm", precision=3)
        current_snr = self._metric(params, "q_peak_snr", precision=3)

        lines = [
            "[SYSTEM]",
            "你是一个 SAXS 数据分析与参数优化专家。",
            "你的任务是根据当前拟合状态、历史轮次、参考知识和检索案例，给出下一轮最小幅度、可执行的参数调整建议，而不是直接做最终判断。",
            "规则：",
            "- 每轮只改 1-2 个参数。",
            "- 禁止重复建议历史里已经回滚或验证无效的参数组合。",
            "- 只能从可调参数白名单中选择 changes。",
            "- 按调参优先级顺序尝试。",
            '- 如果判断已经收敛，输出 {"converge": true, "changes": {}}。',
            "",
            "[USER]",
            "## 当前状态",
            "- 技术类型：SAXS",
            f"- 聚合物：{polymer_name}",
            f"- 当前 r²：{r_squared:.4f}",
            f"- 当前长周期 L：{current_l} nm",
            f"- 当前晶片厚度 lc：{current_lc} nm",
            f"- 当前体积分数 φc：{current_phi_c}",
            f"- 当前 Rg：{current_rg} nm",
            f"- 当前 Bragg 峰 SNR：{current_snr}",
            "",
            "## 参考知识",
            saxs_reference,
            "",
            "## 残差分析",
            residual_summary,
            "",
            "## 调参优先级",
            saxs_strategy,
            "",
            "## 历史轮次",
            history_text,
            "",
            "## 当前参数",
            params_text,
            "",
            "## 可调参数白名单",
            tunable_text,
            "",
            "## 历史参考案例（RAG 检索结果）",
            retrieved_text,
            "",
            "## 任务",
            "根据以上信息，给出下一轮 SAXS 参数修改建议（JSON）。只改最可能提升拟合质量的 1-2 个参数；若历史中已有 ❌ 回滚组合，不得重复建议。",
            "输出格式：",
            "{",
            '  "assessment": "PASS | WARN | FAIL",',
            '  "confidence": 0.85,',
            '  "reasoning": "...",',
            '  "changes": {',
            '    "savgol_window": 15',
            "  },",
            '  "expected_improvement": {',
            '    "r_squared": "0.880 -> 0.920+"',
            "  },",
            '  "risk": "low | medium | high",',
            '  "suggestions": ["建议1", "建议2"],',
            '  "reference_cases": ["case_id_1", "case_id_2"],',
            '  "converge": false',
            "}",
            "只输出 JSON，不要有任何额外文字。",
        ]

        return "\n".join(lines)

    def _build_ir_prompt(
        self,
        current_sample: dict[str, Any],
        retrieved_cases: list[dict[str, Any]],
        history: list[Any] | None = None,
    ) -> str:
        retrieved_text = self._format_retrieved_cases(retrieved_cases)
        polymer_name = str(current_sample.get("polymer_name", "unknown"))
        params = current_sample.get("params", current_sample.get("output_parameters", {}))
        current_config = current_sample.get("current_config", {})
        r_squared = self._safe_float(current_sample.get("r_squared", 0.0))
        residual_summary = self._get_residual_summary(current_sample, "未提供 IR 残差分析。")
        residual_pattern = current_sample.get("residual_pattern", {})
        if not isinstance(residual_pattern, dict):
            residual_pattern = {}
        polymer_knowledge = current_sample.get("polymer_knowledge", {})
        if not isinstance(polymer_knowledge, dict):
            polymer_knowledge = {}
        ir_reference_bands = current_sample.get("ir_reference_bands", {})
        if not isinstance(ir_reference_bands, dict):
            ir_reference_bands = {}
        tunable_params = current_sample.get("tunable_params") or self._default_tunable_params("IR", current_config)
        history_text = self.format_history(history if history is not None else current_sample.get("history", []))
        ir_reference = self._format_ir_reference(polymer_knowledge, params, ir_reference_bands, current_sample.get("analysis_evidence", {}))
        ir_strategy = self._ir_strategy_hint(current_sample, polymer_knowledge, current_config, residual_pattern)
        params_text = self._json_dumps({"config": current_config, "extracted_parameters": params}, indent=2)
        tunable_text = self._format_tunable_params(tunable_params)

        current_n_peaks = self._metric(params, "n_peaks", precision=0)
        current_polymer_score = self._metric(params, "polymer_score", precision=3)
        current_r2 = self._safe_float(params.get("r_squared", r_squared))

        lines = [
            "[SYSTEM]",
            "你是一个 IR 光谱分析与参数优化专家。",
            "你的任务是根据当前拟合状态、历史轮次、参考知识和检索案例，给出下一轮最小幅度、可执行的参数调整建议，而不是直接做最终判断。",
            "规则：",
            "- 每轮只改 1-2 个参数。",
            "- 禁止重复建议历史里已经回滚或验证无效的参数组合。",
            "- 只能从可调参数白名单中选择 changes。",
            "- 按调参优先级顺序尝试。",
            '- 如果判断已经收敛，输出 {"converge": true, "changes": {}}。',
            "",
            "[USER]",
            "## 当前状态",
            "- 技术类型：IR",
            f"- 聚合物：{polymer_name}",
            f"- 当前 r²：{current_r2:.4f}",
            f"- 检测峰数：{current_n_peaks}",
            f"- 聚合物匹配分数：{current_polymer_score}",
            "",
            "## 参考知识",
            ir_reference,
            "",
            "## 残差分析",
            residual_summary,
            "",
            "## 调参优先级",
            ir_strategy,
            "",
            "## 历史轮次",
            history_text,
            "",
            "## 当前参数",
            params_text,
            "",
            "## 可调参数白名单",
            tunable_text,
            "",
            "## 历史参考案例（RAG 检索结果）",
            retrieved_text,
            "",
            "## 任务",
            "根据以上信息，给出下一轮 IR 参数修改建议（JSON）。只改最可能提升拟合质量的 1-2 个参数；若历史中已有 ❌ 回滚组合，不得重复建议。",
            "输出格式：",
            "{",
            '  "assessment": "PASS | WARN | FAIL",',
            '  "confidence": 0.85,',
            '  "reasoning": "...",',
            '  "changes": {',
            '    "peak_height_min": 0.015',
            "  },",
            '  "expected_improvement": {',
            '    "r_squared": "0.910 -> 0.935+"',
            "  },",
            '  "risk": "low | medium | high",',
            '  "suggestions": ["建议1", "建议2"],',
            '  "reference_cases": ["case_id_1", "case_id_2"],',
            '  "converge": false',
            "}",
            "只输出 JSON，不要有任何额外文字。",
        ]

        return "\n".join(lines)

    def _build_nmr_prompt(
        self,
        current_sample: dict[str, Any],
        retrieved_cases: list[dict[str, Any]],
        history: list[Any] | None = None,
    ) -> str:
        retrieved_text = self._format_retrieved_cases(retrieved_cases)
        polymer_name = str(current_sample.get("polymer_name", "unknown"))
        params = current_sample.get("params", current_sample.get("output_parameters", {}))
        current_config = current_sample.get("current_config", {})
        r_squared = self._safe_float(current_sample.get("r_squared", 0.0))
        residual_summary = self._get_residual_summary(current_sample, "No residual summary provided.")
        polymer_knowledge = current_sample.get("polymer_knowledge", {})
        if not isinstance(polymer_knowledge, dict):
            polymer_knowledge = {}
        tunable_params = current_sample.get("tunable_params") or self._default_tunable_params("NMR", current_config)
        history_text = self.format_history(history if history is not None else current_sample.get("history", []))
        nmr_reference = self._format_nmr_reference(polymer_knowledge)
        nmr_tips = self._nmr_strategy_hint(current_sample, polymer_knowledge, current_config)
        params_text = self._json_dumps({"config": current_config, "extracted_parameters": params}, indent=2)
        tunable_text = self._format_tunable_params(tunable_params)

        current_n_peaks = self._metric(params, "n_peaks", precision=0)
        current_peak_distance = self._metric(params, "peak_distance_ppm", precision=3)
        current_baseline = str(current_config.get("baseline_method", current_config.get("baseline_order", "unknown")))

        lines = [
            "[SYSTEM]",
            "You are a PolyNexus NMR analysis expert for liquid and solid-state spectra.",
            "Return strict JSON only.",
            "Rules:",
            "- Modify only 1-2 parameters per round.",
            "- Prefer the smallest change that improves the fit.",
            "- Historical rejected parameter combinations must not be repeated.",
            '- If the current fit is already good enough, return {"converge": true, "changes": {}}.',
            "",
            "[USER]",
            "## 当前状态",
            "- 技术类型：NMR",
            f"- 聚合物：{polymer_name}",
            f"- 当前 r²：{r_squared:.4f}",
            f"- 峰数：{current_n_peaks}",
            f"- 峰间距：{current_peak_distance}",
            f"- 基线设置：{current_baseline}",
            "",
            "## 参考知识",
            nmr_reference,
            "",
            "## 残差分析",
            residual_summary,
            "",
            "## 调参优先级",
            nmr_tips,
            "",
            "## 历史轮次",
            history_text,
            "",
            "## 当前参数",
            params_text,
            "",
            "## 可调参数白名单",
            tunable_text,
            "",
            "## 历史参考案例（RAG 检索结果）",
            retrieved_text,
            "",
            "## 任务",
            "Suggest the next parameter changes as JSON. Use only the whitelist above.",
            "Output format:",
            "{",
            '  "assessment": "PASS | WARN | FAIL",',
            '  "confidence": 0.85,',
            '  "reasoning": "...",',
            '  "changes": {',
            '    "peak_height_min": 0.03',
            "  },",
            '  "expected_improvement": {',
            '    "r_squared": "0.421 -> 0.500+"',
            "  },",
            '  "risk": "low | medium | high",',
            '  "suggestions": ["suggestion 1", "suggestion 2"],',
            '  "reference_cases": ["case_id_1", "case_id_2"],',
            '  "converge": false',
            "}",
            "只输出 JSON，不要有任何额外文字。",
        ]

        return "\n".join(lines)

    def _format_dsc_reference(self, knowledge: dict[str, Any], params: dict[str, Any]) -> str:
        dsc = knowledge.get("dsc", {}) if isinstance(knowledge, dict) else {}
        if not dsc:
            name = knowledge.get("name", "unknown") if isinstance(knowledge, dict) else "unknown"
            return f"参考知识：未找到 {name} 的 DSC 参考知识。"

        parts = [f"参考知识：{knowledge.get('name', 'unknown')}"]
        if dsc.get("tm") is not None:
            parts.append(f"标准 Tm≈{dsc['tm']}°C")
        if dsc.get("tc") is not None:
            parts.append(f"标准 Tc≈{dsc['tc']}°C")
        if dsc.get("delta_hm_100") is not None:
            parts.append(f"100%结晶熔融焓 ΔHm0={dsc['delta_hm_100']} J/g")
        xc_range = dsc.get("xc_range")
        if isinstance(xc_range, list) and len(xc_range) == 2:
            parts.append(f"标准 Xc 范围：{xc_range[0]}-{xc_range[1]}%")
        current_xc = self._extract_xc_value(params)
        if current_xc is not None and isinstance(xc_range, list) and len(xc_range) == 2:
            low, high = float(xc_range[0]), float(xc_range[1])
            if current_xc < low:
                parts.append(f"当前 Xc={current_xc:.1f}% 偏低")
            elif current_xc > high:
                parts.append(f"当前 Xc={current_xc:.1f}% 偏高")
            else:
                parts.append(f"当前 Xc={current_xc:.1f}% 在参考范围内")
        return "；".join(parts) + "。"

    def _dsc_strategy_hint(
        self,
        knowledge: dict[str, Any],
        params: dict[str, Any],
        current_config: dict[str, Any],
        residual_pattern: dict[str, Any],
    ) -> str:
        hints: list[str] = []
        dsc = knowledge.get("dsc", {}) if isinstance(knowledge, dict) else {}
        current_xc = self._extract_xc_value(params)
        xc_range = dsc.get("xc_range")
        residual_type = residual_pattern.get("residual_type", "unknown") if isinstance(residual_pattern, dict) else "unknown"
        current_tm = params.get("Tm_peak_C") if isinstance(params, dict) else None
        ref_tm = dsc.get("tm")
        current_baseline = current_config.get("baseline_corr", current_config.get("baseline_type", "auto"))

        hints.append(f"1. 基线优先：当前 baseline_type={current_baseline}，若残差呈背景漂移，优先尝试 baseline_type。")
        hints.append("2. 峰位/搜索窗优先：Tm/Tc 偏离时，优先调整 Tm_search_low_C / Tm_search_high_C 或 Tc_search_low_C / Tc_search_high_C。")
        hints.append("3. 峰形优先：若峰形不匹配或过宽/过窄，优先调 peak_function，再考虑 smooth_window。")

        if current_tm is not None and ref_tm is not None:
            try:
                delta = float(current_tm) - float(ref_tm)
                if abs(delta) > 10:
                    hints.append(f"当前 Tm={float(current_tm):.1f}°C 与标准 {float(ref_tm):.1f}°C 偏差 {delta:+.1f}°C。")
            except (TypeError, ValueError):
                pass

        if residual_type in {"baseline_drift", "baseline_drift_low_t", "baseline_drift_high_t"}:
            hints.append("Residual is baseline drift: stabilize baseline_corr or baseline_type before moving event windows.")
        elif residual_type in {"peak_shift", "melting_peak_shift"}:
            hints.append("Residual is peak shift: re-center Tm/Tc search windows before touching peak_function.")
        elif residual_type == "tg_step_missing":
            hints.append("Residual is tg_step_missing: inspect Tg window support and DCp before trusting Tg.")
        elif residual_type == "cold_crystallization_overlap":
            hints.append("Residual is cold_crystallization_overlap: separate Tcc from the melting window first.")
        elif residual_type == "event_window_too_narrow":
            hints.append("Residual is event_window_too_narrow: widen the event window before re-fitting.")
        elif residual_type == "event_window_too_wide":
            hints.append("Residual is event_window_too_wide: narrow the event window before trusting the fit.")
        elif residual_type == "exo_up_down_confusion":
            hints.append("Residual is exo_up_down_confusion: verify the exo_up convention and signed enthalpy.")
        elif residual_type == "multi_event_underfit":
            hints.append("Residual is multi_event_underfit: allow more than one thermal event or component.")
        elif residual_type == "segment_split_issue":
            hints.append("Residual is segment_split_issue: check whether the scan was split at the wrong point.")
        elif residual_type in {"noise", "noise_dominant"}:
            hints.append("Residual is noise: increase smooth_window before changing peak thresholds.")

        if current_xc is not None and isinstance(xc_range, list) and len(xc_range) == 2:
            low, high = float(xc_range[0]), float(xc_range[1])
            if current_xc > high:
                hints.append("当前 Xc 偏高：优先检查基线扣除与峰面积是否过大。")
            elif current_xc < low:
                hints.append("当前 Xc 偏低：优先检查弱峰漏检或积分区间不足。")
            else:
                hints.append("当前 Xc 在参考范围内：优先围绕残差最大区域做微调。")

        return "\n".join(f"- {hint}" for hint in hints)

    def _format_saxs_reference(self, knowledge: dict[str, Any], params: dict[str, Any]) -> str:
        if not isinstance(knowledge, dict) or not knowledge:
            return "参考知识：未找到当前聚合物的 SAXS/WAXS 参考知识。"

        parts = [f"参考知识：{knowledge.get('name', 'unknown')}"]
        waxs = knowledge.get("waxs", {})
        if isinstance(waxs, dict):
            peaks = waxs.get("characteristic_peaks", []) or []
            peak_texts: list[str] = []
            for peak in peaks:
                if isinstance(peak, dict) and peak.get("two_theta") is not None:
                    phase = f"({peak['crystal_phase']})" if peak.get("crystal_phase") else ""
                    peak_texts.append(f"{peak['two_theta']}°{phase}")
            if peak_texts:
                parts.append(f"WAXS 特征峰：{'、'.join(peak_texts)}")
        xc_range = waxs.get("xc_range")
        if isinstance(xc_range, list) and len(xc_range) == 2:
            parts.append(f"参考 Xc 范围：{xc_range[0]}-{xc_range[1]}%")
        current_xc = self._extract_xc_value(params)
        if current_xc is not None and isinstance(xc_range, list) and len(xc_range) == 2:
            low, high = float(xc_range[0]), float(xc_range[1])
            if current_xc < low:
                parts.append(f"当前 Xc={current_xc:.1f}% 偏低")
            elif current_xc > high:
                parts.append(f"当前 Xc={current_xc:.1f}% 偏高")
            else:
                parts.append(f"当前 Xc={current_xc:.1f}% 在参考范围内")
        return "；".join(parts) + "。"

    def _saxs_strategy_hint(
        self,
        knowledge: dict[str, Any],
        params: dict[str, Any],
        current_config: dict[str, Any],
        residual_pattern: dict[str, Any],
    ) -> str:
        hints: list[str] = [
            "High-priority SAXS smoothing parameter: savgol_window is the first knob for noisy EDF data and directly affects Bragg peak-region r_squared.",
            "Keep savgol_window odd and savgol_order smaller than savgol_window.",
        ]
        residual_type = residual_pattern.get("residual_type", "unknown") if isinstance(residual_pattern, dict) else "unknown"
        current_r2 = self._safe_float(params.get("r_squared", params.get("fit_r_squared", 0.0)))
        if current_r2 >= 0.90:
            hints.append("当前 r_squared 已经较高，只有残差仍呈结构化时才继续加大平滑。")
        if residual_type == "peak_mismatch":
            hints.append("残差类型为 peak_mismatch：先调 savgol_window，再检查 q_bragg_min / q_bragg_max 是否遮住 Bragg 峰。")
        elif residual_type == "noise":
            hints.append("残差类型为 noise：优先调 savgol_window，而不是先动 q_corr 或 IDF 阈值。")
        elif residual_type == "background_drift":
            hints.append("残差类型为 background_drift：先确认平滑是否足够，再考虑 q_corr 范围。")
        current_savgol = current_config.get("savgol_window")
        current_order = current_config.get("savgol_order")
        if current_savgol is not None:
            hints.append(f"当前 savgol_window={current_savgol}，若要提升 Bragg 峰拟合，可尝试 11/15/19/21 等奇数。")
        if current_order is not None:
            hints.append(f"当前 savgol_order={current_order}，必须小于 savgol_window。")
        return "\n".join(f"- {hint}" for hint in hints)

    def _format_ir_reference(
        self,
        knowledge: dict[str, Any],
        params: dict[str, Any],
        ir_reference_bands: dict[str, Any] | None = None,
        analysis_evidence: dict[str, Any] | None = None,
    ) -> str:
        evidence_source = analysis_evidence if isinstance(analysis_evidence, dict) else {}
        feature_evidence = evidence_source.get("feature_evidence", {}) if isinstance(evidence_source.get("feature_evidence"), dict) else {}
        if not isinstance(feature_evidence, dict) or not feature_evidence:
            feature_evidence = evidence_source if isinstance(evidence_source, dict) else {}

        bands_payload = ir_reference_bands if isinstance(ir_reference_bands, dict) else {}
        ir_knowledge = knowledge.get("ir", {}) if isinstance(knowledge, dict) else {}
        if not isinstance(ir_knowledge, dict):
            ir_knowledge = {}
        reference_evidence = feature_evidence.get("reference_evidence", {}) if isinstance(feature_evidence.get("reference_evidence"), dict) else {}
        assignment_evidence = feature_evidence.get("assignment_evidence", {}) if isinstance(feature_evidence.get("assignment_evidence"), dict) else {}
        structure_evidence = feature_evidence.get("structure_evidence", {}) if isinstance(feature_evidence.get("structure_evidence"), dict) else {}

        bands = bands_payload.get("bands", [])
        if not isinstance(bands, list) or not bands:
            bands = reference_evidence.get("bands", []) if isinstance(reference_evidence.get("bands"), list) else []

        polymer_name = ""
        if isinstance(knowledge, dict):
            polymer_name = str(knowledge.get("name", "") or "").strip()
        if not polymer_name:
            polymer_name = str(bands_payload.get("polymer_name", "") or "").strip()
        if not polymer_name:
            polymer_name = str(reference_evidence.get("polymer_name", "") or "").strip()

        if polymer_name:
            parts = [f"参考知识：{polymer_name}"]
        elif isinstance(bands, list) and bands:
            parts = ["参考知识：IR 参考带已加载"]
        else:
            return "参考知识：未找到当前聚合物的 IR 参考知识。"

        knowledge_bands = ir_knowledge.get("characteristic_bands", [])
        if isinstance(knowledge_bands, list) and knowledge_bands:
            key_band_text = self._format_ir_band_group(knowledge_bands, ir_knowledge.get("key_bands"), limit=6)
            secondary_band_text = self._format_ir_band_group(knowledge_bands, ir_knowledge.get("secondary_bands"), limit=6)
            overlap_risks = self._join_text_items(ir_knowledge.get("overlap_risks"))
            assignment_notes = self._join_text_items(ir_knowledge.get("assignment_notes"))
            if key_band_text:
                parts.append(f"IR 强特征带：{key_band_text}")
            if secondary_band_text:
                parts.append(f"IR 辅助带：{secondary_band_text}")
            if overlap_risks:
                parts.append(f"IR 重叠风险：{overlap_risks}")
            if assignment_notes:
                parts.append(f"IR 归属提示：{assignment_notes}")

        if isinstance(bands, list) and bands:
            band_texts: list[str] = []
            for band in bands[:8]:
                if not isinstance(band, dict):
                    continue
                wavenumber = band.get("wavenumber")
                if wavenumber is None:
                    continue
                label = f"{wavenumber} cm^-1"
                assignment = str(band.get("assignment", "") or "").strip()
                if assignment:
                    label += f" ({assignment})"
                if band.get("crystallinity_sensitive"):
                    label += " *"
                band_texts.append(label)
            if band_texts:
                parts.append(f"IR 参考带：{'、'.join(band_texts)}")
            band_count = bands_payload.get("band_count")
            if band_count is None:
                band_count = reference_evidence.get("band_count")
            if band_count is not None:
                parts.append(f"参考带总数：{band_count}")
            if assignment_evidence:
                hit_count = assignment_evidence.get("key_band_hit_count")
                if hit_count is None:
                    hit_count = reference_evidence.get("hit_count")
                missing_count = assignment_evidence.get("key_band_missing_count")
                if missing_count is None:
                    missing_count = reference_evidence.get("missing_count")
                confidence = assignment_evidence.get("assignment_confidence")
                parts.append(
                    "命中情况："
                    f"hit={hit_count if hit_count is not None else 0}，"
                    f"missing={missing_count if missing_count is not None else 0}，"
                    f"confidence={confidence if confidence is not None else 'unknown'}"
                )
            if structure_evidence.get("paper_conclusion_ready") is not None:
                parts.append(f"论文候选：{'是' if bool(structure_evidence.get('paper_conclusion_ready')) else '否'}")
        else:
            parts.append("IR 参考带暂未加载，当前仅能依赖残差与峰稳定性调参。")
        return "；".join(parts) + "。"

    def _ir_strategy_hint(
        self,
        current_sample: dict[str, Any],
        knowledge: dict[str, Any],
        current_config: dict[str, Any],
        residual_pattern: dict[str, Any],
    ) -> str:
        params = current_sample.get("params", {}) if isinstance(current_sample, dict) else {}
        residual_type = residual_pattern.get("residual_type", "unknown") if isinstance(residual_pattern, dict) else "unknown"
        hints: list[str] = [
            "先按 baseline_method -> smooth_window -> peak_height_min / peak_prominence_min -> peak_distance -> lineshape 的顺序试。",
            "如果已经出现明显噪声，先增大 smooth_window；如果峰漏检，再降 peak_height_min 或 peak_prominence_min。",
        ]
        if "liquid" in str(current_config.get("sample_state", "")).lower():
            hints.append("液体样品通常先对 peak_distance 和 peak_height_min 更敏感。")
        if residual_type in {"baseline_drift_low_wn", "baseline_drift_high_wn", "baseline_drift", "background_drift"}:
            hints.append(f"残差类型为 {residual_type}：先调 baseline_method 或 normalization_method，暂时不要靠降低峰阈值抬高结论。")
        elif residual_type == "normalization_bias":
            hints.append("残差类型为 normalization_bias：优先比较 normalization_method，并检查强弱峰相对比例是否被扭曲。")
        elif residual_type in {"key_band_mismatch", "peak_mismatch"}:
            hints.append(f"残差类型为 {residual_type}：优先调 peak_fit_window_cm1，再小幅调整 peak_prominence_min 或 peak_height_min。")
        elif residual_type == "crowded_band_underfit":
            hints.append("残差类型为 crowded_band_underfit：优先调 peak_distance 或 lineshape，先分开拥挤峰再判断归属。")
        elif residual_type == "over_smoothed_weak_bands":
            hints.append("残差类型为 over_smoothed_weak_bands：先减小 smooth_window 或恢复弱峰，再重新检查关键带支撑。")
        elif residual_type in {"noise", "noise_dominant"}:
            hints.append("残差类型为 noise：先调大 smooth_window，再考虑阈值。")
        if params.get("n_peaks") and int(params.get("n_peaks", 0)) <= 2:
            hints.append("当前峰数偏少时，可先考虑 peak_distance 与 max_peaks，再动基线。")
        return "\n".join(f"- {hint}" for hint in hints)

    def _format_nmr_reference(self, knowledge: dict[str, Any]) -> str:
        nmr = knowledge.get("nmr", {}) if isinstance(knowledge, dict) else {}
        peaks = nmr.get("characteristic_peaks", []) or []
        peak_text: list[str] = []
        for peak in peaks:
            if not isinstance(peak, dict):
                continue
            ppm = peak.get("ppm") or peak.get("shift_ppm")
            if ppm is None:
                continue
            label = f"{ppm} ppm"
            if peak.get("assignment"):
                label += f" ({peak['assignment']})"
            peak_text.append(label)
        xc_range = nmr.get("xc_range")
        xc_part = f"；标准 Xc 范围：{xc_range[0]}-{xc_range[1]}%" if isinstance(xc_range, list) and len(xc_range) == 2 else ""
        return f"参考知识：{knowledge.get('name', 'unknown')} 的 NMR 参考峰位于 {', '.join(peak_text) if peak_text else '未提供'}{xc_part}。"

    def _nmr_strategy_hint(self, current_sample: dict[str, Any], knowledge: dict[str, Any], current_config: dict[str, Any]) -> str:
        params = current_sample.get("params", {}) if isinstance(current_sample, dict) else {}
        residual_type = (current_sample.get("residual_pattern", {}) or {}).get("residual_type", "unknown")
        hints = [
            "优先顺序：baseline_method -> peak_distance_ppm / peak_height_min -> deconvolution_method -> max_peaks。",
            "如果是基线漂移，先处理 baseline_method；如果是峰识别问题，先处理 peak_distance_ppm 和 peak_height_min。",
        ]
        if "liquid" in str(current_config.get("sample_state", "")).lower():
            hints.append("液体谱通常先看 peak_distance_ppm 和 peak_height_min。")
        if residual_type == "peak_mismatch":
            hints.append("残差类型为 peak_mismatch：避免先改与峰无关的预处理。")
        elif residual_type == "background_drift":
            hints.append("残差类型为 background_drift：baseline_method 是首要旋钮。")
        if params.get("n_peaks") and int(params.get("n_peaks", 0)) <= 2:
            hints.append("当前峰数偏少，可先考虑 max_peaks 或 peak_distance_ppm。")
        return "\n".join(f"- {item}" for item in hints)

    def format_history(self, rounds: list[Any]) -> str:
        if not rounds:
            return "（本轮为第一轮，无历史记录）"

        lines: list[str] = []
        for round_record in rounds:
            item = self._round_to_dict(round_record)
            idx = item.get("round_idx", item.get("round_num", "?"))
            accepted = bool(item.get("accepted", True))
            status = "✅ 有效（已保留）" if accepted else "❌ 无效（已回滚）"
            before = self._safe_float(item.get("r_squared_before", item.get("r_squared", 0.0)))
            after = self._safe_float(item.get("r_squared_after", item.get("r_squared", before)))
            changes = item.get("changes")
            if changes is None:
                advice = item.get("llm_advice") if isinstance(item.get("llm_advice"), dict) else {}
                changes = advice.get("changes", {})
            changes_text = self._json_dumps(changes or {}, sort_keys=True)
            target_symptom = str(item.get("target_symptom", "") or "").strip()
            symptom_summary = str(item.get("symptom_summary", "") or "").strip()
            rollback_detail = str(item.get("rollback_detail", "") or "").strip()
            parts = [f"Round {idx}: {status} | r²: {before:.4f} → {after:.4f} | 建议: {changes_text}"]
            if target_symptom:
                parts.append(f"target_symptom: {target_symptom}")
            if symptom_summary:
                parts.append(f"symptoms: {symptom_summary}")
            if rollback_detail and not accepted:
                parts.append(f"rollback: {rollback_detail}")
            lines.append(" | ".join(parts))
        return "\n".join(lines)

    def _format_history(self, rounds: list[Any]) -> str:
        return self.format_history(rounds)

    def _format_retrieved_cases(self, retrieved_cases: list[dict[str, Any]]) -> str:
        if not retrieved_cases:
            return "无历史案例。"

        blocks: list[str] = []
        for index, case in enumerate(retrieved_cases, start=1):
            metadata = case.get("metadata", {})
            if not isinstance(metadata, dict):
                metadata = {"value": metadata}
            blocks.append(
                "\n".join(
                    [
                        f"案例 {index}: {case.get('case_id', 'unknown')}",
                        f"相似度: {self._safe_float(case.get('score', 0.0)):.3f}",
                        f"元数据: {self._json_dumps(metadata, sort_keys=True)}",
                        f"内容: {case.get('document', '')}",
                    ]
                )
            )
        return "\n\n".join(blocks)

    def _default_tunable_params(self, technique: str, current_config: dict[str, Any]) -> list[dict[str, Any]]:
        maps = {
            "WAXS": WAXS_PARAM_MAP,
            "DSC": DSC_PARAM_MAP,
            "SAXS": SAXS_PARAM_MAP,
            "IR": IR_PARAM_MAP,
            "NMR": NMR_PARAM_MAP,
        }
        param_map = maps.get(technique.upper(), {})
        return [
            {
                "name": name,
                "config_field": rule.field_name,
                "current_value": current_config.get(rule.field_name),
                "type": rule.value_type.__name__,
                "constraint": list(rule.constraint) if rule.constraint is not None else [],
                "description": self._param_description(name),
            }
            for name, rule in param_map.items()
        ]

    def _format_tunable_params(self, tunable_params: list[dict[str, Any]]) -> str:
        if not tunable_params:
            return "当前技术暂无可调参数白名单。"

        lines = []
        for item in tunable_params:
            name = str(item.get("name"))
            description = item.get("description") or self._param_description(name)
            goal_priority = item.get("goal_priority")
            goal_reason = str(item.get("goal_priority_reason") or "").strip()
            goal_tags = item.get("goal_priority_goals") or item.get("goal_priority_tags")
            goal_tag_text = ""
            if isinstance(goal_tags, list) and goal_tags:
                goal_tag_text = ", ".join(str(entry).strip() for entry in goal_tags[:3] if str(entry).strip())
            joint_priority = item.get("joint_priority")
            joint_reason = str(item.get("joint_priority_reason") or "").strip()
            joint_families = item.get("joint_priority_families")
            joint_family_text = ""
            if isinstance(joint_families, list) and joint_families:
                joint_family_text = ", ".join(str(entry).strip() for entry in joint_families[:3] if str(entry).strip())
            lines.append(
                " | ".join(
                    [
                        f"name={name}",
                        f"field={item.get('config_field')}",
                        f"type={item.get('type')}",
                        f"current={self._json_dumps(item.get('current_value'))}",
                        f"constraint={self._json_dumps(item.get('constraint'))}",
                        f"goal_priority={goal_priority if goal_priority is not None else 0}",
                        f"goal_reason={goal_reason or 'None'}",
                        f"goal_tags={goal_tag_text or 'None'}",
                        f"joint_priority={joint_priority if joint_priority is not None else 0}",
                        f"joint_reason={joint_reason or 'None'}",
                        f"joint_families={joint_family_text or 'None'}",
                        f"description={description}",
                    ]
                )
            )
        return "\n".join(lines)

    def _param_description(self, name: str) -> str:
        descriptions = {
            "savgol_window": "SAXS 平滑窗口，优先级最高的噪声旋钮之一，必须为奇数。",
            "savgol_order": "SAXS Savitzky-Golay 多项式阶数，必须小于 savgol_window。",
            "q_bragg_min": "Bragg 峰搜索下限，只有峰位跑出窗口时才优先改。",
            "q_bragg_max": "Bragg 峰搜索上限，只有峰位跑出窗口时才优先改。",
            "q_corr_min": "相关/IDF 低 q 边界，更多影响结构参数。",
            "q_corr_max": "相关/IDF 高 q 边界，更多影响结构参数。",
            "idf_peak_rel_thresh": "IDF 峰阈值，通常在平滑和窗口合理后再调。",
            "idf_valley_rel_thresh": "IDF 谷阈值，通常在平滑和窗口合理后再调。",
            "tangent_lc_min_nm": "切线法晶片厚度下限，更多是物理保护项。",
            "lorentz_fit_method": "Lorentz 长周期拟合后端。",
            "baseline_type": "DSC 基线校正方式，背景漂移时优先。",
            "peak_function": "峰形函数。",
            "smooth_window": "平滑窗口。",
            "Tg_method": "Tg 识别方法。",
            "tm_search_low_C": "Tm 搜索窗口下限。",
            "tm_search_high_C": "Tm 搜索窗口上限。",
            "tc_search_low_C": "Tc 搜索窗口下限。",
            "tc_search_high_C": "Tc 搜索窗口上限。",
            "peak_prominence_ratio": "DSC 峰显著性阈值。",
            "min_event_enthalpy_Jg": "DSC 最小事件焓阈值。",
            "max_melting_peak_width_C": "DSC 最大熔融峰宽。",
            "baseline_method": "IR / NMR 基线方法。",
            "peak_height_min": "峰高阈值。",
            "peak_prominence_min": "峰显著性阈值。",
            "peak_distance": "最小峰间距。",
            "peak_fit_window_cm1": "IR 局部拟合窗口。",
            "wavenumber_min": "IR 波数下限。",
            "wavenumber_max": "IR 波数上限。",
            "normalization_method": "IR 归一化方式。",
            "lineshape": "IR 峰形函数。",
            "baseline_order": "NMR 基线多项式阶数。",
            "apodization": "NMR 加窗方式。",
            "lb_Hz": "NMR 线宽。",
            "gb": "NMR 高斯展宽系数。",
            "peak_distance_ppm": "NMR 峰间距。",
            "deconvolution_method": "NMR 去卷积峰形。",
            "max_peaks": "最大峰数。",
        }
        return descriptions.get(name, "")

    def _format_workspace_context(self, workspace_context: dict[str, Any] | None) -> str:
        if not isinstance(workspace_context, dict) or not workspace_context:
            return "None"

        parts: list[str] = []
        summary = str(workspace_context.get("summary") or "").strip()
        if summary:
            parts.append(summary)

        tuning_goal = str(workspace_context.get("tuning_goal_label") or workspace_context.get("tuning_goal") or "").strip()
        if tuning_goal:
            parts.append(f"Goal: {tuning_goal}")

        tuning_context = workspace_context.get("tuning_context")
        if isinstance(tuning_context, dict):
            tuning_parts: list[str] = []
            tuning_goal_ctx = str(tuning_context.get("tuning_goal_label") or tuning_context.get("tuning_goal") or "").strip()
            if tuning_goal_ctx:
                tuning_parts.append(f"goal={tuning_goal_ctx}")
            tuning_summary = str(tuning_context.get("summary") or "").strip()
            if tuning_summary:
                tuning_parts.append(f"summary={tuning_summary}")
            accepted = str(tuning_context.get("accepted_summary") or "").strip()
            if accepted:
                tuning_parts.append(f"accepted_summary={accepted}")
            stop_reason = str(tuning_context.get("stop_reason") or "").strip()
            if stop_reason:
                tuning_parts.append(f"stop_reason={stop_reason}")
            remaining_risks = str(tuning_context.get("remaining_risks") or "").strip()
            if remaining_risks:
                tuning_parts.append(f"remaining_risks={remaining_risks}")
            next_goal = str(tuning_context.get("next_goal") or "").strip()
            if next_goal:
                tuning_parts.append(f"next_goal={next_goal}")
            history = tuning_context.get("history")
            if isinstance(history, list) and history:
                accepted_rounds = 0
                rolled_back_rounds = 0
                rollback_reasons: list[str] = []
                best_round = None
                best_r2 = None
                for item in history:
                    if not isinstance(item, dict):
                        continue
                    round_num = int(item.get("round_num", item.get("round_idx", 0)) or 0)
                    if round_num <= 0:
                        continue
                    if bool(item.get("accepted", True)):
                        accepted_rounds += 1
                    else:
                        rolled_back_rounds += 1
                        advice = item.get("llm_advice") if isinstance(item.get("llm_advice"), dict) else {}
                        rollback_reason = str(advice.get("rollback_reason") or "").strip()
                        if rollback_reason and rollback_reason not in rollback_reasons:
                            rollback_reasons.append(rollback_reason)
                    try:
                        r2_value = float(item.get("r_squared_after", item.get("r_squared", "")))
                    except (TypeError, ValueError):
                        continue
                    if best_r2 is None or r2_value > best_r2:
                        best_r2 = r2_value
                        best_round = round_num
                benchmark_summary = tuning_context.get("benchmark_summary") if isinstance(tuning_context.get("benchmark_summary"), dict) else {}
                baseline_hint = ""
                if isinstance(benchmark_summary, dict) and benchmark_summary:
                    try:
                        delta = float(benchmark_summary.get("average_objective_delta") or 0.0)
                        sign = "+" if delta > 0 else ""
                        baseline_hint = f"{sign}{delta:.3f}"
                    except (TypeError, ValueError):
                        baseline_hint = ""
                chain_bits = [
                    f"baseline delta {baseline_hint or 'N/A'}",
                    f"accepted {accepted_rounds} rounds, rolled back {rolled_back_rounds} rounds",
                ]
                if best_round is not None:
                    chain_bits.append(f"best candidate round {best_round}")
                if rollback_reasons:
                    chain_bits.append(f"remaining risks: {'; '.join(rollback_reasons[:2])}")
                tuning_parts.append(f"chain={' | '.join(chain_bits)}")
            if tuning_parts:
                parts.append("Tuning context: " + " | ".join(tuning_parts[:7]))

        joint_ai_context = workspace_context.get("joint_ai_context")
        if isinstance(joint_ai_context, dict):
            joint_parts: list[str] = []
            joint_summary = str(joint_ai_context.get("summary") or "").strip()
            if joint_summary:
                joint_parts.append(f"summary={joint_summary}")
            scope = str(joint_ai_context.get("scope") or "").strip()
            if scope:
                joint_parts.append(f"scope={scope}")
            families = joint_ai_context.get("issue_families")
            if isinstance(families, list) and families:
                family_text = ", ".join(str(item).strip() for item in families[:3] if str(item).strip())
                if family_text:
                    joint_parts.append(f"issue_families={family_text}")
            issue_count = joint_ai_context.get("issue_count")
            warning_count = joint_ai_context.get("warning_count")
            error_count = joint_ai_context.get("error_count")
            if issue_count is not None:
                joint_parts.append(f"issues={issue_count}")
            if warning_count is not None:
                joint_parts.append(f"warnings={warning_count}")
            if error_count is not None:
                joint_parts.append(f"errors={error_count}")
            if joint_parts:
                parts.append("Cross-tech context: " + " | ".join(joint_parts[:6]))
            highlights = joint_ai_context.get("highlights")
            if isinstance(highlights, list):
                highlight_lines = [
                    f"- {str(item).strip()}"
                    for item in highlights[:3]
                    if str(item).strip()
                ]
                if highlight_lines:
                    parts.append("\n".join(["Cross-tech highlights:"] + highlight_lines))

        joint_report = workspace_context.get("joint_report")
        if isinstance(joint_report, dict):
            joint_summary = str(joint_report.get("summary") or "").strip()
            if joint_summary:
                parts.append(f"Joint report: {joint_summary}")
            rows = joint_report.get("rows") if isinstance(joint_report.get("rows"), list) else []
            validations = joint_report.get("validations") if isinstance(joint_report.get("validations"), list) else []
            if rows or validations:
                parts.append(f"Joint rows={len(rows)}, validations={len(validations)}")

        work_memory = workspace_context.get("work_memory")
        if isinstance(work_memory, dict):
            detail = str(work_memory.get("detail") or "").strip()
            if detail:
                parts.append(f"Work memory: {detail}")
            slices = work_memory.get("slices") if isinstance(work_memory.get("slices"), list) else []
            for item in slices[:2]:
                if not isinstance(item, dict):
                    continue
                label = str(item.get("label") or "").strip()
                piece = str(item.get("detail") or "").strip()
                if label or piece:
                    parts.append(f"{label}: {piece}" if label and piece else (label or piece))

        current_result = workspace_context.get("current_result")
        if isinstance(current_result, dict):
            summary_text = self._result_summary_text(current_result)
            if summary_text:
                parts.append(f"Current result: {summary_text}")

        if not parts:
            return "None"
        return "\n".join(parts[:6])

    def _append_workspace_context(self, prompt: str, workspace_context: dict[str, Any] | None) -> str:
        context_text = self._format_workspace_context(workspace_context)
        if not context_text or context_text == "None":
            return prompt
        return f"{prompt}\n\n## Workspace context\n{context_text}"

    def _append_analysis_evidence(self, prompt: str, current_sample: dict[str, Any]) -> str:
        evidence = current_sample.get("analysis_evidence", {})
        if not isinstance(evidence, dict) or not evidence:
            return prompt
        compact = self._compact_analysis_evidence(evidence)
        if not compact:
            return prompt
        evidence_text = self._json_dumps(compact, indent=2)
        symptom_bridge = self._format_symptom_bridge(compact)
        allowed_actions = current_sample.get("allowed_actions", [])
        allowed_changes = current_sample.get("allowed_changes", {})
        action_names = {
            str(item.get("name", "") or "").strip()
            for item in allowed_actions
            if isinstance(item, dict)
        } if isinstance(allowed_actions, list) else set()
        symptoms = evidence.get("symptoms", [])
        symptom_names = {
            str(item.get("name", "") or "").strip()
            for item in symptoms
            if isinstance(item, dict)
        } if isinstance(symptoms, list) else set()
        preprocessing_requested = bool(action_names & PREPROCESS_ACTION_NAMES) or any(
            token in name
            for name in symptom_names
            for token in ("baseline", "background", "noise", "smooth")
        )
        contract = [
            "## Core evidence",
            evidence_text,
            "",
        ]
        if symptom_bridge:
            contract.extend(
                [
                    symptom_bridge,
                    "",
                ]
            )
        if isinstance(allowed_actions, list) and allowed_actions:
            contract.extend(
                [
                    "## Allowed actions",
                    self._json_dumps(allowed_actions[:6], indent=2),
                    "",
                ]
            )
        if isinstance(allowed_changes, dict) and allowed_changes:
            contract.extend(
                [
                    "## Allowed changes",
                    self._json_dumps(allowed_changes, indent=2),
                    "",
                ]
            )
        contract.extend(
            [
                "## Response contract",
                "- diagnosis: a short diagnosis label for the current evidence failure mode.",
                "- Hypothesis: one sentence tying the change to the observed symptom.",
                "- target_symptom: the concrete evidence failure mode to address.",
                "- recommended_actions: choose 1-2 actions from the allowed action list when present.",
                "- allowed_changes: choose only from the whitelist.",
                "- changes: provide only the concrete parameter deltas needed by the chosen action; keep it empty when the right next step is a non-parameter action.",
                "- expected_evidence_change: describe which evidence fields should improve or stabilize.",
                "- rollback_condition: state what would invalidate the suggestion.",
                "- Keep the final answer as strict JSON and include the evidence-aware fields.",
                "",
                "## Boundary",
                "- core provides the evidence pack; AI must not override it with free-form intuition.",
                "- AI may only propose a small whitelist-constrained action hypothesis.",
                "- orchestrator decides accept / rollback from the evidence and guards.",
                "- the user keeps the final scientific judgment.",
            ]
        )
        if preprocessing_requested:
            technique = str(current_sample.get("technique", "") or "").strip().upper()
            policy = get_preprocess_policy(technique)
            protected_features = self._json_dumps(list(policy.allowed_protected_features))
            protection_instruction = (
                "For SAXS, include every listed protected feature; omitting one is invalid."
                if technique == "SAXS"
                else "Include protected features from this policy list."
            )
            contract.extend(
                [
                    "",
                    "## Preprocessing intent contract",
                    "For a baseline or smoothing action, include this exact object shape:",
                    "{",
                    '  "preprocess_intent": {',
                    '    "schema_version": "1.0",',
                    '    "analysis_id": "current case_id",',
                    f'    "technique": "{technique}",',
                    f'    "target": "{" | ".join(policy.allowed_targets)}",',
                    f'    "direction": "{" | ".join(policy.allowed_directions)}",',
                    f'    "desired_effect": "{" | ".join(policy.allowed_effects)}",',
                    f'    "protected_features": {protected_features},',
                    '    "target_symptoms": ["observed Core symptom names"],',
                    '    "rationale_code": "short stable code",',
                    '    "human_summary": "short explanation"',
                    "  }",
                    "}",
                    "desired_effect is qualitative; Core maps it to bounded numeric candidates.",
                    protection_instruction,
                    "Do not place baseline or smoothing parameters in changes; keep those changes empty.",
                ]
            )
        return f"{prompt}\n\n" + "\n".join(contract)

    def _format_symptom_bridge(self, compact_evidence: dict[str, Any]) -> str:
        lines = []

        structured = compact_evidence.get("symptoms", [])
        if isinstance(structured, list):
            for item in structured[:4]:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name", "") or "").strip()
                summary = str(item.get("summary", "") or "").strip()
                targets = item.get("target_params", [])
                target_text = ""
                if isinstance(targets, list):
                    cleaned = [str(target).strip() for target in targets if str(target).strip()]
                    if cleaned:
                        target_text = " -> " + " / ".join(cleaned[:4])
                if name and summary:
                    lines.append(f"- {name}: {summary}{target_text}")

        symptoms = compact_evidence.get("actionable_symptoms", [])
        if isinstance(symptoms, list):
            for item in symptoms[:4]:
                text = str(item).strip()
                if text:
                    lines.append(f"- {text}")

        deduped = list(dict.fromkeys(lines))
        if not deduped:
            return ""
        return "\n".join(["## Symptom bridge", *deduped[:6]])

    def _compact_analysis_evidence(self, evidence: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(evidence, dict) or not evidence:
            return {}

        compact: dict[str, Any] = {}
        preferred_keys = (
            "summary",
            "fit_evidence",
            "physical_evidence",
            "residual_evidence",
            "feature_evidence",
            "signal_evidence",
            "peak_evidence",
            "reference_evidence",
            "background_evidence",
            "phase_evidence",
            "transform_evidence",
            "structure_evidence",
            "batch_evidence",
            "condition_evidence",
            "stability_evidence",
            "symptoms",
            "risk_flags",
            "confidence_signals",
            "actionable_symptoms",
            "constraint_summary",
            "constraints",
            "cross_validation",
            "source_fields",
        )
        for key in preferred_keys:
            value = evidence.get(key)
            if value in (None, "", [], {}):
                continue
            compact[key] = self._truncate_evidence_value(value, limit=4)

        if "summary" not in compact:
            summary_bits = []
            for key in ("technique", "summary"):
                value = evidence.get(key)
                if value:
                    summary_bits.append(str(value))
            if summary_bits:
                compact["summary"] = " | ".join(summary_bits)

        return compact

    def _truncate_evidence_value(self, value: Any, limit: int = 4) -> Any:
        if is_dataclass(value):
            value = asdict(value)
        if isinstance(value, dict):
            out: dict[str, Any] = {}
            for index, (key, item) in enumerate(value.items()):
                if index >= limit:
                    break
                out[key] = self._truncate_evidence_value(item, limit=limit)
            return out
        if isinstance(value, list):
            return [self._truncate_evidence_value(item, limit=limit) for item in value[:limit]]
        return value

    def _result_summary_text(self, result: dict[str, Any]) -> str:
        if not isinstance(result, dict) or not result:
            return ""

        parts: list[str] = []
        params = result.get("parameters") if isinstance(result.get("parameters"), dict) else {}
        results_summary = result.get("results_summary") if isinstance(result.get("results_summary"), dict) else {}
        if params:
            interesting = []
            for key in ("r_squared", "L_nm", "Tm_peak_C", "Xc_pct", "lc_nm", "D_Scherrer_nm", "n_peaks", "quality_score"):
                if key in params:
                    interesting.append(f"{key}={params.get(key)}")
            if interesting:
                parts.append(", ".join(interesting[:4]))
        if results_summary:
            summary_bits = []
            for key in ("project_label", "result_origin", "status", "r2", "confirmed", "ai_tuned"):
                if key in results_summary:
                    summary_bits.append(f"{key}={results_summary.get(key)}")
            if summary_bits:
                parts.append(", ".join(summary_bits))
        tuning_context = result.get("tuning_context")
        if isinstance(tuning_context, dict):
            tuning_bits = []
            for key in ("summary", "accepted_summary", "stop_reason", "remaining_risks", "next_goal"):
                value = str(tuning_context.get(key) or "").strip()
                if value:
                    tuning_bits.append(f"{key}={value}")
            if tuning_bits:
                parts.append("tuning_context: " + " | ".join(tuning_bits[:4]))
        if results_summary:
            status_bits = []
            for key in ("confirmed", "ai_tuned"):
                value = results_summary.get(key)
                if value is not None:
                    status_bits.append(f"{key}={value}")
            if status_bits:
                parts.insert(0, "result_state: " + ", ".join(status_bits))
        return " | ".join(parts)

    def _format_xc_range(self, knowledge: dict[str, Any], technique: str = "WAXS") -> str:
        section_name = "dsc" if technique.upper() == "DSC" else "waxs"
        section = knowledge.get(section_name, {}) if isinstance(knowledge, dict) else {}
        xc_range = section.get("xc_range")
        if isinstance(xc_range, list) and len(xc_range) == 2:
            return f"{xc_range[0]}-{xc_range[1]}%"
        return "未提供"

    def _format_reference_features(self, knowledge: dict[str, Any], technique: str = "WAXS") -> str:
        if technique.upper() == "DSC":
            dsc = knowledge.get("dsc", {}) if isinstance(knowledge, dict) else {}
            parts = []
            if dsc.get("tm") is not None:
                parts.append(f"Tm≈{dsc['tm']}°C")
            if dsc.get("tc") is not None:
                parts.append(f"Tc≈{dsc['tc']}°C")
            if dsc.get("delta_hm_100") is not None:
                parts.append(f"ΔHm0={dsc['delta_hm_100']} J/g")
            return "、".join(parts) if parts else "未提供"
        return self._format_characteristic_peaks(knowledge)

    def _format_characteristic_peaks(self, knowledge: dict[str, Any]) -> str:
        waxs = knowledge.get("waxs", {}) if isinstance(knowledge, dict) else {}
        peaks = waxs.get("characteristic_peaks", [])
        parts = []
        for peak in peaks:
            theta = peak.get("two_theta")
            if theta is None:
                continue
            phase = peak.get("crystal_phase", "")
            hkl = peak.get("hkl", "")
            label = f"{theta}°"
            if phase:
                label += f"({phase})"
            if hkl:
                label += f"[{hkl}]"
            parts.append(label)
        return "、".join(parts) if parts else "未提供"

    def _format_ir_band_group(
        self,
        bands: list[dict[str, Any]],
        wavenumbers: Any,
        *,
        limit: int | None = None,
    ) -> str:
        if not isinstance(bands, list) or not bands:
            return ""
        targets: set[int] = set()
        if isinstance(wavenumbers, list):
            for item in wavenumbers:
                value = self._clean_numeric(item)
                if value is not None:
                    targets.add(int(round(value)))
        texts: list[str] = []
        for band in bands:
            if not isinstance(band, dict):
                continue
            value = self._clean_numeric(band.get("wavenumber"))
            if value is None:
                continue
            if targets and int(round(value)) not in targets:
                continue
            texts.append(self._format_ir_band_text(band))
            if limit is not None and len(texts) >= limit:
                break
        return "、".join([text for text in texts if text])

    def _format_ir_band_text(self, band: dict[str, Any]) -> str:
        value = self._clean_numeric(band.get("wavenumber"))
        if value is None:
            return ""
        label = f"{int(round(value))} cm^-1"
        details: list[str] = []
        assignment = str(band.get("assignment", "") or "").strip()
        if assignment:
            details.append(assignment)
        phase = str(band.get("phase", "") or "").strip()
        if phase:
            details.append(f"{phase} phase")
        strength = str(band.get("strength", "") or "").strip()
        if strength:
            details.append(strength)
        if details:
            label += f" ({'，'.join(details)})"
        return label

    def _join_text_items(self, values: Any) -> str:
        if not isinstance(values, list):
            return ""
        parts = [str(item or "").strip() for item in values if str(item or "").strip()]
        return "；".join(parts)

    def _clean_numeric(self, value: Any) -> float | None:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if number != number:
            return None
        return number

    def _extract_xc(self, params: dict[str, Any]) -> str:
        value = self._extract_xc_value(params)
        if value is None:
            return "unknown"
        return f"{value:.1f}%"

    def _extract_xc_value(self, params: dict[str, Any]) -> float | None:
        if not isinstance(params, dict):
            return None
        for key in ("Xc_pct", "xc", "Xc", "crystallinity_pct", "crystallinity"):
            value = params.get(key)
            if value is None:
                continue
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
        return None

    def _strategy_hint(
        self,
        knowledge: dict[str, Any],
        params: dict[str, Any],
        current_config: dict[str, Any],
        residual_pattern: dict[str, Any],
        technique: str = "WAXS",
    ) -> str:
        technique_name = str(technique or "").upper()
        if technique_name == "DSC":
            return self._dsc_strategy_hint(knowledge, params, current_config, residual_pattern)
        if technique_name == "SAXS":
            return self._saxs_strategy_hint(knowledge, params, current_config, residual_pattern)
        if technique_name == "IR":
            return self._ir_strategy_hint({"params": params}, knowledge, current_config, residual_pattern)
        if technique_name == "NMR":
            return self._nmr_strategy_hint({"params": params, "residual_pattern": residual_pattern}, knowledge, current_config)

        waxs = knowledge.get("waxs", {}) if isinstance(knowledge, dict) else {}
        xc_range = waxs.get("xc_range")
        current_xc = self._extract_xc_value(params)
        residual_type = residual_pattern.get("residual_type", "unknown") if isinstance(residual_pattern, dict) else "unknown"
        hints = [
            "1. 先调峰形函数：peak_function 通常是 WAXS 最先尝试的旋钮。",
            "2. 再看平滑与峰数：smooth_window 和 max_peaks 影响峰的可见度与过拟合。",
            "3. 背景异常时再动 background_method 或 amorphous_subtraction。",
        ]
        if residual_type == "peak_mismatch":
            hints.append("残差类型为 peak_mismatch：先检查 peak_function 与 peak_distance。")
        elif residual_type == "background_drift":
            hints.append("残差类型为 background_drift：先处理 background_method。")
        elif residual_type == "noise":
            hints.append("残差类型为 noise：先检查 smooth_window 是否足够。")
        if current_xc is not None and isinstance(xc_range, list) and len(xc_range) == 2:
            low, high = float(xc_range[0]), float(xc_range[1])
            if current_xc > high:
                hints.append("当前 Xc 偏高：优先检查基线扣除或峰面积过大。")
            elif current_xc < low:
                hints.append("当前 Xc 偏低：优先检查弱峰漏检或积分区间不足。")
            else:
                hints.append("当前 Xc 在参考范围内：优先围绕残差最大区域微调。")
        return "\n".join(f"- {hint}" for hint in hints)

    def _round_to_dict(self, round_record: Any) -> dict[str, Any]:
        if isinstance(round_record, dict):
            return round_record
        if is_dataclass(round_record):
            return asdict(round_record)
        return {
            "round_idx": getattr(round_record, "round_idx", getattr(round_record, "round_num", "?")),
            "accepted": getattr(round_record, "accepted", True),
            "r_squared_before": getattr(round_record, "r_squared_before", getattr(round_record, "r_squared", 0.0)),
            "r_squared_after": getattr(round_record, "r_squared_after", getattr(round_record, "r_squared", 0.0)),
            "changes": getattr(round_record, "changes", {}),
            "llm_advice": getattr(round_record, "llm_advice", {}),
            "target_symptom": getattr(round_record, "target_symptom", ""),
            "symptom_summary": getattr(round_record, "symptom_summary", ""),
            "rollback_detail": getattr(round_record, "rollback_detail", ""),
        }

    def _metric(self, params: dict[str, Any], key: str, precision: int = 1) -> str:
        if not isinstance(params, dict):
            return "unknown"
        value = params.get(key)
        if value is None:
            for item in params.values():
                if isinstance(item, dict) and key in item:
                    value = item[key]
                    break
        if value is None:
            return "unknown"
        try:
            return f"{float(value):.{precision}f}"
        except (TypeError, ValueError):
            return str(value)

    def _json_dumps(self, value: Any, **kwargs: Any) -> str:
        options = {"ensure_ascii": False, "sort_keys": True, "default": str}
        options.update(kwargs)
        return json.dumps(value, **options)

    def _get_residual_summary(self, current_sample: dict[str, Any], fallback: str) -> str:
        for key in ("residuals_pattern", "residual_pattern"):
            value = current_sample.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, dict):
                for field in ("summary", "text", "description"):
                    text = value.get(field)
                    if text:
                        return str(text)
        residuals = current_sample.get("residuals_pattern")
        if residuals:
            return str(residuals)
        return fallback

    def _safe_float(self, value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
