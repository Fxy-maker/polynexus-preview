# PolyNexus 阶段 8 任务清单

## 0. 当前定位

阶段 8 不再继续回答“要不要做 agent”这个问题，因为阶段 6 和阶段 7 已经把方向收得很清楚：

**PolyNexus 继续走“带 agent 行为的专业分析工作台”，但 agent 必须越来越受 core 证据约束。**

阶段 7 已经把“审阅 - 比较 - 再尝试 - 确认”的工作台闭环做出来了。  
阶段 8 的重点不再是把这个闭环做得更热闹，而是把它做得更准：

- 让 core 不只给出结果，还给出更可操作的准确度证据
- 让 AI 不只会建议调参，还会基于这些证据做更靠谱的判断
- 让 orchestrator 不只看 `r_squared`，而是看“这次到底是不是真的更可信”

所以阶段 8 要做的是：

**把 PolyNexus 从“会做受控优化的工作台”，推进到“由 core 证据驱动、能稳定提升处理准确度的工作台”。**

## 0. 阶段 8 起步原则

阶段 8 不建议直接从 AI 联动开工，而是先补一个前置块：

**P8-0. core 约束与证据层前置**

这一步的目标不是重写分析算法，而是先把现有 core 已经有的物理约束、质量信号、残差诊断和跨技术校验收成统一口径。  
只有这样，后面的 orchestrator 和 AI 联动才会建立在“可信证据”而不是“单一分数”上。

P8-0 的原则很简单：

- 先统一证据
- 再统一回退逻辑
- 最后统一 AI 契约

如果这一步没做稳，后面的 AI 再强，也很容易把“拟合分数变高”误当成“结果更准”。

## 1. 为什么现在该做这个阶段

从现有代码看，阶段 8 已经到了很合适的切入点。

当前已经有的地基：

- `core` 已经开始输出多种质量线索
  - `r_squared`
  - `quality_score`
  - `validation_summary`
  - `residual_pattern`
  - `fit_regions`
  - 各技术特有的峰、长周期、焓、峰位等结构化参数
- `orchestrator` 已经具备受控多轮尝试、回退、质量守卫和历史记录
- `prompt_builder` / `advisor` 已经能吃到当前结果、历史、workspace context
- `eval runner` 和 bridge 测试已经起步，WAXS / DSC / IR / SAXS 已经有部分桥接和评分基础
- `joint/validation.py` 已经有跨技术一致性检查能力

但当前还存在几个直接影响“准确度提升”的断点：

1. `orchestrator` 目前主要还是以 `best_r_squared` 为主轴来接受 / 回退候选结果，`quality_guard` 还比较稀疏。
2. AI 虽然能看到一部分上下文，但来自 core 的“硬证据”还没有被整理成统一、稳定、可比较的证据包。
3. `config_bridge` 现在更像“参数范围和依赖规则层”，还不是“诊断症状 -> 相关参数动作”的因果桥。
4. `eval` 的真实引擎覆盖和多技术准确度校验还不够完整，阶段 8 还不能系统证明“联动后确实更准了”。
5. `joint validation` 已存在，但还没有真正进入 AI 和 orchestrator 的主决策回路。

阶段 8 的价值就在这里：

**不是让 AI 更自由，而是让 AI 更受证据约束；不是让 core 更复杂，而是让 core 更能被 AI 正确使用。**

## 1.1 P8-0 前置目标

P8-0 只解决一个问题：

把当前分散在各技术 core、`joint validation` 和结果摘要里的信号，先整理成一份 AI 和 orchestrator 都能稳定消费的“准确度证据包”。

这一前置块的关键词：

- 物理约束
- 证据统一
- 风险分层
- 诊断症状
- 可回退
- 可复现

P8-0 做完以后，阶段 8 后续任务就不再是“猜 AI 应该看什么”，而是“明确 core 已经给了什么证据，系统应该怎样反应”。

## 2. 阶段目标

阶段 8 只解决一个问题：

把 PolyNexus 从“已经具备受控调参能力的分析工作台”，推进到“能通过 core 与 AI 的紧耦合稳定提升结果准确度的分析工作台”。

这一阶段的关键词：

- 准确度优先
- 证据统一
- 复合评分
- 诊断驱动调参
- 评测闭环
- 跨技术一致性
- 可解释回退

## 3. 阶段边界

### 3.1 阶段 8 要做什么

