# PolyNexus 番外阶段 E IR 可信度修复清单

## 0. 当前问题定位

这份专项清单不是为了把 IR 做得“更像会分析”，而是为了先把 IR 当前到底靠什么在给结论、哪些地方还只是拟合或匹配分数撑着，讲清楚。

目前 IR 这条链路其实已经不算空白：
1. `core` 已经有标准 IR 分析链：
   - `D:\PolyNexus\polynexus\core\ir.py`
   - `D:\PolyNexus\polynexus\core\ir_engine\...`
2. `orchestrator` 已经能跑 IR 的最小调参闭环：
   - `D:\PolyNexus\polynexus\orchestrator.py`
3. IR 残差分析已经单独拆出：
   - `D:\PolyNexus\polynexus\core\ir_residual_analyzer.py`
4. prompt 里也已经有 IR 专属调参顺序：
   - `baseline_method -> smooth_window -> peak_height_min / peak_prominence_min -> peak_distance -> lineshape`
   - 文件：`D:\PolyNexus\rag\prompt_builder.py`

但当前真正的问题也很明确：
1. **IR 的“结果值”和“可信度”还没有彻底拆开**
   - 当前 `orchestrator` 里 IR 常把 `polymer_score` 直接落成 `quality_score`
   - 这会让“匹配分数高”被误读成“结论就可信”
2. **IR 的 evidence 层还偏薄**
   - `analysis_evidence.py` 里目前 IR 只有两条比较轻的约束：
   - `assignment_confidence`
   - `peak_structure`
   - 还不够解释“为什么这次官能团归属可信 / 不可信”
3. **IR 参考知识还没真正补齐**
   - `rag\polymer_knowledge.py` 里已经明确写了：
   - 当前 IR 特征吸收带参考数据尚未系统收录
   - 所以现在更多还是靠残差、峰数和匹配分数在调参
4. **IR 残差语义还不够贴近真实误差来源**
   - 当前主要是：
   - `peak_mismatch`
   - `baseline_drift`
   - `noise`
   - 但 IR 实际常见问题还包括：
   - 基线压坏弱峰
   - 峰重叠导致误判
   - 归一化方式把强弱带相对关系扭曲
   - 特征带数量够，但关键带支撑不够
5. **GUI / agent 语义上还容易把“识别到了某聚合物”说得太像“已经足够可信”**
   - 这对 IR 尤其危险
   - 因为 IR 很容易出现“像这个材料，但证据支撑还不够扎实”的中间态


## 1. 专项目标

番外阶段 E 只解决一个问题：

**让 PolyNexus 在处理 IR 这类“峰很多、解释空间也很多”的数据时，先把测到的峰、可支持的归属、推断出的聚合物结论这三层拆清楚，再让 agent 围绕这些证据做小范围、可回滚的调参。**

本专项希望完成 4 件事：
1. 把 `detected bands`、`assignment evidence`、`polymer conclusion` 三层语义拆开
2. 把 IR 常见失真来源升级成稳定可测的症状，而不是只靠人眼看图
3. 让 `orchestrator` 围绕基线、峰识别、局部拟合窗口、归一化这些真实问题做受控调参
4. 让 GUI 明确告诉用户：当前哪些峰是测到的，哪些归属只是候选，当前结论适不适合直接写进论文


## 2. 阶段边界

### 2.1 本专项要做什么？
- 围绕 **标准 IR** 建一条更诚实的可信度证据链
- 补强 `analysis_evidence` 里的 IR 证据层
- 细化 IR 残差语义与症状层
- 让 `orchestrator` 不再只追 `polymer_score` 或单一 `r_squared`
- 让 agent 更像“证据整理与调参助手”，而不是“直接替用户认材料”

### 2.2 本专项明确不做什么？
- 不重写整套 IR 峰拟合算法
- 不在这一阶段直接扩展到二维变温 IR 全链路
- 不把 AI 变成自动替用户下最终化学归属结论的黑箱
- 不为了让结果看起来更稳而压制风险提示
- 不在这一阶段承诺“只要调几轮参数就一定能把所有 IR 样本调到高可信”


