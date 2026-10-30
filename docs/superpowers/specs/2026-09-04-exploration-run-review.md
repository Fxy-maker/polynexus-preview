# ExplorationRun 安全、架构与科学语义审查

日期：2026-09-04
范围：`ExplorationExecutorDescriptor`、`ExplorationRequest`、
`ExplorationRun`、`ExplorationRunner`、`ExplorationRunStore`，以及未来的
Codex/GUI/CLI、自动参数探索、Evidence Package 和 capability 晋升边界。

## 结论

当前 v1 可以作为“可信内置执行器的开发期探索通道”保留，但不能进入
“Codex 生成代码并执行”或“自动论文证据”阶段。当前实现没有
`eval`/`exec`、动态导入、子进程或网络执行路径，且运行结果使用共享
`ProviderResultInput`、metric manifest 和追加式哈希存储；这部分安全基线是
正确的。

不过，当前请求仍可只携带 raw artifact ID/hash，未强制绑定
`CanonicalDataset`/`CanonicalExperiment`；descriptor 的输入/输出契约也未在
runner 中实际校验。因此若将注册入口开放给 AI，仍可能绕过 canonical
校验，或产生“结构上 computed、科学上未满足声明契约”的结果。

## 分级结果

### P1：下一阶段前必须解决

1. **SEC-01：可信 callable 边界未形成不可信代码沙箱**
   `ExplorationExecutorRegistry.register()` 接受任意 callable
   (`polynexus/core/exploration/runner.py:33-45`)。当前没有 Codex 注册入口，
   所以不是现有远程漏洞；但一旦把 AI 生成函数、插件或用户代码直接注册到
   当前进程，函数可以读取进程内存、环境变量、项目外文件，或永久占用线程。
   结论：不得把此 registry 当作 sandbox。通用代码必须转移到独立受限进程/容器
   或虚拟机，并关闭网络、清空 secrets、只读挂载输入、限制 CPU/内存/墙钟时间、
   输出大小和系统调用。

2. **SEC-02：implementation_hash 目前是声明，不是执行体证明**
   descriptor 只校验调用者提供的 64 位字符串
   (`contracts.py:107-136`)；registry 没有验证 callable 所属模块/包的实际
   内容是否等于该 hash。恶意或误配置注册者可以给任意代码贴上已知 hash。
   结论：未来插件/沙箱加载器必须对不可变源码或 wheel/源码包做实际摘要，记录
   依赖锁和运行时版本；不能把调用者自报的 hash 当作代码证明。

3. **ARCH-01：探索请求可绕过 canonical 数据边界**
   `ExplorationRequest` 只要求 source artifact ID/hash
   (`contracts.py:236-359`)，`parent_run_id` 还是可选；runner 不接收或验证
   `CanonicalDataset`、模板 hash、轴 provenance、校准和 DataBlock
   (`runner.py:63-101`)。这与“AI 不能绕过 canonical validation”的总原则不一致。
   结论：开放 CLI/GUI/Codex 前，request 必须绑定已验证的 canonical dataset/
   experiment identity；若要支持 raw exploratory ingest，也必须先经过一个
   明确的 canonical 转换记录，不能靠自报 source hash。

4. **ARCH-02：descriptor 的 input/output contract 尚未成为执行门**
   descriptor 保存了 input/output contract
   (`contracts.py:96-132`)，但 runner 只检查 technique、源 ID/hash 和
   `ComputationState`，没有校验参数类型/单位/范围，也没有检查输出 metric
   paths、单位、形状、方法或 descriptor_id 是否匹配
   (`runner.py:69-101`)。因此一个未声明的 metric 也可能进入 `completed`。
   结论：先实现严格、版本化的参数 schema 和 provider-result output schema
   validator，失败时保留 failed run，不得进入 completed/evidence。

5. **SCI-01：computed 不等于科学上可解释**
   `_completed_state()` 将 provider 的 computed 状态改投影为
   `promotion=review_required` (`contracts.py:76-89`)，这避免了自动发表，
   但没有证明轴、单位、校准、适用范围、误差或方法假设满足探索 descriptor。
   结论：每个探索 descriptor 需要声明并实际验证这些条件；缺失时输出仍可保留，
   但必须是 `needs_input`/`diagnostic_only`，不能仅凭数值存在而算作可用科学量。

### P2：进入产品集成前必须解决

6. **SEC-03：没有资源、超时和输出大小限制**
   runner 直接调用 callable (`runner.py:76-83`)，没有墙钟、CPU、内存、输出
   或递归深度限制。即使只加载可信内置算法，意外死循环或巨大 metric payload
   也能阻塞 GUI/CLI 或耗尽磁盘。批量入口前应使用受限 worker，并在 Core 层设
   明确预算。

7. **SEC-04：源 hash 是请求声明，未与实际源对象重新解析**
   runner 只比较 provider provenance 中的
   `source_content_hash` 与 request 字段 (`runner.py:88-93`)。这能防止结果与
   请求互相矛盾，但不能证明该 hash 真来自项目中的文件。AI 不能自行构造
   artifact identity；入口应从已加载的 `RawArtifact`/canonical manifest 派生
   identity，并在执行前重新验证当前内容 hash。

