# PolyNexus 番外阶段 C 温变 SAXS 可信度修复清单

## 0. 当前问题定位

这份专项清单不是为了“把 Low Confidence 字样去掉”，而是为了先把这批真实样本的问题讲清楚，再让 `core -> symptom -> orchestrator -> GUI` 这条链真正接住它。

当前针对样本：

- `D:\PolyNexus\测试数据\saxs\无定形单个样品变温`
- 代表文件：`Check-20260618_0_00002.edf` ~ `Check-20260618_0_00018.edf`

已确认的真实情况：

1. 图已经重新生成，不是单纯 GUI 没刷新。
2. 条件轴恢复基本可信：
   - `condition_source = header`
   - `condition_confidence = 0.9`
   - 温度轴单调递增
3. 当前主要问题不在条件轴，而在低 q 证据链：
   - 多帧存在 `ERROR:qstar_contaminated`
   - 多帧存在 `WARN:mask_truncated`
   - `Effective q_min > 0.10 nm^-1`
   - `Guinier region lost`
4. `L_nm` 还有一定变化，但 `lc_nm` / `lc_confidence` 出现明显“被校准值抹平”的迹象：
   - `lc_nm` 整批锁在 `3.07`
   - `lc_confidence` 整批锁在 `0.50`
   - `lc_method = calibrated`
5. 这说明当前系统里同时存在两层语义：
   - 一层是真实 frame 级证据：低 q 污染、invariant 不稳、IDF 不稳
   - 一层是 batch 级 fallback：为了给出温变摘要，写入了校准型 `lc`

这两层语义现在混在一起，会让 AI 和用户都很难判断：

**当前看到的是“真实测得结果”，还是“带 fallback 的保守估计”。**


## 1. 专项目标

番外阶段 C 只解决一个问题：

**让 PolyNexus 在处理温变 SAXS 这类真实低 q 受污染样本时，先说真话，再做受控修正，最后把“哪些结果能信、哪些结果只是保守估计”清楚地交给用户。**

本专项希望完成 4 件事：

1. 把 `raw evidence` 和 `calibrated fallback` 明确拆开。
2. 把“低 q 污染 + fallback 抹平”升级成稳定可测的症状。
3. 让 `orchestrator` 先修低 q 证据链，再决定是否接受厚度参数。
4. 让 GUI 明确区分“测得结果”和“估计结果”。


## 2. 阶段边界

### 2.1 本专项要做什么

- 围绕温变 SAXS 样本建立一条更诚实的证据链
- 修正 `SAXS temperature batch` 分支里对 `lc/Q*` 的 fallback 表达方式
- 让 symptom / action / rollback 真的围绕低 q 污染问题运转
- 让结果面板能解释“为什么现在还不能信厚度链”

### 2.2 本专项明确不做什么

- 不重写整条 SAXS 算法线
- 不为了好看直接压掉 `Low Confidence`
- 不让 AI 自由乱改全部 SAXS 参数
- 不在这个专项里引入独立聊天式 agent 界面
- 不把最终科研判断交给 AI


## 3. 最小闭环

本专项最小可交付闭环如下：

1. `core` 输出 frame 级真实证据与 batch 级 fallback 证据
2. 系统识别“低 q 污染主导”与“fallback 覆盖真实波动”这两类症状
3. `orchestrator` 只围绕低 q / correlation / IDF 窗口做小范围受控尝试
4. 系统按证据变化而不是按图是否顺眼来接受/回滚
5. GUI 明确展示：
   - 当前可信的是哪部分
   - 当前不可信的是哪部分
   - 当前结果里哪些值仍然依赖 fallback

只要这条链打通，PolyNexus 对这类真实样本的表现就会更像：

**“会承认不确定性、会解释原因、会做小范围修正、不会假装已经算准”的专业分析工作台。**


## 4. 任务清单

### C-T1. 真实样本问题台账冻结

目标：
先把这批 `无定形单个样品变温` 的当前状态冻结成专项基线，避免后续一边改一边失去对照。

主要落点：

- `D:\PolyNexus\测试数据\saxs\无定形单个样品变温\polynexus_output`
- `D:\PolyNexus\polynexus\core\analysis_evidence.py`
- `D:\PolyNexus\polynexus\core\saxs_symptom_detector.py`

最小输出：

- 当前样本基线摘要
- 当前症状列表
- 当前 fallback 使用情况
- 当前低置信原因统计

建议记录字段：

- `qstar_contaminated_frame_count`
- `mask_truncated_frame_count`
- `guinier_lost_frame_count`
- `low_conf_frame_count`
- `calibrated_fallback_active`
- `calibrated_fallback_ratio`

验收标准：