## 3. 最小闭环

本专项最小可交付闭环如下：
1. `core` 输出更完整的 IR 峰证据、基线证据、归属证据、聚合物结论证据
2. 系统识别“当前主要问题是基线、噪声、漏峰、错峰、重叠峰，还是关键特征带支撑不足”
3. `orchestrator` 只做白名单内、可回滚的小范围 IR 调参尝试
4. 接受 / 回滚规则按证据改善而不是只按单一分数改善
5. GUI 明确展示：
   - 当前测到哪些峰
   - 当前哪些峰归属比较稳
   - 当前聚合物判断有多大把握
   - 当前是否适合直接作为论文结论使用


## 4. 任务清单

### E-T1. IR 真实样本基线台账冻结

目标：
先选 1 组真实 IR 样本，把当前状态冻结成专项基线，避免后面一边改一边失去对照。

主要落点：
- `D:\PolyNexus\docs\baselines\PolyNexus 番外阶段E-T1 IR当前基线台账.md`
- `D:\PolyNexus\polynexus\orchestrator.py`
- `D:\PolyNexus\polynexus\core\analysis_evidence.py`

最小输出：
- 当前 `polymer_name / polymer_score / r_squared / n_peaks / Xc_pct`
- 当前主要残差类型与最大残差区域
- 当前关键峰数量、峰位、峰宽是否稳定
- 当前 GUI 会如何解读这组结果

建议记录字段：
- `detected_peak_count`
- `assigned_peak_count`
- `key_band_support_score`
- `polymer_score`
- `assignment_confidence_score`
- `baseline_stability_score`
- `peak_coverage_score`
- `paper_conclusion_ready`

验收标准：
- 不看图也能知道当前这组 IR 到底是“峰没抓对”、还是“抓到了峰但归属不稳”
- 后续每一轮修复都能和这份基线对比

推荐模型：`mini`


### E-T2. IR evidence 分层补强

目标：
把当前 IR 还偏扁平的 evidence 结构，扩成真正能支撑可信度判断的多层证据。

主要落点：
- `D:\PolyNexus\polynexus\core\analysis_evidence.py`
- `D:\PolyNexus\polynexus\orchestrator.py`

最小输出：
- `signal_evidence`
- `peak_evidence`
- `baseline_evidence`
- `assignment_evidence`
- `structure_evidence` 或 `classification_evidence`

建议至少补齐字段：
- `peak_count`
- `peak_positions`
- `peak_widths`
- `peak_prominence_distribution`
- `baseline_method`
- `normalization_method`
- `assigned_peaks`
- `unassigned_peaks`
- `key_reference_bands_hit`
- `key_reference_bands_missing`
- `polymer_score`
- `assignment_confidence`
- `classification_basis`

验收标准：
- `analysis_evidence` 不再只是“有几个峰 + 有个聚合物分数”
- AI 和 GUI 都能区分：
  - 测到的峰
  - 对峰的归属
  - 基于归属推到的聚合物结论

推荐模型：`mini`


### E-T3. IR 物理 / 化学约束升级

目标：
把现在只有 `assignment_confidence` 和 `peak_structure` 的轻约束，升级成更贴近 IR 实际失真来源的可信度门。

主要落点：
- `D:\PolyNexus\polynexus\core\analysis_evidence.py`
- `D:\PolyNexus\tests\test_analysis_evidence.py`

建议新增约束：
- `key_band_support_insufficient`
- `assignment_without_characteristic_bands`
- `baseline_sensitive_assignment`
- `weak_peak_only_support`
- `overcrowded_band_separation_unstable`
- `polymer_score_without_assignment_support`
- `crystallinity_index_without_band_support`

建议保留并强化：
- `assignment_confidence`
- `peak_structure`