- 把各技术 core 已经产出的质量线索统一组织成 AI 可消费的证据结构
- 让 orchestrator 的接受 / 回退逻辑从“单一分数驱动”升级成“多信号复合判断”
- 把残差模式、物理校验、峰位证据、跨技术一致性逐步纳入 AI 和 orchestrator 的主回路
- 让 AI 的建议更像“针对问题给动作”，而不是“看到低分就泛化调参”
- 扩展 eval / benchmark，让阶段 8 的改进能被测出来，而不是只靠主观感觉

### 3.2 阶段 8 明确不做什么

- 不做无边界自动科研结论生成
- 不做大模型主导、core 退居次要的黑盒系统
- 不做全技术一次性重写分析引擎
- 不做 RL、强化学习代理、自动长链推理平台
- 不把文献问答、远程协作、聊天主界面重构混进本阶段

## 4. 阶段 8 的最小产品模型

阶段 8 的最小模型不是“让 AI 更聪明”，而是先把下面这条准确度链路做稳：

1. core 输出当前结果时，同时输出结构化准确度证据
2. orchestrator 用这些证据判断“该接受、该回退、还是该继续试”
3. AI 只在证据允许的范围内推荐相关参数动作
4. 多轮尝试后，系统能明确解释“为什么这轮更可信”
5. eval / benchmark 能证明阶段 8 的策略比阶段 7 更准，而不是只是更会讲话

只要这条链顺了，PolyNexus 的 AI 就会更像一个“受证据约束的分析助手”，而不是一个只会建议参数的外接模块。

## 5. P8-0 各任务最小闭环

### P8-0-T1. core 物理约束清点

最小用户故事：

用户不需要先知道所有技术细节，但系统内部要先知道：哪些约束是绝对不能破的，哪些只是提醒，哪些只应该作为证据。

这一版只做：

- 按技术清点现有硬约束
  - WAXS：峰位范围、峰宽、结晶度、背景和峰型依赖
  - DSC：温区、焓、峰宽、搜索窗口、`quality_score`
  - SAXS：`q` 窗口、`L` / `lc` 关系、`quality_flag`、`validation_summary`
  - IR / NMR：峰位范围、基线、峰识别、去卷积边界
- 把约束分成三层：
  - `hard_fail`
  - `soft_warn`
  - `evidence_only`
- 不改算法，只整理规则口径

这一版不做：

- 深度重写 core 算法
- 把所有规则一次性统一成复杂物理模型
- 自动发明新的约束

验收标准：

- 每个技术至少能列出自己的硬约束和软约束
- 约束分类能被后续 evidence schema 直接引用
- 不同技术的约束描述开始有统一口径

### P8-0-T2. `analysis_evidence` 最小 schema

最小用户故事：

core 每次输出结果时，不只是返回参数字典，还能返回一份结构化证据包，让后续系统知道“这次结果靠什么站住”。

这一版只做：

- 定义统一的 `analysis_evidence` 结构
- 先包含这些字段：
  - `fit_evidence`
  - `physical_evidence`
  - `residual_evidence`
  - `feature_evidence`
  - `risk_flags`
  - `confidence_signals`
  - `actionable_symptoms`
- 为 WAXS / DSC / SAXS / IR / NMR 各自加轻量 adapter
- 先复用现有输出，不新增重计算

这一版不做：

- 新数据库设计
- 重型特征工程
- 复杂多模态聚合

验收标准：

- 每个技术都能产出同构的 evidence payload
- evidence payload 能直接映射到后续 orchestrator / prompt 输入
- 现有结果逻辑不被破坏

### P8-0-T3. core 证据回归与基线测试

最小用户故事：

用户可以相信，新的证据层不是“写出来好看”，而是能稳定复现、稳定表达核心约束。

这一版只做：

- 为最关键的技术线先补定向测试
  - 优先 `SAXS`
  - 再 `DSC`
  - 然后 `WAXS`
- 测的不是“AI 是否聪明”，而是：
  - 约束是否被正确识别
  - 风险是否被正确分层
  - 证据字段是否稳定输出
  - 明显不合理的结果是否能被拦住或标警告

这一版不做：

- 大规模 benchmark 平台
- 一次性补齐所有边界样本
- 直接评估 AI 生成质量

验收标准：

- core evidence 变动不会悄悄把旧逻辑打坏
- 关键约束的测试可以作为后续联动的安全网
- 阶段 8 后续改动有了明确基线

## 6. 各任务最小闭环

### P8-T1. `core evidence pack` 统一证据层

最小用户故事：

用户跑完一次分析后，系统不只拿到 `parameters + r_squared`，而是拿到一份能描述“这次结果到底靠不靠谱”的统一证据包。

这一版只做：

