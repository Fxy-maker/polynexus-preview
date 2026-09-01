# Codex–PolyNexus–ARS 研究闭环验收 — 2026-09-01

## 结论

本任务实现了一个项目级、可恢复的研究任务外壳。Codex/CLI 负责编排，
PolyNexus `ProjectWorkflowService` 负责确定性分析，Suite/ARS 负责论文资料
投递与审查；三者只通过现有的 `ProjectWorkflowRun`、`ComputeRun`、证据包和
论文 DTO 传递科学对象，没有新增一套 AI 私有数值或证据模型。

任务状态可以从磁盘恢复，但验收不等于论文科学结论已获批准：真实回放在
ARS handoff 后保留为 `ars_in_progress`，因为实际 ARS 写作运行时和人类科学
审查仍未执行。

## 小型 fixture 完整回放

fixture 位于 `tests/fixtures/research_loop/raw/IR/spectrum.csv`，是一个带
`Wavenumber,Absorbance` 表头的四行 IR 光谱。完整生命周期由
`tests/test_research_loop_integration.py` 覆盖：

```text
create → inspect → propose_mapping → confirm_mapping → run
→ checkpoint → handoff_to_ars → record_ars_actions
→ resolve_action → recompute → second checkpoint/handoff
→ submission_preflight → complete_export → reload
```

该回放验证了两次分析使用不同的不可变 run/package/handoff ID；`edit` 不触发
Core 重算，`recompute` 回到 PolyNexus 并产生新 run，`ask_human` 会暂停任务。
正式预检在完整 ARS、方法、Zotero/引用、可见文本和可追溯性都满足时才允许
进入 `export_ready`；导出文件缺失时仍拒绝完成。

## 恢复、哈希和篡改边界

- `ResearchTask`/`ResearchAction` 通过 canonical JSON 保存内容哈希、父 revision
  和 append-only 文件；旧 revision 不被覆盖。
- 最新指针损坏或尾部 revision 写入不完整时，store 回退到最后一个有效链节；
  有效链内的父 revision/hash 不匹配、任务身份篡改、action 身份篡改和非法
  resolution sibling 均 fail closed。
- 相同 resolution 的重放是幂等的；若 action sibling 已落盘而 task head 尚未
  推进，重放会修复 task head；不同 resolution 不会覆盖已有决定。
- 新版证据包的 manifest hash、包内复制文件 hash、package path、run ID 和
  task ID 在 Suite handoff 处重新校验。包内容或运行归属被改写时 handoff 被
  阻断；无 `package_hash` 的历史包保留只读兼容行为。
- 每个 task-bound run 的 `runs/<run_id>.json` 必须在 package manifest 中精确
  出现，文件内 `run_id` 与 `request_parameters.research_task_id` 必须一致；
  缺失、错配或无 task owner 的 run 不能 handoff。
- handoff 在写入任何 ARS 记录之前强制要求 `manifest.json` 存在，并要求其
  `package_hash` 为合法值且与 handoff payload 一致；兼容 provider 不能用一个
  没有 manifest 的 `ready` 返回污染 task 状态。
- artifact hash 使用 1 MiB 流式 SHA-256 计算，完整性校验不会把多 GB 证据包
  全量读入内存。

## 隔离与共享对象

同一项目可以有多个 `ResearchTask`。任务只保存 source/run/package/handoff
引用；working evidence 冻结时按当前 task 的 run ID 交集过滤，不能把另一任务
的 run 混入包。GUI Quick Analysis 的临时附件不在研究任务 inventory 中，只有
用户明确提供正式 source scope 才能进入 mapping。

项目库存中的相对 artifact ID 与绝对路径 artifact ID 在进入 ComputeRun 前有
显式、哈希校验的 alias；跨文件或过期哈希不会被静默接受。这保留了现有 GUI、
CLI、Codex 和 ARS 使用同一公共 DTO 的边界。

## 真实“弹性体中文”只读回放

