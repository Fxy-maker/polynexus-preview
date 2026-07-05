# PolyNexus 番外阶段 D 静态 WAXS 可信度修复清单

## 0. 当前问题定位

这份专项清单不是为了把 WAXS 的结果页再“包装得更像可信”，而是为了先把 WAXS 当前到底靠什么在判断可信度讲清楚，再把 `core -> residual -> analysis_evidence -> orchestrator -> GUI` 这条链真正补完整。

当前 WAXS 的基础已经有不少了：

1. `core` 已经能完成静态 WAXS 的峰检测、峰拟合、非晶扣除、结晶度、Scherrer / Williamson-Hall 等主流程。
2. `ResidualAnalyzer` 已经能把残差粗分成 `random / background_drift / systematic_peak`。
3. `config_bridge` 已经有 WAXS 可调参数白名单，`orchestrator` 也已经能跑 WAXS static 的最小调参闭环。
4. `analysis_evidence` 已经给 WAXS 建了两条很轻的约束：
   - `peak_visibility`
   - `fit_quality_vs_phys`

但当前真正的问题也很明确：

1. **WAXS 可信度判断还偏“拟合分数驱动”**
   - `r_squared` 仍然是最显眼、最容易被误读成“是否可信”的信号。
   - 但 WAXS 的风险常常不在“拟合没收敛”，而在“峰是凑出来的、非晶拆分不稳、晶型支撑不够”。

2. **物理证据层太薄**
   - 现在的约束还不足以回答：
   - 当前 `Xc_pct` 是不是被非晶背景模型推高/压低了？
   - 当前 `n_peaks` 虽然大于 0，但这些峰是不是可靠峰族？
   - 当前 `two_theta_offset`、`peak_distance`、`max_peaks` 的调参是否正在把错误峰拟合得更漂亮？

3. **残差语义还不够贴 WAXS**
   - 现有 `ResidualAnalyzer` 更像通用拟合残差分类器。
   - 但 WAXS 真正常见的问题还包括：
   - 峰位整体偏移
   - 峰数不足或过拟合
   - 非晶 halo 吃掉晶峰
   - 峰宽异常导致晶粒尺寸不可信

4. **GUI 还没有把“拟合得不错”和“物理上站得住”拆开**
   - 这会让用户容易把 `r_squared` 高、图顺眼，直接理解成“Xc / D / 晶型都可信”。

代表性基线入口建议先固定在：

- `D:\PolyNexus\tests\eval\cases\real\waxs_real_static_pa6.json`
- `D:\PolyNexus\测试数据\waxs\普通广角\PA6.raw`


## 1. 专项目标

番外阶段 D 只解决一个问题：

**让 PolyNexus 在处理静态 WAXS 这类“图可能很好看，但物理解释未必站稳”的样本时，先说清楚当前证据链稳不稳，再决定是否接受这轮拟合结果。**

本专项希望完成 4 件事：

1. 把 `fit good-looking` 和 `physically trustworthy` 两层语义拆开。
2. 把 WAXS 的主要失真来源升级成稳定可测的症状，而不是只靠人工看图判断。
3. 让 `orchestrator` 围绕“峰位 / 峰数 / 非晶背景 / 结晶度分解”的真实问题做小范围受控调参。
4. 让 GUI 明确告诉用户：当前可信的是哪部分，不可信的是哪部分，是否适合直接用于论文出图和结论。


## 2. 阶段边界

### 2.1 本专项要做什么

- 围绕 **静态 WAXS** 建一条更诚实的可信度证据链
- 强化 `analysis_evidence` 里的 WAXS 物理约束
- 补全 WAXS 专属残差语义和症状层
- 让 `orchestrator` 真正围绕 WAXS 风险点收敛，而不是只追逐更高 `r_squared`
- 让结果页能区分“当前图能出”和“当前参数能信”

### 2.2 本专项明确不做什么

- 不重写整套 WAXS 拟合算法
- 不在这一阶段把温变 WAXS / 拉伸 WAXS 一起拉进来
- 不把 AI 变成自动替用户决定晶型或结晶度真值的黑箱
- 不为了让结果看起来稳定而压制风险提示
- 不在这个专项里扩大到 Joint 全链路一致性修复


## 3. 最小闭环

本专项最小可交付闭环如下：

1. `core` 输出更完整的 WAXS 拟合证据、峰证据、非晶证据、结构证据
2. 系统识别“当前问题主要是峰问题、背景问题、偏移问题，还是过拟合问题”
3. `orchestrator` 只做小范围、白名单内、可回滚的 WAXS 调参尝试
4. 系统按物理证据改善而不是只按单个分数接受/回滚
5. GUI 明确展示：
   - 当前结晶度是否可信
   - 当前峰族和晶型支撑是否充分
   - 当前晶粒尺寸是否只是拟合副产品
   - 当前结果是否适合直接用于论文图和结论


