# PolyNexus 番外阶段 D-T1 静态 WAXS 当前基线台账

## 1. 目标

先把 `waxs_real_static_pa6` 这条真实 case 的当前状态冻结下来，作为后续每次修正的对照基线。
这里的“冻结”不是把单一样品当成最终真理，而是记录当前代码版本在真实样本上的行为快照，方便后面判断修复到底是在变好，还是只是图更顺眼。

## 2. 样本范围

- case 文件: `D:\PolyNexus\tests\eval\cases\real\waxs_real_static_pa6.json`
- 真实数据: `D:\PolyNexus\测试数据\waxs\普通广角\PA6.raw`
- 技术: `WAXS / static`
- 样本标签: `PA6`
- 点数: `3758`
- 2theta 范围: `2.0625` 到 `80.0000`

## 3. 当前基线摘要

### 3.1 核心数值

- `r_squared = 0.9296174269`
- `quality_score = 0.9296174269`  
  说明: 在当前 WAXS 链路里，`quality_score` 实际上沿用了 `r_squared` 口径。
- `eval_score = 0.9535475018`
- `Xc_pct = 69.6`
- `D_Scherrer_nm = 8.3`
- `n_peaks = 2`
- `Xc_method = peak_deconvolution`
- `crystal_system = unknown`
- `sector_used = full`

### 3.2 峰信息

当前拟合到的峰为 2 个：

1. `2theta = 17.8781°`
   - `FWHM = 0.8549°`
   - `area = 2442.34`
2. `2theta = 21.7529°`
   - `FWHM = 1.1242°`
   - `area = 1810.52`

当前检测到的峰位与拟合峰位一致，说明峰数量和峰位在当前配置下是自洽的。

### 3.3 残差情况

- `residual_type = random`
- `max_residual_region = 2θ=17.0°`
- `RMSE = 44.5390`
- `residual_pattern.r_squared = 0.984763`

残差摘要当前说明的是：
- 整体残差主要呈随机分布
- 最大残差集中在 `17°` 附近
- 从残差类型上看，没有被判成明显的 `background_drift` 或 `systematic_peak`

### 3.4 物理约束与证据层

当前 `analysis_evidence` 的摘要是：
- `summary = residual=random; constraints=2`
- `constraint_summary.status = ok`
- `constraint_summary.triggered_total = 0`

这意味着：
- 目前没有触发 WAXS 的硬失败或软警告约束
- 但证据层本身还是很薄，主要还是围绕 `r_squared` 和少量峰信息在说话

## 4. 这条基线对 GUI 的意义

按现在的结果面板逻辑，这条数据会被用户理解成：

- 这是一个**可以出结果的原始结果**
- 拟合质量看起来不错
- 有明确的晶峰支持
- 但当前 GUI 还不会自动把它说成“论文结论已完全稳定”

更准确地说，当前界面更像会把它视为：
- `Measured peak support` 较明确
- `Crystallinity estimate` 可以读
- 但如果后续要做更严格的论文级判断，还是应该保留“待复核”的空间

## 5. 当前基线的实际风险

这条样本目前的风险，不在于“完全没出结果”，而在于：

1. 结果仍然很依赖分峰和背景处理
2. `quality_score` 在 WAXS 里并不是独立质量门，而是沿用 `r_squared`
3. 当前证据层对“为什么这组结果可信”还解释得不够细
4. GUI 还没有完全把“可用结果”和“论文可直接定论结果”拆开

## 6. 这一版基线记录的用途

后续如果我们改：
- `analysis_evidence`
- `residual_analyzer`
- `orchestrator`
- `GUI`
- WAXS 的物理约束

都应该拿这条 PA6 真实 case 做对照，看下面这些是否真的改善：

- 峰位是否更稳
- 峰宽是否更合理
- 残差是否更贴近真实问题
- 证据层是否能更明确地区分“结果值”和“支撑结果的证据”
- GUI 是否能让用户一眼看懂这到底是不是论文级结果

## 7. 当前结论

这条基线说明：

- 当前静态 WAXS 不是“没算出来”，而是**已经算出了一个看起来还不错的结果**
- 但系统还需要更强的证据层来回答“这个结果到底靠不靠谱”
- 所以 D-T1 的价值，是把这个真实状态先固定下来，后面每一步修复都能明确对比

## 8. 回归记录

当前已跑通真实样本回归，得到的关键快照为：
- `r_squared = 0.9296174269`
- `Xc_pct = 69.6`
- `D_Scherrer_nm = 8.3`
- `n_peaks = 2`
- `residual_type = random`
- `max_residual_region = 2θ=17.0°`
- `quality_score = 0.9296174269`

---

这份台账现在可以作为 D 阶段后续所有 WAXS 修复的对照基线。
