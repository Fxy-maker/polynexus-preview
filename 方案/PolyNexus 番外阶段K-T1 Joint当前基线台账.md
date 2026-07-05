# PolyNexus 番外阶段 K-T1 Joint 当前基线台账

## 0. 台账目的

这份台账冻结当前 Joint 可信度链起点，用于后续 K 阶段修复对照。

## 1. 当前代码入口

主要入口：

- `polynexus/core/joint/dataset.py`
- `polynexus/core/joint/validation.py`
- `polynexus/core/joint/comparators.py`
- `polynexus/core/joint/coordinator.py`
- `polynexus/gui/widgets/joint_analysis_hub.py`
- `polynexus/gui/main_window.py`
- `tests/test_joint_hub_dataset.py`
- `tests/test_joint_coordinator.py`
- `tests/test_joint_analysis_hub.py`

## 2. 当前已有能力

Joint 当前已经能：

- 从样品库收集同一批次下各技术最新结果。
- 统计 DSC/SAXS/WAXS/IR/NMR 是否存在。
- 识别 analysis opportunities：
  - `crystallinity consistency`
  - `structure-thermodynamics`
  - `SAXS-WAXS multiscale`
  - `IR/DSC calibration`
- 运行跨技术 validations。
- 输出 summary rows、validation rows、AI context。
- 在 GUI 中展示 Joint Hub 和 diagnostics。
- 在 AI tuning workspace 中携带 `joint_ai_context`。

## 3. 当前 ai_context 字段

当前 `build_joint_hub_report()` 输出的 `ai_context` 包含：

- `summary`
- `scope`
- `sample_count`
- `batch_count`
- `issue_count`
- `warning_count`
- `error_count`
- `issue_families`
- `highlights`
- `samples`
- `batches`
- `row_count`

这些字段已经能提醒有无跨技术问题，但还不能完整解释“冲突为什么发生”。

## 4. 当前可信度短板

### 4.1 单技术 evidence 没有进入 Joint 权重

Joint 当前主要看 `results_summary` 中的数值。它还没有系统消费每条 run 的 `analysis_evidence`。

结果是：

- 低可信 SAXS `Xc` 可能和 DSC/WAXS 直接比较。
- 未标定 IR band index 可能被误看成结晶度。
- assignment-limited NMR `Xc` 可能被误看成结晶度。

### 4.2 条件轴和批次可比性还不够强

Joint row 知道 `condition_values`，但还缺：

- 条件轴来源可信度。
- 多技术是否处在同一条件窗口。
- 同批次是否混入多样品或多程序段。

### 4.3 issue families 偏粗

当前 issue family 主要包括：

- `phi_c inconsistency`
- `Tm bidirectional gap`
- `L consistency unstable`
- `cross-tech issue`

还缺：

- `IR calibration weak`
- `NMR assignment limited`
- `condition alignment weak`
- `single-tech evidence weak`
- `SAXS-WAXS scale mismatch`

## 5. 当前判断

可以信的部分：

- Joint Hub 的数据收集和基础展示已经可用。
- 跨技术 validations 已经有基础。
- AI context 已经能携带 issue summary。

暂时不能直接信的部分：

- Joint 还不能判断某个冲突是科学冲突，还是某个单技术输入低可信导致的假冲突。
- Joint 还不能对 IR/NMR/SAXS 的“弱结晶度来源”做语义降级。
- Joint 还不能完整表达条件轴不可比风险。

## 6. 后续验收基线

K 阶段完成后，应能回答：

- 当前 Joint row 的各技术证据等级是什么。
- 当前 Xc 冲突是否来自弱来源、未标定来源或真实跨技术不一致。
- 当前 Tm-L/lc 检查是否有足够条件可比性。
- 当前是否应该优先修单技术，还是进入 Joint compare。
- 当前 Joint 结果是否能进入导出报告的可信结论区。
