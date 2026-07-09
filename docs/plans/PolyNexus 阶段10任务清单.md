# PolyNexus 阶段10任务清单

## 0. 当前定位

阶段 10 不再讨论“要不要做 agent”。

当前产品定位已经明确为：

**带 agent 行为的专业分析工作台**

也就是：

- 底层仍然是可靠的分析软件
- 上层逐步加入 agent 能力
- agent 负责建议、组织上下文、串起复核流程
- 最终科研判断仍由用户完成

阶段 10 的主题只有一个：

**把 core 与 AI 的联动，从“会给建议”推进到“证据驱动的受限闭环”。**

本阶段优先技术线：`SAXS`


## 1. 阶段目标

阶段 10 要完成 5 件事：

1. `core` 不只给结果，还要给出可复核的证据包
2. 系统先识别“症状”，再决定是否让 AI 参与下一步
3. AI 只能做诊断排序和动作选择，不能直接越权改整套 core
4. `orchestrator` 能围绕一个具体问题做小范围受限重跑，并在必要时回滚
5. GUI 要把“发现了什么问题、尝试了什么修正、为什么推荐当前结果”讲清楚


## 2. 阶段边界

### 2.1 本阶段要做什么

- 以 `SAXS` 为样板线，建立 `core -> evidence -> symptom -> AI action -> rerun -> rollback -> review` 的闭环
- 扩充 `analysis_evidence`，让 AI 不依赖看图也能判断结果是否可信
- 为 `SAXS` 建立症状检测层和动作白名单
- 升级 `orchestrator`，让它围绕症状做受限试探，而不是只收一条裸参数建议
- 把低置信结果改造成“原因可追溯”的复核体验

### 2.2 本阶段明确不做什么

- 不做独立聊天式 agent 主界面
- 不做无限轮自动优化器
- 不把最终科研判断交给 AI
- 不在这一阶段重写全部技术线
- 不为了追求“AI 感”而牺牲工作台的稳定和可解释性


## 3. 阶段最小闭环

阶段 10 的最小可交付闭环如下：

1. `core` 输出一组可复核的数据证据
2. 系统先用规则层识别当前症状
3. AI 基于症状和证据，选择有限动作
4. `orchestrator` 只试少量受限变体
5. 如果结果更稳、更可信，则提升为推荐结果
6. 如果结果更差或不稳定，则自动回滚并保留原因
7. GUI 把这条判断链展示给用户

只要这条链打通，PolyNexus 的 agent 行为就会更像“受证据约束的分析助手”，而不是一个只会泛泛调参的外挂模块。


## 4. 主线任务清单

### P10-T1. SAXS evidence pack 扩充

目标：
把 SAXS 结果从“参数字典”升级成“证据包”。

主要落点：

- `D:\PolyNexus\polynexus\core\analysis_evidence.py`
- `D:\PolyNexus\polynexus\orchestrator.py`
- `D:\PolyNexus\polynexus\core\saxs.py`
- `D:\PolyNexus\polynexus\core\saxs_engine\core.py`

最小输出：

- `signal_evidence`
- `peak_evidence`
- `transform_evidence`
- `structure_evidence`
- `batch_evidence`
- `condition_evidence`

验收标准：

- 不打开图片，也能知道当前结果为什么可信或不可信
- `analysis_evidence` 能直接进入 `orchestrator` 和 `prompt_builder`

推荐模型：
`mini`


### P10-T2. 条件轴恢复证据链

目标：
让 `Check-xxxx.edf` 这类批量样本在温度/应变轴缺失时，系统能说清楚“轴是怎么恢复出来的”。

主要落点：

- `D:\PolyNexus\polynexus\core\saxs_engine\io.py`
- `D:\PolyNexus\polynexus\core\saxs.py`

最小输出：

- `condition_source`
- `condition_confidence`
- `condition_missing_frames`
- `condition_continuity_score`

验收标准：

- 批次分析结果中能明确看到条件值来源
- 条件轴是“可靠恢复”还是“弱推断”要能区分

推荐模型：
`mini`


### P10-T3. SAXS symptom detector

目标：
在 AI 之前加一层确定性症状检测器，避免模型从零盲猜。

建议新增文件：

