# SAXS 变温 Guinier 序列证据

## Goal

在阶段 1 的逐帧 Guinier 证据之上，增加不插值、不改写输入的序列级趋势与
连续性证据，并将其挂载到 `TempSeriesResult`。

## Non-goals

- 不改变 `guinier_analysis`、单帧 `GuinierEvidence` 或层片算法。
- 不插值、删除、替换或平滑任何温度帧。
- 不把序列趋势升级为单帧 `Quantitative`，不新增 AI 救援或 GUI 发布角色。
- 不使用连续性统计自动否定真实相变突变。

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `polynexus/core/saxs_engine/saxs_temperature.py`
- `polynexus/core/saxs_engine/__init__.py`
- `tests/test_saxs_guinier_sequence_evidence.py`
- `tests/test_saxs_temperature_guinier_evidence.py`
- `docs/superpowers/specs/2026-07-27-saxs-guinier-sequence-evidence-design.md`

## Implementation plan

1. 先为 `GuinierSequenceEvidence` 和纯构造器写 focused failing tests，覆盖
   空/单帧/缺失帧、温度轴缺陷、连续趋势、孤立跳变和严格 JSON。
2. 在 `saxs_quality_contracts.py` 实现不可变序列 DTO、帧证据解析、确定性
   分级和只读连续性诊断，并通过 `__init__.py` 导出。
3. 在 `TempSeriesResult` 中挂载序列摘要，保持每个失败帧为 `None`，增加不
   改变既有列的序列状态列，并补充变温回归。
4. 运行 focused/完整 SAXS/结构化 verifier，记录实际结果并用显式白名单创建
   原子 checkpoint。

## Acceptance criteria

- [ ] 序列 DTO 严格 JSON-safe，且能从帧证据恢复。
- [ ] 空/单帧/全失败序列分别得到 `Unusable` 或 `Diagnostic`，不伪造 Rg。
- [ ] 至少两个有效帧且温度轴有效时得到 `Trend`；序列级不产生
  `Quantitative`。
- [ ] 缺失、失败、无效温度、重复温度均保留原位置和 reason code。
- [ ] 连续真实变化不因序列统计被删除或自动降级；孤立变化只形成可解释
  诊断证据。
- [ ] `TempSeriesResult` 保留序列摘要，现有逐帧结果和 DataFrame 列兼容。
- [ ] focused tests、完整 SAXS 回归、结构化 verifier 和原子 checkpoint 有
  实际命令输出。

## Verification

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_saxs_guinier_sequence_verify'
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-guinier-sequence-evidence.md --changed --types
```

## Known limitations

连续性断点只是证据，不是相变识别或自动救援决策。阈值和相变区语义仍需真实
实验数据及人工科学审查；下一阶段才讨论候选生成和 AI shadow/confirm-only。

## Changed-file allowlist

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `polynexus/core/saxs_engine/saxs_temperature.py`
- `polynexus/core/saxs_engine/__init__.py`
- `tests/test_saxs_guinier_sequence_evidence.py`
- `tests/test_saxs_temperature_guinier_evidence.py`
- this task card
- `docs/superpowers/specs/2026-07-27-saxs-guinier-sequence-evidence-design.md`
- `docs/superpowers/plans/2026-07-27-saxs-guinier-sequence-evidence.md`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`