- 不看图也能知道这批样本当前坏在哪
- 后续每次修正都能和这份基线比较

推荐模型：`mini`


### C-T2. Raw / Calibrated 双层 evidence 拆分

目标：
把“真实测得值”和“为了温变摘要临时校准出来的值”明确拆开，避免 AI 和 GUI 把 fallback 当真值。

主要落点：

- `D:\PolyNexus\polynexus\core\saxs.py`
- `D:\PolyNexus\polynexus\core\analysis_evidence.py`

最小输出：

- `lc_nm_raw`
- `la_nm_raw`
- `Xc_raw`
- `lc_nm_calibrated`
- `la_nm_calibrated`
- `Xc_calibrated`
- `Q_star_valid_raw`
- `calibrated_fallback_active`
- `calibrated_fallback_reason`
- `fallback_applied_fields`

验收标准：

- `analysis_evidence` 能区分“测得”和“估得”
- 不再出现“frame 级证据说不稳，但 batch 摘要看起来特别稳”的语义冲突

推荐模型：`mini`


### C-T3. 温变批处理回写策略收紧

目标：
不要再让温变批处理把校准值直接覆盖进 `result.structure`，导致后续 evidence / symptom / GUI 都把 fallback 误认成真实输出。

主要落点：

- `D:\PolyNexus\polynexus\core\saxs.py`

最小改动方向：

- 收紧 `_run_temperature_pipeline()`
- 收紧 `_apply_batch_params_to_results()`
- 原始 frame 结果保留真实 `structure` 输出
- calibrated 值只作为 batch summary / recommended overlay / fallback context 暴露

验收标准：

- frame 级对象仍然保有真实原始推导结果
- batch 层可以展示 calibrated 摘要，但不会污染原始证据链

推荐模型：`mini`


### C-T4. 新增温变 SAXS 专项症状

目标：
把这批真实问题从“看起来怪”升级成可以驱动动作和回滚的明确症状。

主要落点：

- `D:\PolyNexus\polynexus\core\saxs_symptom_detector.py`

建议新增症状：

- `temperature_calibration_fallback_active`
- `batch_summary_conflicts_with_frame_evidence`
- `thickness_chain_unreliable`

建议保留并强化的现有症状：

- `beamstop_or_low_q_contamination`
- `idf_artifact_regular_spacing`
- `gamma_tangent_unstable`
- `multi_method_disagreement`

验收标准：

- AI 不再只看到一个 `Low Confidence`
- 系统能明确知道“现在该先修低 q，不该先信 lc/la/Xc”

推荐模型：`mini`


### C-T5. 低 q 污染优先的动作闭环

目标：
让 `orchestrator` 先围绕低 q / correlation / IDF 修复，而不是直接在厚度参数上打补丁。

主要落点：

- `D:\PolyNexus\polynexus\orchestrator.py`
- `D:\PolyNexus\polynexus\core\saxs_action_registry.py`
- `D:\PolyNexus\polynexus\config_bridge.py`

优先动作顺序建议：

1. `adjust_q_crop`
2. `adjust_corr_window`
3. `adjust_idf_smoothing`
4. `switch_lorentz_method`
5. `raise_tangent_floor`

动作约束：

- 优先处理 `beamstop_or_low_q_contamination`
- 若 `calibrated_fallback_active` 为真，则避免过早接受厚度链结果
- 不允许“图更顺眼但证据更假”的候选通过

验收标准：

- 多轮尝试更像“先稳住低 q 证据链”
- 不再一上来就把厚度链当作主要优化目标

推荐模型：`5.4`


### C-T6. 接受 / 回滚规则升级

目标：
让系统按证据改善来收敛，而不是按单个分数或单张图来收敛。

主要落点：

- `D:\PolyNexus\polynexus\orchestrator.py`
- `D:\PolyNexus\polynexus\core\analysis_evidence.py`

建议新增比较项：

- `qstar_contaminated_frame_count`
- `mask_truncated_frame_count`
- `low_conf_frame_count`
- `fallback_ratio`
- `raw_vs_calibrated_gap`
- `stability_score`
- `method_agreement_score`

建议新增回滚条件：

- `low_q_contamination_unresolved`
- `fallback_still_dominant`
- `raw_calibrated_conflict_worsened`
- `thickness_chain_still_unreliable`

验收标准：

- 新结果必须在证据上更可信，才允许替换当前推荐结果
- “更平滑但更假”的结果会自动回滚

推荐模型：`5.4`


### C-T7. GUI 结果语义拆分

目标：
让用户一眼看懂“当前显示的是测得值还是估计值”，减少误判。

主要落点：