- `D:\PolyNexus\polynexus\core\saxs_symptom_detector.py`

第一批症状：

- `condition_axis_missing`
- `condition_axis_unstable`
- `batch_mixed_samples`
- `beamstop_or_low_q_contamination`
- `peak_window_mismatch`
- `idf_artifact_regular_spacing`
- `gamma_tangent_unstable`
- `multi_method_disagreement`

验收标准：

- 低置信结果能拆成具体症状
- 症状输出稳定、可测试、可追溯

推荐模型：
`mini`


### P10-T4. symptoms 接入 orchestrator 状态

目标：
让每一轮调参都明确“当前针对的到底是什么问题”。

主要落点：

- `D:\PolyNexus\polynexus\orchestrator.py`

最小改动：

- `_build_agent_state()` 增加 `symptoms`
- `_score_snapshot()` 与历史记录带上症状语义
- 回滚原因不再只有泛化分数解释

验收标准：

- 每轮记录都能看到目标症状
- “为什么被拒绝/回滚”更具体

推荐模型：
`mini`


### P10-T5. SAXS 动作白名单

目标：
AI 不能自由乱改参数，只能从受控动作模板里选。

建议新增文件：

- `D:\PolyNexus\polynexus\core\saxs_action_registry.py`

第一批动作：

- `adjust_q_crop`
- `adjust_peak_window`
- `adjust_corr_window`
- `adjust_idf_smoothing`
- `switch_lorentz_method`
- `raise_tangent_floor`
- `rerun_condition_recovery`
- `split_batch_by_sample`
- `mark_frame_outlier`

验收标准：

- AI 输出不再直接暴露成任意 `changes`
- 动作和症状之间存在明确对应关系

推荐模型：
`5.4`


### P10-T6. Prompt / Advisor 升级为动作契约

目标：
把 AI 从“泛建议”收紧成“诊断 + 动作选择器”。

主要落点：

- `D:\PolyNexus\rag\prompt_builder.py`
- `D:\PolyNexus\rag\advisor.py`

新的最小输出 schema：

- `diagnosis`
- `target_symptom`
- `recommended_actions`
- `expected_evidence_change`
- `rollback_condition`
- `converge`

验收标准：

- prompt 更工程化，少空话
- 模型输出稳定成结构化动作

推荐模型：
`5.4`


### P10-T7. 受限重跑执行层

目标：
让 `orchestrator` 真正围绕一个症状试少量受限变体，而不是只收一条建议然后硬跑。

主要落点：

- `D:\PolyNexus\polynexus\orchestrator.py`
- `D:\PolyNexus\polynexus\config_bridge.py`
- `D:\PolyNexus\polynexus\core\saxs_action_registry.py`

最小行为：

- 每轮只展开 2 到 5 个受控候选
- 每个候选都有动作来源和目标症状
- 候选失败时自动回滚

验收标准：

- 多轮优化更像“针对问题的小范围实验”
- 失败的尝试不会污染当前最佳结果

推荐模型：
`5.4`


### P10-T8. 稳定性评分与回滚升级

目标：
避免“看起来拟合更好，但结果其实更脆”的假提升。

主要落点：

- `D:\PolyNexus\polynexus\orchestrator.py`
- `D:\PolyNexus\polynexus\core\analysis_evidence.py`

建议加入：

- `parameter_stability_score`
- `method_agreement_score`
- `batch_continuity_score`

新增回滚条件：

- `condition_continuity_worsened`
- `structure_jump_too_large`
- `symptom_unresolved`
- `new_hard_fail_introduced`
- `stability_score_dropped`

验收标准：

- 推荐结果不只分数更高，还要更稳
- 不稳定结果会自动降级成“需人工复核”

推荐模型：
`5.4`


### P10-T9. GUI 结果复核工作台化

目标：
把“AI 味很重的提示”改造成真正好用的复核界面。

主要落点：

- `D:\PolyNexus\polynexus\gui\convergence_viewer.py`
- `D:\PolyNexus\polynexus\gui\main_window.py`
- `D:\PolyNexus\polynexus\gui\i18n.py`

界面最小结构：

- 检测到的问题
- 已尝试的修正
- 当前推荐结果
- 推荐依据与剩余风险

验收标准：

