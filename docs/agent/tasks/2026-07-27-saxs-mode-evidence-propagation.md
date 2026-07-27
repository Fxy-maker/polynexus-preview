# SAXS 静态/变温/应变证据传播

## Goal

把单帧 `SAXSResult` 的质量与 1D 方法证据传播到变温/应变每个观测帧，保持
模式专用科学字段、帧顺序和失败可见性。

## Non-goals

- 不改变任何现有 SAXS 数值算法、温度/应变相位判断或发布角色。
- 不插值、复制邻帧、平滑或删除缺失/失败帧。
- 不把温度序列趋势用于应变模式，不新增跨模式科学阈值。
- 不实现 2D、AI 救援、Workbench 或 Figure/Manifest 发布变更。

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_temperature.py`
- `polynexus/core/saxs_engine/saxs_strain.py`
- `tests/test_saxs_mode_evidence_propagation.py`
- `docs/superpowers/specs/2026-07-27-saxs-mode-evidence-propagation-design.md`

## Implementation plan

1. 为变温和应变成功/失败帧写 focused failing tests，锁定公共 evidence 和
   data-quality payload 的逐帧传播及 DataFrame 摘要。
2. 在两个 point DTO 增加可选 `metric_evidence`/`data_quality_report`，只在
   `analyze_single` 成功分支读取，不改变模式专用字段。
3. 增加严格 JSON-safe 的 evidence level 摘要列，保持既有列顺序和数据值。
4. 运行 focused、温度/应变/完整 SAXS 回归和结构化 verifier，记录证据并
   创建原子 checkpoint。

## Acceptance criteria

- [x] 变温成功帧保留自己的 `metric_evidence` 和 `data_quality_report`。
- [x] 应变成功帧保留自己的 `metric_evidence` 和 `data_quality_report`。
- [x] 任一核心失败帧保持 `None`/`Unusable`，不复制邻帧或改变帧数/顺序。
- [x] 变温仍只有温度序列 builder，应变不产生温度序列证据。
- [x] 两种 DataFrame 增加紧凑等级摘要，既有列和值兼容。
- [x] focused、完整 SAXS、结构化 verifier、两道质量 gate 和 checkpoint 均有
  实际证据。

## Verification

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_saxs_mode_propagation_verify'
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-mode-evidence-propagation.md --changed --types
```

## Verification evidence (2026-07-27)

- Mode propagation focused tests plus existing temperature/strain status and
  evidence filtering tests: `26 passed`.
- Exact 38-file `tests/test_saxs_*.py` matrix: `244 passed, 4 warnings` in
  `21.48s`; warnings are the existing Arial CJK glyph warnings from SAXS figure
  layout.
- Structured verifier passed: quality gate `282 passed`, preprocessing gate
  `103 passed`, Ruff, compile, memory, task-card, and whitespace checks passed.
- Checkpoint is created with the explicit allowlist; no push, merge, deploy, or
  generated-output changes were made.

## Known limitations

跨模式证据传播不等于跨模式科学结论。2D 探测器质量、取向不确定度、AI
候选验证、Workbench/Manifest/Export 和人工科学审查仍未关闭。

## Changed-file allowlist

- `polynexus/core/saxs_engine/saxs_temperature.py`
- `polynexus/core/saxs_engine/saxs_strain.py`
- `tests/test_saxs_mode_evidence_propagation.py`
- this task card
- `docs/superpowers/specs/2026-07-27-saxs-mode-evidence-propagation-design.md`
- `docs/superpowers/plans/2026-07-27-saxs-mode-evidence-propagation.md`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`
