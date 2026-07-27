# SAXS 1D 方法族证据设计

日期：2026-07-27
状态：阶段 3 设计
关联 Goal：建立可解释、可验证、可降级的 PolyNexus SAXS 数据质量与分析体系

## 1. 目标与保守边界

阶段 1/2 已经为 Guinier 单帧和变温序列建立了质量、适用性、物理检查和
分级基础。本阶段把现有 Porod、Kratky、Porod invariant（`Q*`）和层片
结构参数接入同一 `MetricEvidence` 形状，先形成可追溯的证据面，不重写
现有数值算法。

本阶段采用保守科学语义：只使用现有配置 q 范围、已有点数/有限值检查和
现有 `SAXSResult` 质量字段；不新增未经实验确认的 `slope≈-4`、Kratky
形状或方法间一致性硬阈值。方法特有的偏离只作为 `fit_evidence`、
`physical_checks` 和 reason code。为避免把尚未校准的方法证据包装成定量
结论，新增方法证据的最高等级暂为 `Trend`；阶段 4/真实数据审查后再决定
是否开放方法级 `Quantitative`。

## 2. 统一契约

`SAXSResult.metric_evidence` 是严格 JSON-safe 的字典，键为 `porod`、
`kratky`、`invariant`、`lamellar`，每个值是 `MetricEvidence.to_dict()`。
现有 `result.porod`、`result.kratky`、`result.structure` 和质量字段保持
兼容，GUI 不直接读取算法内部状态。

每个 builder 都接收现有结果、`DataQualityReport`、显式适用性上下文和
`source_ref`，只读输入并输出：数值/单位、拟合统计、物理检查、不确定度
（当前没有可靠估计时为 `None`）、风险码、来源和等级。

适用性规则与 Guinier 一致：`supported` 才可进入 `Trend`；`unknown` 或
`unsupported` 最高为 `Diagnostic`。数据质量 `Unusable` 时指标为
`Unusable`；数值缺失或点数不足时保留原因，不伪造数值。

## 3. 方法特有证据

- Porod：使用现有 `q_porod`/`Iq4`/`Kp`/`slope`，记录 q 范围、点数、
  Iq⁴ 平台中位数和离散度、相对理想斜率 `-4` 的偏差；偏差只作风险，
  不用新阈值自动拒绝。
- Kratky：使用现有 `q`、`kratky`、`kratky_norm` 和 `q_peak_kratky`，
  记录有限点数、峰是否存在、峰位置及归一化峰值；不自动声明 folded/
  unfolded/globular 形状。
- Invariant：使用 `StructureParams.Q_invariant` 和现有 `Q_star_valid`，
  记录正值/有限值检查、beamstop 污染状态和来源；不重新计算积分。
- Lamellar：使用 `LongPeriodResult`/`StructureParams` 的 L、lc、la、
  phi_c、confidence 和已有方法来源，记录正值、范围和缺失字段；不重做
  Bragg/Lorentz/correlation/IDF 投票。

## 4. 接入与失败处理

`analyze_single` 在现有 Porod/Kratky/structure 结果就绪后构造四项证据，
再进入既有 `validate_saxs_results`。任何 builder 异常都降级为带
`metric_evidence_build_failed` 的 `Diagnostic/Unusable` 条目，不能阻断
原有分析结果，也不能生成 NaN JSON。变温/应变本阶段只继承单帧结果中的
证据字典；序列级融合另有任务卡。

## 5. 测试与阶段门槛

focused tests 覆盖每个 builder 的 clean/缺失/低质量/未知适用性路径、
严格 JSON 和 `SAXSResult` 传播；现有 Porod/Kratky/physical-helper 回归
必须保持通过。阶段门槛仍包括完整 SAXS 回归、结构化 verifier、quality/
preprocessing gates、`git diff --check` 和原子 checkpoint。真实样品、2D
探测器、AI 救援和发布角色不在本阶段关闭。
