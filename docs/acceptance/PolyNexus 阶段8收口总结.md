# PolyNexus 阶段 8 收口总结

## 1. 阶段定位回顾

阶段 8 的目标不是把 PolyNexus 变成一个更像聊天机器人的系统，而是继续把它往这个方向推稳：

**底层是可靠的分析软件，上层逐步加入 agent 能力，agent 负责建议、串流程、组织上下文，最终判断仍由用户完成。**

这一阶段最重要的变化，不是“AI 说得更多了”，而是“core 的证据、orchestrator 的回退、AI 的动作建议、评测口径”终于开始对齐了。

## 2. 本阶段已完成内容

- [x] `P8-T1 core evidence pack 统一证据层`
  - 把 core 输出整理成可消费的 evidence / workspace context
  - 让后续 AI 与 orchestrator 不再只看零散参数

- [x] `P8-T2 orchestrator 复合目标与回退语义升级`
  - 让 accept / rollback 不再只跟单一 `r_squared` 绑定
  - 复合 objective、约束命中、症状修复开始进入决策链

- [x] `P8-T3 symptom -> parameter 诊断动作桥`
  - 为 WAXS、SAXS、DSC、IR、NMR 等技术建立了最小症状到参数动作的映射
  - AI 可调参数集合开始按症状裁剪，不再全量乱试

- [x] `P8-T4 evidence-driven prompt 与 AI 回合契约`
  - prompt 里把 `analysis_evidence` 提到主输入位置
  - AI 输出更结构化的回合契约，便于 orchestrator 受控判断

- [x] `P8-T5 eval / benchmark 准确度评测扩展`
  - baseline vs tuned 的 objective 对比落到了 eval 结果里
  - 增加了 accept / rollback 原因、约束命中率、症状修复命中率

- [x] `P8-T6 跨技术一致性回流到单技术优化`
  - 把 joint validation 的冲突信号回流到单技术调参链路
  - 避免单技术局部最优被误判成全局更优

- [x] `P8-T7 准确度回归与阶段边界固化`
  - 为本阶段的主链路补了定向回归
  - 再次明确 core / AI / orchestrator / user 的职责边界

## 3. 本阶段的额外可见成果

除了任务单中的主目标，这一阶段还把调参报告窗往前推了一步：

- 调参报告现在能直接展示 benchmark 摘要
- 用户能更快看到 objective delta、接受率、回退率、约束命中和症状修复情况
- 这让“这次为什么更准”从后台统计变成了前台可见信息

## 4. 阶段 8 的实际产物

阶段 8 做完后，PolyNexus 不再只是“能调参”，而是开始具备一个更完整的受控分析闭环：

1. core 给出证据
2. AI 根据证据提出有限动作假设
3. orchestrator 负责试验、评价和回退
4. benchmark 负责把收益和边界讲清楚
5. 用户仍然做最终科研判断

这比“让 AI 直接给结论”更稳，也更符合这个项目现在的产品定位。

## 5. 为什么现在可以收口

阶段 8 已经把最重要的几件事跑通了：

- 评测口径更靠近真实准确度，而不是单一分数
- 跨技术冲突不会再被轻易忽略
- AI 的动作空间开始和症状强绑定
- orchestrator 的回退语义更像一个可解释的受控试验层

继续在阶段 8 内扩展，已经会越来越像边角补丁，不再是这个阶段最核心的收益。

## 6. 仍然保留的边界

阶段 8 完成，不代表 PolyNexus 变成了：

- 全自动科研决策系统
- 无边界自由搜索优化器
- 独立聊天式 agent 平台
- 直接替代 core 物理判断的黑盒评分器

这些仍然不是当前产品方向。

## 7. 已完成回归

阶段 8 收口时，已经跑过的关键回归包括：

- `python -m py_compile polynexus/orchestrator.py rag/prompt_builder.py tests/eval/runner.py tests/eval/audit_reporter.py tests/eval/test_eval_phase01.py tests/eval/test_audit_reporter.py tests/test_prompt_builder.py tests/test_orchestrator.py`
- `pytest -q tests/eval/test_eval_phase01.py tests/eval/test_audit_reporter.py tests/test_prompt_builder.py tests/test_orchestrator.py -q`
- `pytest -q tests/test_main_window_persistence.py -k "ai_tuning_workspace_context or ai_tuning_report_summary or ai_tuning_report_decision_summary or ai_tuning_report_benchmark_summary" -q`

## 8. 收口结论

阶段 8 的核心判断已经成立：

**PolyNexus 现在更像一个证据驱动的专业分析工作台，而不是一个只会看单分数的调参器。**

接下来如果继续往前走，最自然的方向不是继续堆更多“AI 说法”，而是把这些证据、benchmark 和回退语义，进一步做成更顺手的工作台交互。

