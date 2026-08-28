# 自适应等温 DSC 基线设计

## 背景

当前等温 DSC 候选事件检测已经能够排除常见的切换瞬态，但积分阶段仍默认使用事件后尾部恒定基线。对 PA6-DWJJ，历史 AI 采用事件端点线性基线，因此两者的 Avrami `n` 和 `t₁/₂` 出现了可解释但不必要的差异。需要把基线选择变成材料无关、由曲线形状驱动的确定性策略。

## 目标

- 对每个候选事件在其两端提取稳健窗口，并使用记录段尾部的稳定窗口作为恒定基线对照。
- 默认使用端点线性基线；在数据不支持时安全降级到尾部恒定基线。
- 每种实际使用的基线计算一个结果，但最终主结果只选择一个，不平均、不混合。
- 在结果和共享 ComputeRun/evidence 投影中记录基线方法、窗口、斜率和备选差异。
- 不使用 PA6/PA11/PA12 的温度、秒数或材料数据库规则。

## 非目标

- 不自动判断论文正文、补充材料或 Discussion 采用范围。
- 不修改原始数据。
- 不引入多项式/样条基线作为默认方法。
- 不把不同基线结果平均为一个“折中值”。
- 不删除现有快速分析、CLI、Batch、GUI 或 Agent/Codex 入口。

## 设计

### 1. 候选基线

每个事件候选使用其自身的 `start_index` 和 `end_index`。在两端分别取按事件长度比例确定的稳健窗口（窗口包含多个点时取中位数），构造：

- `endpoint_linear`：连接前端和后端窗口中位数的线性基线，默认方案；
- `tail_constant`：使用记录段尾部稳定窗口中位数的恒定基线，作为降级和敏感性对照；这与既有候选检测的尾部基线定义保持一致。

窗口长度按候选事件点数的比例计算，并限制在可用数据范围内；不能使用材料温度或固定秒数。端点窗口不满足最小点数、无有限值或事件尾部未闭合时，`endpoint_linear` 标记不可用，主结果降级为 `tail_constant` 并保留 warning。

### 2. 确定性选择

Core 先计算每个可用基线的积分、Xt、Avrami 参数和拟合质量。选择顺序为：

1. `endpoint_linear`，如果两端窗口有效且事件有正面积；
2. `tail_constant`，仅在端点线性基线不可用时；
3. 无可计算结果时返回结构化失败原因。

`tail_constant` 即使不是主结果，也作为 `baseline_variants` 保存。系统不根据“更接近历史 AI”或材料名称选结果。若备选方法的 `t₁/₂` 或 `n` 差异超过相对敏感性阈值，只增加 `baseline_sensitive` warning，不阻断计算。

### 3. 结果契约

`AvramiResult` 和参数表增加或保持以下字段：

- `baseline_method`；
- `baseline_start_value_Wg`、`baseline_end_value_Wg`、`baseline_slope_Wg_per_min`；
- `baseline_window_start_index`、`baseline_window_end_index`；
- `baseline_variants`（每个变体的方法、参数和关键结果）；
- `baseline_selection_reason`；
- `baseline_sensitive`。

候选事件、积分索引、`fit_xt_range=(0.05, 0.80)` 与原始 artifact/template provenance 继续沿用现有共享契约。

### 4. 入口一致性

Core 生成唯一的基线和 Avrami 结果。ComputeRun、CLI、Batch、GUI、Agent/Codex、证据包和 ARS 输入只消费现有 `AnalysisResult`/参数投影，不实现第二套基线算法。AnalysisPlan 保存实际采用的基线方法和参数快照；重新运行同一计划必须得到同样的主结果。

### 5. 可解释失败与警告

- 原始数组结构错误、时间不递增或事件没有正面积：继续硬阻断；
- 端点窗口不足、尾部未回稳、两种基线差异大：输出可计算结果并增加 warning；
- 所有 warning 和备选结果必须在 evidence 中可追溯。

## 验收标准

- PA6-DWJJ 180–184 ℃的主结果与历史端点线性基线结果在合理数值容差内一致。
- 合成的稳定漂移曲线默认选择 `endpoint_linear`，无材料名称参与。
- 合成的无前端窗口曲线自动降级到 `tail_constant` 并保留 warning。
- 多候选事件每个都保留独立的基线结果和 provenance。
- `ComputeRun`、参数表和证据投影包含相同的基线字段。
- 现有 DSC、ComputeRun、CLI/Batch、Agent/Codex、GUI/evidence 测试不回归。

## 科学边界

基线方法的选择是确定性数据处理决策，不等于科学结论。Core 不宣布论文采用范围；AI 可以根据候选和敏感性信息提出建议，用户或 ARS 仍负责最终科学审核。