8. **ARCH-03：descriptor hash、依赖和运行环境未进入 request/run identity**
   request 保存 executor ID、version、implementation hash，但不保存
   `descriptor_hash`、依赖锁、Python/数值库版本、随机种子或校准 identity
   (`contracts.py:236-359`)。同一实现 hash 下改变声明契约或依赖环境，可能产生
   无法解释的差异。应把这些内容作为不可变执行上下文并进入 cache/run hash。

9. **ARCH-04：相同 request 的非确定性重试无法表达为独立尝试**
   `run_id` 只由 request_id 派生 (`contracts.py:532-534`)；若同一请求因随机
   初始化、线程调度或外部数值库产生不同结果，第二次只能与同一 run ID 冲突，
   不能保留为独立 attempt。自动探索需要显式 seed/attempt identity，并保留每次
   尝试及其停止/重试原因。

10. **ARCH-05：无效 manifest 在 list_runs() 中被静默跳过**
    `ExplorationRunStore.list_runs()` 捕获 `ValueError` 后直接 continue
    (`storage.py:63-70`)。这便于普通 UI 读取，但不适合完整性审计：损坏或被
    篡改的记录可能从列表中消失。应提供显式 invalid-records/diagnostics 视图，
    在证据打包和审计模式下 fail closed。

11. **ARCH-06：尚未与 Evidence Package 形成正式共享输入**
    `to_evidence_item()` 只生成现有 `EvidenceItem`
    (`contracts.py:596-626`)；当前 `ProjectEvidencePackager` 仍要求
    `ProjectWorkflowRun`、`AnalysisRun` 和 recipe manifest。直接把 ExplorationRun
    塞进旧 package 会迫使系统伪造 ComputeRun 或绕过 `_validate_run()`。结论：应
    增加明确的 exploration-run snapshot/member contract，逐个校验 run/request/
    source/descriptor/result hash，再由 Codex 明确选择哪些项进入 package。

12. **SCI-02：探索结果投影过宽，不能直接送入 ARS**
    evidence adapter 把完整 provider result、metric manifest 和 provenance 放入
    `observed_results`，但没有按 claim/metric 做筛选 (`contracts.py:611-624`)。
    这适合工作区留存，不适合作为论文输入。必须分离“完整探索历史”和“精选
    evidence projection”；ARS 只能收到后者，且保持 `review_required`。

13. **SCI-03：没有 capability 晋升标准**
    当前代码没有从 exploration 到 `CapabilityDescriptor.status=available` 的
    晋升协议。不能依据某次结果、AI 评分或拟合优度自动晋升。至少需要独立复现、
    已知标准/负例、适用范围、校准和不确定度验证、跨数据集回放、版本化 descriptor
    以及人工科学审查；晋升应生成新 capability/version，不修改历史 exploration
    run。

14. **SCI-04：method_intent 与 parameters 尚未具备科学类型**
    method intent 是自由文本，parameters 只是冻结 JSON
    (`contracts.py:276-359`)。这保留了灵活性，但也允许无单位、越界或含义不明的
    参数进入执行。下一步应由 descriptor 声明参数 schema、单位、范围、默认值、
    互斥条件和适用样品上下文；未知字段应保留为探索元数据但不能静默影响正式指标。

15. **SCI-05：缺少独立 replay/对照/不确定度证据**
    当前测试覆盖 DTO 完整性、错配和持久化，但没有证明某个探索算法的科学正确性。
    在晋升或 Results 候选前，应有冻结 fixtures、已知标准、负例、重复运行、灵敏度
    和误差传播测试，并将验证报告作为独立证据对象，而非写进 provider result 的
    自由文本。

## 推荐实施顺序

1. **先修 canonical admission 和严格 descriptor validator**：补 canonical
   dataset/template、轴 provenance、校准、descriptor hash、依赖/环境/seed，
   并让 input/output contract 真正成为 runner 前置条件。
2. **再做可信 worker，而不是进程内 sandbox**：内置 executor 可继续在开发期
   使用；Codex/用户代码必须进入隔离 worker，具备资源、文件、网络、依赖和输出
   限制，并记录真实代码包 hash。
3. **随后接 CLI/GUI/Codex**：所有入口只创建 request、调用 runner、读取同一
   ExplorationRun/ProviderResultInput/metric manifest；不新增摘要或私有结果表。
4. **然后接自动探索**：增加参数 schema、预算、seed、attempt ID、去重、停止
   条件、失败保留和完整候选历史；目标函数只能作为探索排序，不能直接等价于
   科学有效性。
5. **最后接 Evidence Package 和 capability 晋升**：先做独立 snapshot contract
   和精选投影，再建立基于 replay/标准/不确定度/人工审查的晋升流程。

## 放行判定

| 能力 | 当前判定 |
| --- | --- |
| 可信内置 callable 的开发期实验 | 有条件放行 |
| 普通用户直接注册 Python 函数 | 不放行 |
| Codex 生成代码并执行 | 不放行 |
| GUI/CLI 正式入口 | 暂缓，先完成 canonical/contract validator |
| 自动参数探索 | 暂缓，先完成预算与 attempt 语义 |
| 进入 Evidence Package | 暂缓，先完成独立 snapshot contract |
| 自动晋升正式 capability | 不放行，必须人工科学审查 |

这份审查不改变当前代码，也不把任何 exploration 结果提升为论文结论。
