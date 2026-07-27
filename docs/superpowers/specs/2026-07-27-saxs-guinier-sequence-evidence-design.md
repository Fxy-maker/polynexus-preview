# SAXS 变温 Guinier 序列证据设计

日期：2026-07-27
状态：阶段 2 设计
关联 Goal：建立可解释、可验证、可降级的 PolyNexus SAXS 数据质量与分析体系

## 1. 目标与边界

阶段 1 已为每个变温 1D 帧生成独立的 `GuinierEvidence`。本阶段只增加
序列级证据，回答“已有帧之间是否足以支持一个 Rg 趋势观察”，不改变任何
单帧 Rg、Guinier 拟合窗口或层片物理量。

本阶段不插值缺失帧、不删除异常帧、不把相变区的真实突变判为错误、不自动
修改输入曲线，也不接入 AI 救援或 GUI 发布角色。

## 2. 方案选择

采用“质量契约 + 变温结果接入”的纵向闭环。只做独立统计函数会让结果无法
被后续 Workbench/Manifest 使用；直接加入 AI/自动救援又会绕过尚未定义的候选
验证边界。序列 DTO 作为中间层，可以先验证证据传播，再复用到 Porod、Kratky
和其他模式。

## 3. 数据契约

新增不可变 `GuinierSequenceEvidence`，至少包含：

- 输入帧数、具有有限温度的帧数、具有可用于趋势的 Rg 帧数；
- `missing_frame_indices`、`diagnostic_frame_indices`、无效温度和重复温度位置；
- 连续性断点位置及可审计的相邻变化统计；
- 温度范围、Rg 范围、`QualityLevel` 和去重后的 reason codes；
- `MetricEvidence(metric_name="Rg_sequence")`，引用来源和帧数证据。

`build_guinier_sequence_evidence(temperatures, frame_evidence, ...)` 接受
只读输入。可用帧必须同时有有限正 Rg 且单帧等级为 `Quantitative` 或
`Trend`；`Diagnostic`/`Unusable` 帧只能作为缺失或诊断统计，不能进入趋势
数组。输入长度不一致、非有限温度或重复温度都会保留原位置并生成原因码。

序列等级规则固定为：

- `Unusable`：没有可用于趋势的帧；
- `Diagnostic`：只有一个可用帧，或温度轴存在无效/重复条件；
- `Trend`：至少两个可用帧且温度轴有效。存在缺失帧或连续性断点时仍保留
  `Trend`，但必须带 reason code，不得假装数据完整；
- 本阶段不生成序列级 `Quantitative`，避免把趋势观察误称为单帧定量结果。

连续性检查只产生诊断证据。对按输入顺序排列的相邻可用 Rg 使用相对变化，
在至少四个可用帧时用稳健的中位数/MAD 标记孤立的大变化；它不会修改序列、
降级真实突变，也不会替代相变模型。连续的单调变化不应被标记为孤立异常。

## 4. 结果接入与失败处理

`TempSeriesResult` 增加 `guinier_sequence_evidence` 字典。变温分析完成逐帧
处理后调用契约构造器，并保留原始排序后的帧位置。`TemperaturePointResult`
保持现有逐帧证据不变。`to_dataframe()` 只增加重复的序列等级/原因摘要列，
不改变现有列名、帧顺序或数值。

分析异常时序列构造器收到 `None`，该帧进入缺失统计；温度帧数量仍与输入
一致。构造器本身不得抛出 NumPy/JSON 特殊值，所有输出必须通过现有
`contract_json` 严格序列化。

## 5. 测试与验收

focused regression 覆盖：干净多帧趋势、缺失/失败帧、重复温度、无效温度、
孤立跳变、连续真实变化、单帧和空序列，以及严格 JSON 序列化。变温回归验证
序列摘要实际挂载到 `TempSeriesResult`，且缺失帧没有被生成。

阶段门槛是 focused tests、完整 SAXS 回归、结构化 verifier、`git diff --check`
和原子 checkpoint。阶段完成后仍需人工科学审查，才能决定连续性统计是否可
作为下一阶段救援候选的输入。