验收标准：
- 不能再出现“`polymer_score` 看起来不错，但关键特征带其实没站稳”时还被说成基本可信
- 不能再出现“峰数不少，但大多只是弱峰或不关键峰”时还直接抬高结论可信度

推荐模型：`mini`


### E-T4. IR 专属残差语义细化

目标：
把 IR 残差从现在较通用的三分类，升级成更接近真实实验问题的语义层。

主要落点：
- `D:\PolyNexus\polynexus\core\ir_residual_analyzer.py`
- 如有必要新增：`D:\PolyNexus\polynexus\core\ir_symptom_detector.py`

建议新增或细化残差类型：
- `baseline_drift_low_wn`
- `baseline_drift_high_wn`
- `key_band_mismatch`
- `crowded_band_underfit`
- `over_smoothed_weak_bands`
- `normalization_bias`
- `noise_dominant`

当前可保留为兜底：
- `peak_mismatch`
- `baseline_drift`
- `noise`
- `random`

验收标准：
- AI 不再只知道“峰不太对”
- 而是能进一步知道：
  - 是基线压坏了
  - 是局部峰窗不对
  - 是平滑把弱峰抹掉了
  - 还是归一化扭曲了强弱峰关系

推荐模型：`mini`


### E-T5. IR 症状层与参数动作桥接

目标：
把 IR 的真实问题稳定映射到白名单参数动作，而不是让 AI 自由发挥改参数。

主要落点：
- `D:\PolyNexus\polynexus\orchestrator.py`
- `D:\PolyNexus\polynexus\config_bridge.py`
- 如有必要新增：`D:\PolyNexus\polynexus\core\ir_action_registry.py`

建议症状到动作优先顺序：

1. `baseline_drift_*`
   - 先试 `baseline_method`
   - 再试 `normalization_method`
2. `noise_dominant`
   - 先试 `smooth_window`
3. `key_band_mismatch`
   - 先试 `peak_fit_window_cm1`
   - 再试 `peak_prominence_min`
   - 再试 `peak_height_min`
4. `crowded_band_underfit`
   - 先试 `peak_distance`
   - 再试 `lineshape`
5. `weak_peak_only_support`
   - 先试阈值类参数
   - 不要过早抬高聚合物结论

动作约束：
- 每轮只改 1-2 个参数
- 先处理基线 / 噪声，再处理峰阈值 / 峰窗
- 不允许“为了多识别几个峰而明显破坏关键带相对关系”的组合通过

验收标准：
- 调参路径更像“针对问题修”
- 而不是“看到分数不高就试着改点什么”

推荐模型：`5.4`


### E-T6. 接受 / 回滚规则升级

目标：
让 IR 的收敛规则从“匹配分数更高就算更好”，升级成“峰支撑、归属支撑、基线稳定性共同改善才算更好”。

主要落点：
- `D:\PolyNexus\polynexus\orchestrator.py`
- `D:\PolyNexus\polynexus\core\analysis_evidence.py`

建议新增比较项：
- `polymer_score`
- `assignment_confidence_score`
- `key_band_support_score`
- `baseline_stability_score`
- `peak_coverage_score`
- `unassigned_key_band_count`
- `triggered_constraint_count`

建议新增回滚条件：
- `assignment_support_weakened`
- `key_band_support_collapsed`
- `baseline_became_less_stable`
- `peak_count_increased_but_key_bands_lost`
- `classification_basis_became_weaker`

验收标准：
- 新结果必须在“证据支撑”上也更可信，才允许替换当前推荐结果
- “分数更高但证据更空”的结果会自动回滚

推荐模型：`5.4`


### E-T7. IR 参考知识补强

目标：
把当前“IR 参考知识尚未收录”的状态推进到至少能支撑主流聚合物特征带判断，而不是一直只靠分数和残差兜着。

主要落点：
- `D:\PolyNexus\rag\polymer_knowledge.py`
- `D:\PolyNexus\polynexus\data\polymers\*.json`

最小补强方向：
- 为现有主流聚合物补齐 IR characteristic bands
- 区分：
  - 强特征带
  - 辅助带
  - 易重叠带
