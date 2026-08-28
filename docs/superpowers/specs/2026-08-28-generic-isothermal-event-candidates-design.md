# 通用等温 DSC 候选事件计算设计

日期：2026-08-28
状态：待人工审阅

## 目标

将等温 DSC 的处理从“自动选定一个事件并可能错误阻断”改为材料无关的候选事件计算：Core 识别并计算所有可行事件，AI 或用户在研究问题上下文中选择研究相关事件，最终选择和计算参数写入本次 AnalysisPlan，保证可复现。

## 非目标

- 不为 PA6、PA11、PA12 或其他材料加入固定温度、固定秒数或专用阈值。
- 不修改原始实验文件。
- 不让 AI 修改热流数据或直接编造科学数值。
- 不由 Core 判断论文 Results/Discussion 资格。
- 不删除现有兼容入口；迁移完成前保留兼容别名。

## 核心架构

```text
原始文件
  -> canonical thermal_program.v1 / dsc.isothermal.v1
  -> IsothermalEventDetector
  -> 全部候选事件 + 候选评分/警告
  -> 对每个候选计算 Xt、t1/2、G、n、k、R²
  -> AI 默认推荐研究相关候选；歧义时交给用户
  -> AnalysisPlan 冻结候选 ID、边界、基线和拟合区间
  -> ComputeRun / evidence package / GUI / CLI 使用同一结果
```

## 候选事件模型

每个等温段至少输出：

- `candidate_id`；
- `kind`：`transient`、`primary_exotherm`、`secondary_event` 或 `unknown`；
- 原始数据索引和相对时间边界；
- `transient_excluded`；
- 基线方法和参数；
- 峰位置、prominence、面积、噪声比和边界完整性；
- 候选评分及评分理由；
- 该候选的完整确定性计算结果；
- 质量警告。

默认推荐只是排序结果，不会删除未推荐候选。候选排序依据数据形状的相对特征：局部噪声、变化率、峰 prominence、峰前后基线稳定性、事件面积和采样点数量。不得使用材料名称推断温度或时间窗口。

## 计算和判断边界

Core 负责：

- 验证时间轴、数值数组和采样点数量；
- 识别候选事件；
- 对所有候选执行相同积分和 Avrami 计算；
- 默认使用 `Xt=5%–80%`，并允许本次 AnalysisPlan 显式覆盖；
- 保存积分起止、瞬态排除、基线和拟合参数。

Core 只对结构性错误硬阻断，例如非数值数组、时间不递增、点数不足或没有任何可计算候选。边界不确定、峰形不完整、低 prominence 或低 R² 作为警告，不抹掉可计算结果。

AI/用户负责：

- 根据研究问题选择候选事件；
- 必要时确认候选排序或修改本次方案的边界；
- 解释研究用途和证据等级。

AI/用户不能修改原始数据，也不能绕过 canonical 转换和确定性计算。

## PA6 问题的预期修复

对 PA6-DWJJ，系统应同时保留降温切换瞬态和真实结晶放热候选。默认推荐真实主放热候选；该候选应从瞬态结束后开始积分，并得到接近历史独立处理口径的结果。历史结果不是写死到 Core 的答案，只作为回归基准和验证材料。

## 共享边界

- Producer：canonical DSC converter、`IsothermalEventDetector`、`DSCEngine`、`ComputeRunService`。
- Consumers：项目分析、Agent/Codex、CLI、Batch、GUI、evidence package 和 ARS writing input。
- 所有入口必须读取同一个候选事件和 AnalysisPlan 投影，不得在 GUI 或 AI 入口另写一套峰识别算法。

## 验收标准

- [ ] 同一等温段可输出瞬态、主事件和其他可行候选，不丢弃未推荐候选。
- [ ] 默认推荐由数据形状驱动，不含材料专用常量。
- [ ] PA6-DWJJ 前五个等温平台不再把切换瞬态作为主事件，结果接近历史 1.82–3.40 min 范围。
- [ ] 185 ℃ PA6、PA11、PA12、PA6-50、PA11-50、PA12-50 的已有可计算结果不被破坏。
- [ ] 每个候选均保存边界、基线、拟合区间、警告和源文件哈希。
- [ ] AI/CLI、Batch、GUI 和 evidence package 使用相同候选与 AnalysisPlan 投影。
- [ ] 结构性坏数据仍正确硬阻断；科学质量问题只产生警告。

## 验证矩阵

- PA6-DWJJ 真实回归：瞬态与主放热候选、`t1/2`、积分边界。
- 六样品真实回归：不因材料名称或温度范围触发专用分支。
- 合成曲线：单峰、多峰、反向峰、长瞬态、无明显峰和不完整峰。
- Core/ComputeRun/CLI/Batch/GUI DTO/evidence package 的共享投影一致性。

## 待审阅事项

本设计仍需人工确认：默认推荐候选的评分排序是否符合实验语义，以及历史 AI 数值作为回归容差时应采用何种允许误差。科学结论和论文用途仍由 ARS/用户决定。