原始来源没有被修改。回放从以下文件复制到派生临时项目后执行：

```text
来源：C:\Users\Fan Xuyi\Desktop\文件夹\弹性体\弹性体中文\raw\nmr\PA6-H.csv
派生：D:\PolyNexus-real-project-replay-final-20260831-v3
```

来源文件特征为无表头、制表符分隔、131071 行；第一列是 chemical shift，
第二列是 intensity。只读源 SHA-256 为：

```text
b371a7beff3d35d556e4a1dd52f8c6efdbb1c25eba13862d53a78759413a98c4
```

用户确认的 mapping 为 `chemical_shift`（ppm）/`intensity`，行范围
`0..131070`，inventory artifact ID 为
`efc570504127c7a47db30b2d1af66c7278f6940e74cd3abbff6ad6f0ce32feac`，并绑定
`request_parameters.submodule_id = nmr.liquid_h`。真实回放产生：

| 对象 | 结果 |
|---|---|
| ResearchTask | `real-pa6h-nmr-loop`，revision 8，`ars_in_progress` |
| ComputeRun | `run-6f193af9f6c1725d560e22b8`，NMR liquid 1H，`review_required` |
| Evidence package | `research-real-pa6h-nmr-loop-v001`，1 run、1 evidence、3 figures，`review_required` |
| ARS handoff | `handoff-847c410852d886b3`，`ready`，绑定上述 package/run |
| 人工审查 | 1 条 `human_scientific_review`，状态 `pending` |

该回放只证明文件映射、确定性运行、证据冻结和 handoff 可重放；它不证明峰
归属、样品组成、氢键物种、结晶机制或任何定量论文结论。包中保留的限制包括
`unique_hydrogen_bond_species` 和无背景时的绝对散射量限制。

## blocked / review_required 的含义

`blocked` 用于输入、身份、哈希、状态转换、包绑定或人工拒绝等安全边界，
不会用默认值替代缺失科学信息。`review_required` 表示分析结果已经保留，
但需要 provider 适用性、方法、证据或科学审查；它不是失败，也不能被 AI
自动升级为可投稿结论。正式论文导出还必须经过 Suite 的严格
`submission_preflight`，包括 ARS 完成、方法和引用/Zotero 验证、claim-to-source
可追溯性、可见文本审计和版式检查。

## ARS 与人工边界

当前仓库实现的是稳定协议和持久化边界，不声称已经调用外部/安装的 ARS 模型。
实际 ARS 运行、文献在线核验、mapping/peak assignment、材料组成和机制判断、
最终稿件批准仍需相应运行时或人类完成。所有这些未完成项会在 task revision、
review-decision 和 preflight 中显式保留，不能通过重放或改写旧证据包绕过。

`record_ars_completion()` 保存的是本地可重放的 ARS 返回收据：它同时绑定 task、
handoff hash、package hash 和完整 action 集。正式预检只接受该持久化收据，且新
handoff 或新 action 会使旧收据失效；稿件 JSON 自称 `ars_workflow.completed` 不会
被信任。这一记录证明本地流程已接收并锁定相应的结构化返回，不构成远程 ARS
身份、模型执行或文献联网核验的证明。

## 验收文件与限制

本次新鲜验证结果：研究闭环及受影响消费者矩阵 `223 passed, 3 skipped`；
`python scripts/verify.py --task docs/agent/tasks/2026-08-31-codex-ars-research-loop.md --changed --types`
通过（任务卡、记忆、Ruff、编译、质量 `313`、预处理 `157`）；独立 Ruff 与
`git diff --check` 通过。

实现与回归测试见 task card
`docs/agent/tasks/2026-08-31-codex-ars-research-loop.md`。真实回放输出留在上述
派生目录；真实 raw、旧 immutable package、manuscript 和其他任务产生的运行时
文件均未纳入本 checkpoint。仓库全量历史测试仍可能包含其他任务已记录的失败；
本验收只对本闭环的聚焦矩阵和 task-scoped verifier 作结论。