- 用户一眼能明白当前结果的用处
- `Low Confidence` 不再只是压在图上的一句字

推荐模型：
`mini` 负责界面实现，`5.4` 适合定信息架构和文案结构


### P10-T10. 测试与真实样本巡检

目标：
让这条闭环不只在理想输入上成立，也能抗住真实数据。

建议新增测试：

- `D:\PolyNexus\tests\test_saxs_symptom_detector.py`
- `D:\PolyNexus\tests\test_saxs_action_registry.py`
- `D:\PolyNexus\tests\test_saxs_orchestrator_loop.py`

真实样本优先队列：

- `无定形单个样品变温`
- `pa6变温`
- `Check-xxxx.edf`
- 多样品混在同一文件夹的批次目录

验收标准：

- 每种高频症状至少有一个可复现用例
- 真实样本问题能被解释，不只是“分数变了”

推荐模型：
`mini` 做测试和巡检，复杂策略分歧时切 `5.4`


## 5. 番外阶段设计

### 番外阶段 A. 真实样本巡检与快修

定位：
用于处理主线推进中暴露出的高频真实问题，但不打乱主线阶段编号。

适用场景：

- 样本能跑，但结果解释明显不对
- GUI 展示让用户误判
- 某个真实目录结构与假设不一致
- 条件轴、批次、低置信提示影响用户判断

番外任务建议：

- `A-T1` 真实样本问题台账
- `A-T2` 条件轴缺失恢复快修
- `A-T3` 多样品目录拆分与分组快修
- `A-T4` 低置信提示改造成原因链

边界：

- 可以插队处理
- 只修阻塞判断的问题
- 不在番外阶段偷偷扩大主线范围


### 番外阶段 B. 工作台实用性修补

定位：
在不重做大界面的前提下，持续削弱“AI 感太重、工作台感太弱”的问题。

适用场景：

- 面板命名抽象
- 操作路径不清晰
- 信息密度失衡
- 结果卡片只会提醒，不会解释

番外任务建议：

- `B-T1` 面板命名与中文文案清理
- `B-T2` 复核入口与下一步动作显性化
- `B-T3` 历史链路和当前推荐的区分强化
- `B-T4` 结果摘要卡从“AI 判断”改成“复核摘要”


## 6. 推荐执行顺序

推荐顺序：

1. `P10-T1` SAXS evidence pack 扩充
2. `P10-T2` 条件轴恢复证据链
3. `P10-T3` SAXS symptom detector
4. `P10-T4` symptoms 接入 orchestrator
5. `番外阶段 A-T1` 真实样本巡检台账
6. `P10-T5` SAXS 动作白名单
7. `P10-T6` Prompt / Advisor 契约升级
8. `P10-T7` 受限重跑执行层
9. `P10-T8` 稳定性评分与回滚升级
10. `番外阶段 B` 工作台实用性修补
11. `P10-T9` GUI 结果复核工作台化
12. `P10-T10` 测试与真实样本巡检收口

这样排的原因：

- 前四项先让系统知道“自己出了什么问题”
- 中段再让 AI 和 orchestrator 参与闭环
- 番外阶段负责接住真实样本和产品感问题
- 最后再统一收口 GUI 与测试


## 7. 模型使用建议

适合 `mini` 的任务：

- evidence 字段整理
- symptom 规则实现
- 测试补齐
- GUI 细化与文案清理
- 真实样本巡检与问题复现

更适合 `5.4` 的任务：

- 动作白名单设计
- prompt 契约重构
- orchestrator 评分与回滚策略
- 稳定性判据和候选接受逻辑

简单说：

- 前半段打地基，`mini` 足够
- 中段涉及“策略设计和闭环判据”，更适合 `5.4`
- 后半段测试、落地、巡检，`mini` 又能继续接住


## 8. 本阶段的开工点

阶段 10 建议从下面 4 项起步：

- `P10-T1` SAXS evidence pack 扩充
- `P10-T2` 条件轴恢复证据链
- `P10-T3` SAXS symptom detector
- `P10-T4` symptoms 接入 orchestrator

这四项做完后，系统就会从“会给建议”进入“知道自己哪里不对”。

这也是后续动作白名单、受限重跑和 GUI 复核工作台能真正站稳的前提。