- 为 WAXS / DSC / SAXS / IR / NMR 定义统一的 `analysis_evidence` 最小 schema
- 优先复用已有输出，不做重型重算：
  - `r_squared`
  - `quality_score`
  - `validation_summary`
  - `residual_pattern`
  - `fit_regions`
  - `quality_flag`
  - technique-specific 核心特征
- 统一最少字段：
  - `fit_evidence`
  - `physical_evidence`
  - `residual_evidence`
  - `feature_evidence`
  - `risk_flags`
  - `confidence_signals`
  - `actionable_symptoms`

这一版不做：

- 重写五套 core 分析算法
- 引入全新的复杂数据库结构
- 一次性做完所有技术的深度学术规则库

验收标准：

- 每个技术线都能稳定产出同构 evidence payload
- orchestrator、prompt builder、eval runner 可以直接消费这份 payload
- 用户结果变好或变差时，系统能指出“哪一类证据变了”

### P8-T2. `orchestrator` 复合目标与回退语义升级

最小用户故事：

AI 推荐了一组参数后，系统不会仅仅因为 `r_squared` 稍微上涨就接受它，而会综合判断这次是否真的更可信。

这一版只做：

- 在 `ParameterOrchestrator` 内引入复合接受目标
- 从“`best_r_squared` 主导”升级到“复合 objective score”
- objective 的第一版只整合已有可用证据：
  - `r_squared`
  - `quality_score`
  - `validation_summary / quality_flag`
  - residual 风险
  - 核心物理约束是否触发
- 给每次回退补明确 reason code，例如：
  - `fit_improved_but_phys_worse`
  - `quality_score_dropped`
  - `validation_risk_increased`
  - `no_meaningful_gain`

这一版不做：

- 黑盒综合分训练器
- 自动学习权重
- 多技术联合最优化器

验收标准：

- 新候选不再只因为 `r_squared` 微升就被保留
- report / history 中能看见每轮接受或回退的结构化原因
- 用户能理解“这轮为什么被系统拒绝”

### P8-T3. `symptom -> parameter` 诊断动作桥

最小用户故事：

当 core 发现的是“峰位错配”“平滑过强”“长周期不稳”“Tm 搜索窗口不合理”这类具体问题时，AI 推荐的参数变化要和问题本身有关，而不是泛化乱试。

这一版只做：

- 为各技术建立最小的“诊断症状 -> 参数动作”映射表
- 优先覆盖最影响准确度的高频问题：
  - WAXS：峰型、背景、峰数、平滑、2θ 偏移
  - SAXS：Bragg 区间、corr 区间、平滑、阈值、拟合方法
  - DSC：搜索窗口、基线、峰函数、平滑、事件阈值
  - IR / NMR：baseline、peak threshold、fit window、lineshape、去卷积相关参数
- 让 AI 的可调参数集合由当前症状裁剪，而不是总把全量 tunable params 暴露给它

这一版不做：

- 复杂因果图谱
- 自动发现参数依赖网络
- 让模型自由发明新参数

验收标准：

- AI 建议与当前 evidence 中暴露的症状更一致
- 无关参数被乱动的情况明显减少
- 同类问题的调参建议开始更稳定、更像工程逻辑

### P8-T4. evidence-driven prompt 与 AI 回合契约

最小用户故事：

AI 在每一轮不只是“看见一堆上下文”，而是明确知道：

- 当前问题是什么
- 哪些证据在变差
- 这轮允许动哪些参数
- 希望改善的是哪类证据，而不只是某个分数

这一版只做：

- 升级 prompt builder 的结构，把 `analysis_evidence` 作为主输入之一
- 要求 AI 输出更严格的回合契约：
  - `hypothesis`
  - `target_symptom`
  - `allowed_changes`
  - `expected_evidence_change`
  - `rollback_condition`
- 保留现有 workspace context，但把 core evidence 前置到更高优先级

这一版不做：

- 长篇链式推理展示
- 开放聊天式 agent
- 绕过 orchestrator 直接执行高风险动作

验收标准：

- prompt 中 core 证据比“叙述性上下文”更核心
- AI 返回的建议更结构化，便于 orchestrator 判断
- 同一类失败模式下，模型输出更稳定

### P8-T5. eval / benchmark 准确度评测扩展

最小用户故事：

阶段 8 做完后，我们不需要只凭感觉说“这次更准了”，而是能在一组固定样例上看到准确度和稳定性确实提升。

这一版只做：

- 扩展现有 eval runner 与 bridge 覆盖
- 优先补足：
  - SAXS
  - IR
  - NMR
  - DSC / WAXS 的更复杂场景
