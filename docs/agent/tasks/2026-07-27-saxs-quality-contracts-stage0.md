# SAXS Quality Contracts Stage 0

## Goal

Establish the first typed, strict-JSON quality/evidence contract for SAXS
frames and rescue candidates without changing existing SAXS calculations.

## Non-goals

- Do not implement Guinier fitting, rescue execution, AI selection, or physical
  acceptance gates in this stage.
- Do not infer missing frames or repair input arrays.
- Do not promote any metric or figure publication role.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `tests/test_saxs_quality_contracts.py`
- `tests/fixtures/saxs_quality_cases.py`
- `tests/fixtures/__init__.py`
- Durable task/memory records only.

## Implementation plan

1. Define immutable quality, metric, Guinier, rescue-candidate, and rescue-
   validation DTOs with strict JSON conversion.
2. Add focused regressions for non-mutating defect inventory, round-trip
   serialization, quality-level preservation, and fail-closed rescue gates.
3. Run the Stage 0 verifier and checkpoint only the explicit allowlist.

## Acceptance criteria

- [x] `DataQualityReport` inventories q/I defects without mutating inputs.
- [x] `MetricEvidence`, `GuinierEvidence`, `RescueCandidate`, and
  `RescueValidationReport` round-trip through strict JSON-safe dictionaries.
- [x] Quality levels remain explicitly limited to `Quantitative`, `Trend`,
  `Diagnostic`, and `Unusable`.
- [x] A rescue candidate cannot become accepted unless hard, physical,
  sequence, and data-preservation gates pass.
- [x] Focused tests, synthetic fault fixtures, Ruff, and the structured task
  verifier pass.

## Verification

```powershell
python -m pytest tests/test_saxs_quality_contracts.py -q
python -m ruff check polynexus/core/saxs_engine/saxs_quality_contracts.py tests/test_saxs_quality_contracts.py tests/fixtures/saxs_quality_cases.py
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-quality-contracts-stage0.md --changed --types
```

实际结果：focused contract suite `7 passed`；SAXS 回归矩阵 `37 passed`；
结构化 verifier 在外置 `C:\Temp\PolyNexus_saxs_quality_contracts_verify`
basetemp 下通过，quality gate `282 passed`，preprocess gate `103 passed`。
默认仓库临时目录曾因既有 Windows `WinError 5` 清理问题报告 `229 passed,
53 errors`，错误均发生于测试收尾删除 `.pytest_tmp`，外置 basetemp 重跑已
隔离该环境问题。

## Known limitations

This checkpoint does not connect the contracts to SAXS temperature/static/
strain analysis results, FigureDefinitions, Workbench, AI rescue, or real
scientific acceptance. Those remain separate stages under
`docs/agent/tasks/2026-07-26-saxs-quality-analysis-program.md`.

## Changed-file allowlist

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `tests/test_saxs_quality_contracts.py`
- `tests/fixtures/saxs_quality_cases.py`
- `tests/fixtures/__init__.py`
- this task card
- `docs/superpowers/plans/2026-07-26-saxs-quality-contracts.md`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`

## Checkpoint

- Atomic implementation checkpoint already present at `556f006`:
  `feat(saxs): add quality evidence contracts`.
