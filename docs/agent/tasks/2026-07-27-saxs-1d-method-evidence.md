# SAXS 1D 方法族证据

## Goal

将现有 Porod、Kratky、不变量和层片结果统一为可追溯、可降级的
`MetricEvidence`，并挂载到 `SAXSResult`，保持现有数值输出和 GUI 兼容。

## Non-goals

- 不重写 Porod/Kratky/invariant/Bragg/Lorentz/correlation/IDF 数值算法。
- 不新增 `slope≈-4`、Kratky 形状或方法一致性的未经审查硬阈值。
- 不在本阶段实现温度/应变序列融合、2D、AI 救援或发布角色升级。

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `polynexus/core/saxs_engine/core.py`
- `polynexus/core/saxs_engine/__init__.py`
- `tests/test_saxs_1d_method_evidence.py`
- `tests/test_saxs_result_contract.py`
- `docs/superpowers/specs/2026-07-27-saxs-1d-method-evidence-design.md`

## Implementation plan

1. 为四个 builder 写失败测试，锁定现有输出字段、适用性、数据质量、严格
   JSON 和失败降级语义。
2. 实现四个只读 builder，复用 `MetricEvidence` 和 `QualityLevel`，不引入
   新的物理硬阈值。
3. 增加 `SAXSResult.metric_evidence`，在既有单帧结果完成后挂载四项证据，
   保护 builder 异常和缺失输入。
4. 跑 focused/SAXS 回归/结构化 verifier，记录限制并创建原子 checkpoint。

## Acceptance criteria

- [x] 四个方法均输出严格 JSON-safe 的 `MetricEvidence` 字典，含来源、数值、
  点数/拟合证据、物理检查、风险码和等级。
- [x] `supported` 且证据充分时最高为 `Trend`；unknown/unsupported 最高为
  `Diagnostic`；不可用输入为 `Unusable`。
- [x] Porod 斜率偏差、Kratky 峰/形状、invariant beamstop、层片方法缺失或
  不一致均被记录，不被静默吞掉，也不引入新硬阈值。
- [x] `SAXSResult` 保留原有 `porod`/`kratky`/`structure`，新增映射不破坏
  现有消费者。
- [x] focused、完整 SAXS、结构化 verifier、两道质量 gate 和原子 checkpoint
  均有实际证据。

## Verification

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_saxs_1d_method_verify'
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-1d-method-evidence.md --changed --types
```

## Verification evidence (2026-07-27)

- 方法 builder focused tests：`5 passed`；方法/Guinier/变温/评分/物理 helper/
  质量契约/结果契约回归：`34 passed`。
- 精确收集的 37 个 `tests/test_saxs_*.py` 文件：`242 passed, 4 warnings`
  in `21.05s`；warning 仍是既有 SAXS figure Arial CJK glyph warning。
- 结构化 verifier 通过：quality gate `282 passed`，preprocessing gate
  `103 passed`，Ruff、compile、memory、task-card 和 whitespace checks 均通过。
- 本阶段 checkpoint 使用显式 changed-file allowlist 创建，未 push、merge 或
  deploy。

## Known limitations

本阶段只建立证据结构和保守分级。方法级定量阈值、真实聚合物场景适用性、
2D 误差传播、序列/AI 救援和 Workbench 发布仍需独立阶段与人工科学审查。

## Changed-file allowlist

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `polynexus/core/saxs_engine/core.py`
- `polynexus/core/saxs_engine/__init__.py`
- `tests/test_saxs_1d_method_evidence.py`
- `tests/test_saxs_result_contract.py`
- this task card
- `docs/superpowers/specs/2026-07-27-saxs-1d-method-evidence-design.md`
- `docs/superpowers/plans/2026-07-27-saxs-1d-method-evidence.md`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`
