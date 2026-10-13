# PolyNexus 预览版：需要人工审查的具体事项

这是 PR #1 的合并前审查说明，不是每次计算都要用户审批的清单。
既定定位仍是 AI 探索、Core 确定性计算与追溯、局部缺失不阻断独立指标。
审查对象是实现是否符合这个定位，以及哪些结果的科学解释还不能自动确定。
自动化测试验证软件契约和回归行为，不等于独立科学验证。

## 合并前需要看的五个边界

| 审查事项 | 当前实现及具体问题 | 推荐判断与影响 | 审查证据 |
| --- | --- | --- | --- |
| DSC 实验段角色 | 通用热程序保留单独出现的 255 °C、180 °C 两个保温段，不按材料名或固定温度删除。但重复出现的最高温保温段仍会由旧启发式排除为 `melt_hold`；保温段也有默认 `isothermal_crystallization` 角色。程序形状不能证明真实相变或实验目的。 | 审查这些推断是否适用于公开声明的范围。推荐后续改成显式实验角色，未确认时保留各段独立计算；不要把最高温等同于已熔融，或把保温等同于已结晶。若预览版保留旧路线，应明确限制，不能宣称任意热程序的角色识别已通用。 | `polynexus/core/canonical_experiments/dsc_isothermal.py`，尤其 `_remove_inferred_preparation_holds`；`tests/test_tpae_golden_workflow.py`；`tests/test_canonical_experiments.py` |
| SAXS 物理含义与跟踪边界 | 有符号的背景扣除残差进入积分；总通道提供结构指标，扇区提供取向。跟踪失峰后不能用另一个长周期拟合值重启；当前每步相对位移上限为 25%，并存在默认层片候选范围。二维投影取向也不自动等同于三维 Herman 因子。 | 推荐认可本轮失峰修复与有符号积分契约；让懂 SAXS 的人检查峰区间、位移限制及取向名称的适用范围。快速变化或特殊样品需要显式设置/探索方法；失峰仅令依赖该特征的指标不可用，独立积分继续。 | `polynexus/core/saxs_engine/core.py` 的 `bragg_long_period`/`analyze_single`；`saxs_strain.py`；`tests/test_saxs_strain_tracking_fail_closed.py`；2026-08-04 科学正确性设计 |
| 新高级模型与 SEC 校准的科学范围 | TGA Kissinger/OFW、DMA 主曲线、流变 Cox–Merz/触变/蠕变/松弛/TTS、力学循环/疲劳/断裂均依赖显式 spec，仍为诊断候选。SEC 要指定校准标准、响应通道和质量/数量分布语义，不进行区间外外推。拟合成功不能证明模型适合该实验。 | 推荐以诊断能力公开和合并，保持不同方法并行；检查方法、单位、条件、拟合区间、基线和响应假设是否完整留在结果中。不要把 DMA 峰直接写成 Tg、把 SEC 校准结果写成绝对分子量、或把断裂功写成标准断裂韧度。缺少元数据只影响相关模型。 | `docs/agent/tasks/2026-09-13-advanced-models-complete-suite.md`；`2026-09-13-sec-gpc-calibration-distribution.md`；`polynexus/core/sec_processing.py`；相关 `test_*_advanced.py` |
| AI 自定义代码的运行边界 | worker 与 Core 分进程，有超时/输出限制、清空环境以及 Python 层文件/网络限制。原生扩展、子进程等可以超出这些 Python 级限制；Windows 没有这里依赖的 POSIX `resource` 硬限制。它不是可运行敌对代码的 OS 沙箱。 | 推荐本地预览只接入受信任、用户可检查的 executor，并准确描述为受限 worker；若要对外自动执行任意不可信代码，先补容器/VM 或操作系统强制隔离。Codex 的运行环境不会自动变成 PolyNexus worker 的安全边界。 | `polynexus/core/exploration/worker.py`；对应 worker/runner 测试；`docs/OPEN_SOURCE.md` |
| 共享对象与论文证据出口 | 多入口共用 canonical、ComputeRun、指标、图表/证据对象；portable export 绑定原始文件和导出文件。探索结果要经过明确的指标选择才进入证据。选择记录表示一次选择，不证明结论正确；晋升中的人工审查标志也不是身份认证。 | 架构审查抽查一个 GUI/CLI/Agent 同输入运行和一个 raw→portable→canonical→evidence 路径，确认 hash、单位、方法、警告一致。推荐保留 Codex 精选，不新增账号或逐次审核闸门；论文作者最终核对分组、结论与实际实验是否相符。 | `tests/test_advanced_cross_entry.py`、`tests/test_portable_export_cross_entry.py`；`polynexus/core/exploration/evidence.py`、`promotion.py`；本轮完整/boundary 检查 |

上面的第三项可以按模型分给相应学科人员，但无需为每个指标新建审批流程。
审查通过的是实现边界和发布范围，不是对所有未知高分子样品给出通用保证。

## 可以继续计算，正式能力晋升前再补的证据

- 独立 replay：真实仪器/不同材料数据与独立参考实现或可核实的文献结果。
  同一实现运行两次只能证明复现性；不能作为准确性的独立证明。
- 标准样品和负对照：公开下载的数据需要确认来源、单位、测试条件和它是否
  真是标样，不能因为来自公开仓库就标成标准。新物质没有内置预期时仍可
  计算；不凭材料名创造应有数值。
- 不确定度：当前共享契约支持诊断性 RSS 和显式覆盖因子。人工检查各误差
  来源、量纲及独立性假设；相关误差不能直接当独立项相加。没有重复测量
  或校准信息时为 `unavailable`，不阻断普通结果，也不强加误差范围到正文。
- capability 晋升：逐方法提供上述证据并进行科学审查。readiness 对象帮助
  AI 准备证据，不自动晋升；一个调用者提供的 `passed` 或审查布尔值不构成
  独立、经过身份认证的认可。科研预览不需要现在建设监管审计系统。

## 普通运行时真正需要用户判断的情况

只有分组/跨技术对齐改变实验含义、单位或通道有歧义、方法依赖未声明的
科学前提，以及论文结论超过证据时才需要进一步确认。确定性解析、普通
警告、可重试执行失败、图表格式选择不属于上述人工科学审查。

仓库合并规则来源：[AGENTS.md](../../AGENTS.md) 第 7 节：
“Architecture, schema, security, performance, and scientific-semantics changes
still require human review before merge.” 因此代码和检查完成后仍保留 draft PR，
交付可审查结果，不自动合并。