## 4. 任务清单

### D-T1. 真实样本基线台账冻结

目标：
先把 `waxs_real_static_pa6` 这条真实 case 的当前状态冻结下来，作为后续每次修正的对照基线。

主要落点：

- `D:\PolyNexus\tests\eval\cases\real\waxs_real_static_pa6.json`
- `D:\PolyNexus\polynexus\core\analysis_evidence.py`
- `D:\PolyNexus\polynexus\core\residual_analyzer.py`

最小输出：

- 当前 `r_squared / quality_score / n_peaks / Xc_pct / D_Scherrer_nm`
- 当前残差类型与最大残差区域
- 当前峰数量、峰位、峰宽是否稳定
- 当前 GUI 会如何解读这组结果

建议记录字段：

- `peak_count_detected`
- `peak_count_fitted`
- `dominant_peak_positions`
- `amorphous_fraction_proxy`
- `fit_only_pass`
- `physical_support_pass`
- `paper_ready_candidate`

验收标准：

- 不看图也能知道当前这组 WAXS 数据的主要风险在哪里
- 后续每一轮可信度修复都能跟这份基线对比

推荐模型：`mini`


### D-T2. WAXS evidence 分层补强

目标：
把 WAXS 当前过于扁平的 `analysis_evidence` 扩成真正能支撑可信度判断的结构化证据层。

主要落点：

- `D:\PolyNexus\polynexus\core\analysis_evidence.py`
- `D:\PolyNexus\polynexus\core\waxs.py`

最小输出：

- `fit_evidence`
- `peak_evidence`
- `background_evidence`
- `structure_evidence`
- `phase_evidence`

建议最少补齐字段：

- `peak_count`
- `peak_positions`
- `peak_widths`
- `peak_area_ratio`
- `background_method`
- `amorphous_subtraction`
- `amorphous_n_peaks`
- `two_theta_offset`
- `crystallinity_method`
- `crystal_system`
- `unit_cell_params_present`
- `scherrer_support_peaks`

验收标准：

- `analysis_evidence` 不再只是“有个分数和几个结果值”
- AI 和 GUI 都能区分“结果值”和“支撑这些结果值的证据”

推荐模型：`mini`


### D-T3. WAXS 物理约束升级

目标：
把现在只有 `peak_visibility` 和 `fit_quality_vs_phys` 的轻约束，升级成更贴 WAXS 实际误差来源的可信度门。

主要落点：

- `D:\PolyNexus\polynexus\core\analysis_evidence.py`
- `D:\PolyNexus\tests\test_analysis_evidence.py`

建议新增约束：

- `peak_count_insufficient`
- `peak_family_unstable`
- `amorphous_partition_unstable`
- `peak_width_nonphysical`
- `offset_sensitive_solution`
- `crystallinity_without_peak_support`
- `size_without_multi_peak_support`

建议保留并强化：

- `peak_visibility`
- `fit_quality_vs_phys`

验收标准：

- 不能再出现“`r_squared` 很高，但其实没有足够晶峰支撑 `Xc_pct`”时还被当成基本可信
- 不能再出现“只有一两个可疑峰，却直接给出看起来很像真值的晶粒尺寸”

推荐模型：`mini`


### D-T4. WAXS 专属残差语义拆分

目标：
让 WAXS 的残差分类从通用层升级成更接近真实实验问题的语义层。

主要落点：

- `D:\PolyNexus\polynexus\core\residual_analyzer.py`
- 如有必要新增：`D:\PolyNexus\polynexus\core\waxs_residual_analyzer.py`

建议新增或细化残差类型：

- `peak_position_bias`
- `peak_count_underfit`
- `peak_count_overfit`
- `amorphous_background_bias`
- `peak_width_mismatch`
- `low_angle_background_drift`

当前通用类型可保留为兜底：

- `random`
- `background_drift`
- `systematic_peak`

验收标准：

- AI 不再只知道“峰不太对”，而是能进一步知道“是峰位偏了、峰少了、峰多了，还是 halo 拆错了”
- 后续动作能和真实症状一一对应

推荐模型：`mini`


### D-T5. WAXS 症状层与参数动作桥接

目标：
把 WAXS 的真实问题稳定映射到可控动作，而不是让 AI 直接自由发挥改参数。

主要落点：

- `D:\PolyNexus\polynexus\orchestrator.py`
- `D:\PolyNexus\polynexus\config_bridge.py`
- 如有必要新增：`D:\PolyNexus\polynexus\core\waxs_action_registry.py`