- 增加与阶段 8 目标更一致的评测输出：
  - baseline vs tuned 的 objective 对比
  - accept / rollback 原因分布
  - 物理约束命中率
  - 症状修复命中率

这一版不做：

- 一次性构建海量 benchmark 平台
- 自动标注工厂
- 全面替代人工审阅

验收标准：

- 至少有一组固定 benchmark 可以复现阶段 8 收益
- “更准”不再只等于“r_squared 更高”
- 能发现不同技术线在 accuracy 提升上的薄弱点

### P8-T6. 跨技术一致性回流到单技术优化

最小用户故事：

当同一样品已经有多技术数据时，单技术调参不应该假装自己活在孤岛里，而应该知道当前结果是否和其他技术线冲突。

这一版只做：

- 把 `joint/validation.py` 的校验结果转成可消费的 evidence / workspace context
- 让 orchestrator / AI 能看到最关键的跨技术警告：
  - `phi_c` 不一致
  - `Tm` 双向校验异常
  - `L` 一致性不稳
- 只把这些结果作为“提醒、惩罚或回退信号”，不做多技术联合自动优化

这一版不做：

- 联合多技术一起自动搜索参数
- 自动跨 batch 改历史结果
- 远程协作式会签判断

验收标准：

- 当跨技术存在明显冲突时，AI 和 orchestrator 不再继续把单技术局部最优误判为全局更优
- 用户能看到“这次结果在单技术内变好了，但和别的技术还不一致”

### P8-T7. 准确度回归与阶段边界固化

最小用户故事：

阶段 8 做完后，用户会感受到系统更重视“结果到底准不准”，但不会觉得系统变成了另一个黑盒评分器。

这一版只做：

- 为 evidence pack、复合 objective、诊断动作桥、prompt 升级、eval 扩展、跨技术回流补定向回归
- 再次固化边界：
  - core 负责提供证据
  - AI 负责提出有限动作假设
  - orchestrator 负责受控试验与回退
  - 用户仍然负责最终科研判断

这一版不做：

- 大规模全链路自动优化平台
- 全量 UI 重构
- 让 AI 直接替代 core 的计算判断

验收标准：

- 新链路提升准确度时不会明显破坏稳定性
- 关键主链路仍可取消、回退、解释
- 新能力不会制造“AI 比 core 更重要”的错觉

## 6. 推荐顺序

阶段 8 推荐执行顺序：

1. `P8-T1 core evidence pack 统一证据层`
2. `P8-T2 orchestrator 复合目标与回退语义升级`
3. `P8-T3 symptom -> parameter 诊断动作桥`
4. `P8-T4 evidence-driven prompt 与 AI 回合契约`
5. `P8-T5 eval / benchmark 准确度评测扩展`
6. `P8-T6 跨技术一致性回流到单技术优化`
7. `P8-T7 准确度回归与阶段边界固化`

原因：

- T1 先统一证据，不然后面都还是各说各话
- T2 先让系统内部的接受 / 回退逻辑变得更准，避免 AI 再聪明也喂给错误目标
- T3 / T4 再让 AI 的动作空间和思考输入真正围绕证据组织
- T5 用 benchmark 把收益量化出来
- T6 最后把跨技术一致性引回来，避免一开始复杂度过高
- T7 收口做回归和边界固化，防止阶段越做越散

## 7. 阶段回归底线

阶段 8 每完成一个任务，至少检查：

1. 同一输入 + 同一配置下，core 结果仍然稳定可复现
2. orchestrator 仍然可取消、可回退、可解释
3. 新候选不会只因为 `r_squared` 上升就被无条件接受
4. AI 不会绕过参数范围、依赖规则和高风险约束
5. history / export / work memory 仍能正确表达结果来源与确认状态
6. eval benchmark 至少能覆盖阶段 8 改动触达的主技术线

## 8. 阶段完成定义

满足下面条件即可视为阶段 8 完成：

- core 能稳定产出统一、可消费的准确度证据
- orchestrator 的接受 / 回退逻辑不再过度依赖单一 `r_squared`
- AI 的建议开始明显更贴近具体诊断症状
- benchmark 能证明阶段 8 的联动比阶段 7 更准
- 产品仍然保持“core 是根、AI 是受约束助手、用户掌握最终判断”的边界

## 9. 对你这个项目最重要的阶段判断

如果只用一句话概括阶段 8：

**阶段 8 不是继续把 AI 做强，而是把“core 的证据”做成 AI 必须服从的硬约束。**

这一步做好了，后面不管你继续往“更强 agent 行为”走，还是继续往“更专业的分析工作台”走，地基都会稳很多。