- `D:\PolyNexus\polynexus\gui\main_window.py`
- `D:\PolyNexus\polynexus\gui\convergence_viewer.py`
- `D:\PolyNexus\polynexus\gui\i18n.py`

最小界面结构建议：

- 当前可信结果
- 当前保守估计结果
- 当前主要风险
- 已尝试修正
- 为什么仍需要人工复核

最小文案语义建议：

- `Measured result`
- `Calibrated fallback`
- `Low-q evidence unstable`
- `Thickness chain not yet trustworthy`

验收标准：

- 用户不会再把 `lc_nm = 3.07` 自动理解成“厚度趋势已经稳定”
- `Low Confidence` 不再只是压在图上的一句字

推荐模型：`mini`


### C-T8. 真实样本回归验证（已完成）

目标：
让这条专项修复链不只在理想测试样本上成立，也能解释你手上的这批真实温变数据。

主要落点：

- `D:\PolyNexus\tests\test_saxs_symptom_detector.py`
- `D:\PolyNexus\tests\test_saxs_orchestrator_loop.py`
- `D:\PolyNexus\tests\test_saxs_condition_recovery.py`
- 如有必要新增：`D:\PolyNexus\tests\test_saxs_temperature_fallback.py`

最小验证内容：

- 真实样本当前为何低置信
- raw / calibrated 是否已拆开
- symptom 是否能稳定命中
- orchestrator 是否优先修低 q 问题
- GUI 是否明确标识 fallback

验收标准：

- 即使结果暂时还不能完全修好，系统也能把原因讲对
- 若后续某轮真的修好，系统能明确证明“比基线更可信”

推荐模型：`mini`

已完成的回归验证：

- `python -m tests.eval.runner --cases-dir tests/eval/cases/real`
- 结果：`15/15 PASS`
- 真实 SAXS 样本 `saxs_real_temperature_check_20260618`
  - `composite=1.000`
  - `phys=1.000`
  - `peak=1.000`
- `pytest tests/eval/test_runner_real_saxs.py tests/test_saxs_condition_recovery.py tests/eval/test_audit_reporter.py -q`
  - 通过

补充观察：

- `saxs_parameters.csv` 里仍然能看到 `condition_source=header`
- `calibrated_fallback_active` 仍然成立
- `lc_nm_raw` 和 `lc_nm_calibrated` 已经清楚拆开
- 这说明真实样本的语义链已经可以被系统解释，而不是靠图面观感硬猜


## 5. 推荐执行顺序

推荐顺序：

1. `C-T1` 真实样本问题台账冻结
2. `C-T2` Raw / Calibrated 双层 evidence 拆分
3. `C-T3` 温变批处理回写策略收紧
4. `C-T4` 新增温变 SAXS 专项症状
5. `C-T5` 低 q 污染优先的动作闭环
6. `C-T6` 接受 / 回滚规则升级
7. `C-T7` GUI 结果语义拆分
8. `C-T8` 真实样本回归验证

这样排的原因：

- 前三项先让 `core` 说真话
- 中间两项再让 AI 和 orchestrator 有正确目标
- 第六项保证系统不会“越修越假”
- 最后再统一把 GUI 和回归验证收口

当前状态：

- `C-T1` 到 `C-T8` 已完成
- 番外阶段 C 已具备真实样本回归依据


## 6. 模型使用建议

适合 `mini` 的任务：

- 样本基线台账
- evidence 字段拆分
- symptom 规则补充
- GUI 文案和结果面板语义
- 测试补齐和样本回归验证

更适合 `5.4` 的任务：

- 低 q 污染优先的动作闭环设计
- 接受 / 回滚规则升级
- 候选动作排序与证据比较逻辑

简单说：

- 这份专项前半段可以继续用 `mini`
- 真正涉及“动作选择和闭环判据”的 `C-T5 / C-T6` 更适合 `5.4`


## 7. 这份专项的完成标志

番外阶段 C 完成，不等于这批样本一定全部变成高置信。

它真正的完成标志是：

1. 系统能正确地区分“样本真的不稳”与“只是 fallback 抹平了结果”
2. 系统能先修低 q 证据链，再决定是否接受厚度参数
3. 用户能清楚看懂当前哪些结果能信，哪些结果还只是保守估计

只要这三件事站稳，后面的阶段 10 主线就会更扎实，也更像你想要的那种：

**底层可靠、上层有 agent 行为、但不会装作自己已经替用户完成科研判断的专业分析工作台。**


## 8. 阶段 C 收口结论

- 这份专项已经从“问题定位”走到了“真实样本回归验证”
- 代码链、症状链、orchestrator 闭环和 GUI 语义拆分都已经有了对应验证
- 后续如果继续动温变 SAXS 这条链，可以直接拿这份清单和基线台账做对照