- 给出可用于归属判断的最小参考结构

建议字段：
- `ir.characteristic_bands`
- `ir.key_bands`
- `ir.secondary_bands`
- `ir.overlap_risks`
- `ir.assignment_notes`

验收标准：
- prompt 不再只能说“当前主要依赖残差与峰稳定性调参”
- IR 结论开始真正有参考知识支撑

推荐模型：`5.4`


### E-T8. GUI 结果语义拆分

目标：
让用户一眼知道当前 IR 页面里，什么是测到的、什么是推断的、什么还不适合直接写进论文。

主要落点：
- `D:\PolyNexus\polynexus\gui\main_window.py`
- `D:\PolyNexus\polynexus\gui\i18n.py`

最小界面结构建议：
- 当前检测峰
- 当前关键带支撑
- 当前聚合物判断
- 当前主要风险
- 当前是否适合直接用于论文结论

建议文案语义：
- `Detected bands`
- `Assignment support`
- `Polymer conclusion`
- `Key bands still missing`
- `Figure usable, conclusion pending`

验收标准：
- 用户不会再把“识别成 PA6”自动理解成“PA6 结论已经足够稳”
- agent 给出的建议能回到工作台上的具体证据区，而不是悬空地说“可信度偏低”

推荐模型：`mini`


### E-T9. 真实样本回归验证

目标：
让这条 IR 可信度修复链不只在合成 case 上成立，也能解释真实样本为什么可信或为什么不可信。

主要落点：
- `D:\PolyNexus\tests\test_ir_bridge.py`
- `D:\PolyNexus\tests\test_ir_engine.py`
- 如有必要新增：`D:\PolyNexus\tests\eval\cases\real\ir_*.json`

最小验证内容：
- 当前真实样本为什么低可信 / 中可信
- evidence 是否已拆成多层
- 症状是否能稳定命中
- orchestrator 是否优先修基线 / 峰识别问题
- GUI 是否明确区分“可出图”和“可下结论”

验收标准：
- 即使结果暂时还不能完全修好，系统也能把原因讲对
- 若后续某轮真的修好，系统能明确证明“比基线更可信”

推荐模型：`mini`


## 5. 推荐推进顺序

建议按下面顺序做：

1. `E-T1` 先冻结一条真实 IR 基线
2. `E-T2 + E-T3` 先把 evidence 和约束补强
3. `E-T4 + E-T5` 再把残差语义和参数动作桥接起来
4. `E-T6` 最后收紧接受 / 回滚规则
5. `E-T7 + E-T8` 同步补参考知识与 GUI 语义
6. `E-T9` 用真实样本回归收口

这样推进的好处是：
- 先把“怎么看懂 IR 可信度”站稳
- 再去做“怎么调参修”
- 不会一上来就把 agent 调参做成会动但不会解释的黑箱


## 6. 完成后的产品变化

这个专项做完之后，IR 板块最重要的变化不该只是“分数更好看”，而应该是：

1. 用户能清楚知道当前 IR 结论是怎么来的
2. agent 能围绕真实证据去调参，而不是只追某个分数
3. GUI 能把“检测到的峰”“支持的归属”“聚合物结论”拆清楚
4. 即使遇到不够好的数据，系统也会诚实地保留低可信，而不是硬抬
5. 后面如果要把 IR 进一步接进 joint / cross-technique 联动，这条 evidence 链也能直接复用


## 7. 我对 IR 这条线的判断

如果说 SAXS 当前最难的是“低 q 物理约束没站稳”，WAXS 当前最难的是“拟合和物理支持还没完全拆开”，那 IR 当前最核心的问题就是：

**它已经能给出像样的识别结果，但还不够会证明这些识别结果为什么值得信。**

所以 IR 这条清单的优先级，不是先把 agent 做得更会说，而是先把：
- 峰证据
- 归属证据
- 聚合物结论证据

这三层真正搭起来。
