# SAXS AI 救援桥接设计

日期：2026-07-27
状态：阶段 7 设计与实现中

## 目标

把 SAXS 质量/序列证据接入现有 `preprocess_optimization` 合同，使 AI 只能提出经过 schema 和 SAXS 保护字段校验的 preprocessing intent/candidate；候选仍必须经过现有证据硬门槛，默认只运行 shadow。

## 设计边界

- 复用 `PreprocessIntent`、`PreprocessCandidate`、`PreprocessEvidence`、`DecisionOutcome`、`SAXSPreprocessAdapter` 和 `PreprocessPolicy`。
- AI 输入只作为不可信 intent payload 解析，不能决定 technique、保护字段、automation policy 或直接修改配置。
- 强制保护 `weak_peaks`、`integrated_area`、`guinier_region`、`beamstop_boundaries`、`peak_position`、`peak_width`、`physical_parameters`。
- 计划对象明确 `candidate_only`、`original_preserved` 和 `physical_validation_required`。
- `shadow` 始终保留原始配置；`confirm_only` 只能返回用户确认请求；`tiered_auto` 只有配置 policy 明确 calibrated 且所有现有 hard guards 通过时才暴露 `apply_allowed=True`。

## 数据流

`AI intent payload → parse/validate → SAXS policy + adapter → deterministic candidates → candidate rerun evidence → existing decision engine → auditable SAXS decision`。

本阶段不调用模型、不执行候选配置、不改变 SAXS 数值计算。候选重算、物理指标漂移和序列证据仍由调用方提供 `PreprocessEvidence`；缺失证据会触发原有 hard guard 拒绝。

## 验收

1. 非 SAXS 或缺失保护字段的 intent 被拒绝。
2. 合法 intent 只能生成 SAXS policy 允许的 bounded candidates，并保留 candidate-only 标记。
3. 默认 shadow 的真实决策为 `keep_original`，即使模拟决策为 auto_accept。
4. confirm-only 返回 `request_confirmation`；未校准 tiered-auto 不能启用；已校准且硬门槛全过才允许 `apply_allowed`。
5. 既有 preprocessing 和完整 SAXS 回归不变。

## 后续

真实模型调用、用户确认 UI、候选重算执行器、经验校准和 Workbench/Figure 审计属于后续产品闭环阶段。
