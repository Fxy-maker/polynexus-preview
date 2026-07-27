# SAXS 序列级救援与相变感知验证设计

日期：2026-07-27
状态：阶段 6 设计与实现中

## 目标

把变温 SAXS 已经完成的确定性 `lc` 序列路径选择包装成可追溯的救援候选，并为候选提供显式的重新分析验证报告。候选可以帮助用户保留可用信息，但不能创造缺失温度帧、覆盖原始 q-I 数据或绕过物理门槛。

## 范围与非目标

- 复用现有 `RescueCandidate`、`RescueValidationReport` 和 `lc_path_selection`。
- 只暴露已有替代方法（如 tangent、IDF、gamma-min）选出的路径。
- 缺失、无有效替代指标或 primary 路径已经 usable 的帧不生成候选。
- 不排序、插值、删除或补造温度帧；不改变既有 `lc_nm`、`Rg`、Q* 和相变判断。
- 不在本阶段引入 AI，也不新增未经校准的取向、相变或连续性硬阈值。

## 设计

`build_sequence_rescue_candidates()` 接受温度点对象或映射，读取现有路径选择结果，生成 JSON-safe 的 deterministic `RescueCandidate`。候选参数包含帧位置、温度、原始值、建议值、建议来源、路径状态、`preserve_missing_frames=True` 和 `apply_mode="candidate_only"`，因此下游不会把候选误当成已经应用的结果。

`validate_sequence_rescue_candidate()` 只接受调用方显式提供的四个门槛：hard gate、physical gate、data preservation 和 sequence gate。四者全部通过才产生 accepted，否则 deterministic rejection reasons 进入 `RescueValidationReport`。该函数不执行候选、不修改点对象，也不把 soft score 当作接受条件。

`TempSeriesResult` 保存 `sequence_rescue_candidates`，并在 DataFrame 中按帧暴露候选 ID。缺失帧仍保持缺失；候选结果只用于审计、人工确认和后续 AI shadow 输入。

## 验收

1. 替代路径候选保留原帧数值且参数严格 JSON-safe。
2. usable primary 帧和缺失帧不产生伪造候选。
3. 任意一个硬门槛失败都会拒绝候选；soft score 不能绕过门槛。
4. 温度结果和表格能引用候选 ID，既有分析回归不变。

## 后续边界

真正的候选重新分析、跨指标物理门槛校准、相变附近人工科学审查、AI shadow/confirm 和 Figure/Workbench 发布资格属于后续阶段。