建议症状到动作优先顺序：

1. `peak_position_bias`
   - 先试 `two_theta_offset`
2. `peak_count_underfit`
   - 先试 `peak_distance`
   - 再试 `max_peaks`
3. `amorphous_background_bias`
   - 先试 `background_method`
   - 再试 `amorphous_subtraction`
   - 再试 `amorphous_n_peaks`
4. `peak_width_mismatch`
   - 先试 `peak_function`
5. `noise_dominant`
   - 先试 `smooth_window`

动作约束：

- 每轮只改 1-2 个参数
- 不允许同时改两个强耦合层：
  - 比如 `peak_distance + max_peaks`
  - 比如 `amorphous_subtraction + amorphous_n_peaks`
- 如果新结果只是让图更顺眼，但物理约束更差，必须回滚

验收标准：

- 调参路径更像“针对问题修”，而不是“随机试几个参数”
- 被拒绝的参数组合能形成清晰历史，不会来回打转

推荐模型：`5.4`


### D-T6. 接受 / 回滚规则升级

目标：
让 WAXS 的收敛规则从“分数更高就算更好”升级成“分数、峰支撑、物理约束共同改善才算更好”。

主要落点：

- `D:\PolyNexus\polynexus\orchestrator.py`
- `D:\PolyNexus\polynexus\core\analysis_evidence.py`

建议新增比较项：

- `r_squared`
- `quality_score`
- `triggered_constraint_count`
- `peak_support_score`
- `background_stability_score`
- `phase_support_score`
- `size_support_score`

建议新增回滚条件：

- `physical_support_weakened`
- `crystallinity_support_collapsed`
- `peak_family_became_less_stable`
- `background_partition_worsened`

验收标准：

- 新结果必须在物理证据上更可信，才允许替换当前推荐结果
- “更好看但更假”的结果会自动回滚

推荐模型：`5.4`


### D-T7. GUI 结果语义拆分

目标：
让用户一眼知道当前 WAXS 结果里，什么是可信结论，什么只是待复核的拟合产物。

主要落点：

- `D:\PolyNexus\polynexus\gui\main_window.py`
- `D:\PolyNexus\polynexus\gui\i18n.py`

最小界面结构建议：

- 当前主结论
- 当前可信度判断
- 当前主要风险
- 当前是否适合论文出图
- 当前下一步建议

建议文案语义：

- `Measured peak support`
- `Crystallinity estimate`
- `Physical support still limited`
- `Peak family needs review`
- `Figure usable, conclusion pending`

验收标准：

- 用户不会再把“拟合曲线对上了”自动理解成“结晶度和晶粒尺寸已经可信”
- 结果页更像科研结论页，而不是只报一堆数

推荐模型：`mini`


### D-T8. 真实样本回归验证

目标：
确保这份清单修的不是理想 case，而是能解释你手上的真实 WAXS 样本。

主要落点：

- `D:\PolyNexus\tests\test_analysis_evidence.py`
- `D:\PolyNexus\tests\test_orchestrator.py`
- 如有必要新增：
  - `D:\PolyNexus\tests\test_waxs_residual_analyzer.py`
  - `D:\PolyNexus\tests\test_waxs_confidence_contract.py`

最小验证内容：

- 真实样本当前为何低置信
- WAXS evidence 是否完成分层
- 新约束能否稳定命中
- orchestrator 是否优先修真实问题
- GUI 是否能把“图可出”和“值可信”拆开

验收标准：

- 即使结果暂时还不能完全修好，系统也能把原因讲清楚
- 如果后续某轮真的变好，系统能明确证明“比基线更可信”

推荐模型：`mini`


## 5. 推荐推进顺序

建议不要一口气全动，按这个顺序最稳：

1. `D-T1` 基线冻结
2. `D-T2` evidence 分层
3. `D-T3` 物理约束升级
4. `D-T4` 残差语义拆分
5. `D-T5` 症状到动作桥接
6. `D-T6` 接受 / 回滚规则升级
7. `D-T7` GUI 结果语义拆分
8. `D-T8` 真实样本回归


## 6. 这一阶段完成后的产品变化

做完这份清单后，PolyNexus 的 WAXS 不会只是“更会拟合”，而会更像一个靠谱的专业分析工作台：

- 会承认高分结果也可能不可信
- 会说明当前到底缺的是峰支撑、背景支撑，还是结构支撑
- 会让 AI 围绕真实物理问题调参
- 会把论文可出图和科研可下结论这两件事分开讲清楚

这也是后面把温变 WAXS、拉伸 WAXS、再到 Joint 一起接起来的前提。
