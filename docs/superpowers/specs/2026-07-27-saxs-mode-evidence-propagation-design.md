# SAXS 静态/变温/应变证据传播设计

日期：2026-07-27
状态：阶段 4 设计
关联 Goal：建立可解释、可验证、可降级的 PolyNexus SAXS 数据质量与分析体系

## 1. 目标

阶段 3 已让单帧 `SAXSResult` 同时携带 Guinier 和 1D 方法族证据。本阶段把
这些证据完整传播到变温 `TemperaturePointResult` 和应变
`StrainPointResult`，使每个观测帧都能说明“哪些指标可用、证据等级如何、
为什么降级”。静态模式继续使用 `SAXSResult` 作为单帧载体。

## 2. 模式边界

三种模式共享数据质量和方法证据字典，但不共享科学解释：

- 静态：单帧结构参数和方法证据；
- 变温：保留温度相变、峰演化和已有 Guinier 序列证据；不把温度趋势升级
  为单帧定量；
- 应变：保留 Q*、取向、空洞和应变相位；不把取向或空洞判据塞进通用
  `MetricEvidence`，也不把应变轴当温度轴排序。

本阶段不插值、不合并、不平滑、不删除失败帧，不改变既有序列数组和发布
角色。分析异常只会留下该帧的 `None`/`Unusable` 证据，帧数量仍与输入一致。

## 3. 契约与接入

`TemperaturePointResult.metric_evidence` 和 `StrainPointResult.metric_evidence`
均为可选的 JSON-safe 字典，内容是对应 `SAXSResult.metric_evidence` 的
逐帧快照；同时传播 `data_quality_report`。两类 `to_dataframe()` 增加一个
紧凑的 `Metric_evidence_levels` 摘要列，不改变已有列名或数值列。

传播只发生在各自已有的 `analyze_single` 成功分支中：

1. `getattr(saxs_result, "metric_evidence", None)` 读取公共 DTO；
2. 失败帧维持 `None`，不从邻帧复制；
3. 温度/应变专用指标继续由各自模块计算并保持原字段；
4. 序列级趋势只在已有温度 builder 中生成，应变不调用温度序列 builder。

## 4. 测试与验收

使用 fake `SAXSResult` 的传播测试覆盖：两种模式的成功帧、核心失败帧、
空证据兼容旧消费者、帧数量/顺序保持、DataFrame 摘要列和严格 JSON。再跑
现有温度/应变/完整 SAXS 回归、结构化 verifier、quality/preprocessing gates
和原子 checkpoint。真实相变/应变科学阈值、2D 误差传播、AI 和发布验收仍
属于后续阶段。
