---
task_id: 2026-08-28-adaptive-isothermal-baseline
kind: scientific
status: completed
date: 2026-08-28
title: 自适应等温 DSC 基线
---

# 自适应等温 DSC 基线

## Goal

让等温 DSC 对每个候选事件使用材料无关的自适应基线：默认端点线性基线，必要时降级到尾部恒定基线，同时保留备选结果和完整 provenance。

## Non-goals

- 不使用材料专用规则或固定温度/秒数。
- 不平均多个基线结果。
- 不修改原始数据。
- 不自动决定论文采用范围。

## Affected boundaries

- `polynexus/core/dsc_engine/dsc_kinetics.py` 的候选事件积分和 Avrami 结果契约。
- `polynexus/core/dsc.py` 参数/结果投影。
- `ComputeRun`、CLI、Batch、GUI、Agent/Codex、evidence/ARS 消费现有共享投影。
- 合成回归和真实 PA6/PA11/PA12 六样品只读回放。

## Implementation plan

1. 以事件长度比例构造端点稳定窗口，并计算端点线性与尾部恒定基线变体。
2. 默认选择可用的端点线性基线；端点不可用时降级到尾部恒定基线并记录 warning。
3. 将选定方法、窗口、斜率、备选结果和敏感性通过 `AvramiResult` 与现有参数/ComputeRun 投影暴露。
4. 用合成曲线、DSC/ComputeRun/CLI/Batch/Agent/GUI/evidence 测试和六样品真实回放验证一致性。

## Acceptance criteria

- [x] 端点线性基线在有效端点窗口时为默认主结果。
- [x] 端点窗口不可用时降级到尾部恒定基线并记录 warning。
- [x] 备选基线结果保留但不混入主结果。
- [x] PA6-DWJJ 180–184 ℃结果接近历史端点线性基线结果。
- [x] 结果、参数表和 ComputeRun/evidence 投影记录基线方法与窗口。
- [x] 现有 DSC/ComputeRun/CLI/Batch/Agent/GUI/evidence 测试无回归。

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_dsc_kinetics.py tests/test_dsc_canonical_isothermal_conversion.py
python -m pytest -p no:cacheprovider -q tests/test_compute_service.py tests/test_cli_batch.py tests/test_cli_batch_run_service.py tests/test_agent_workflow_cli.py tests/test_evidence_package_view.py tests/test_project_writing_metrics.py
python scripts/verify.py --task docs/agent/tasks/2026-08-28-adaptive-isothermal-baseline.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "fix(dsc): add adaptive isothermal baseline selection" `
  --files polynexus/core/dsc_engine/dsc_kinetics.py polynexus/core/dsc.py polynexus/core/dsc_engine/figure_isothermal.py tests/test_dsc_kinetics.py tests/test_project_writing_metrics.py docs/superpowers/specs/2026-08-28-adaptive-isothermal-baseline-design.md docs/superpowers/plans/2026-08-28-adaptive-isothermal-baseline.md docs/agent/tasks/2026-08-28-adaptive-isothermal-baseline.md docs/acceptance/2026-08-28-dsc-adaptive-baseline.md docs/agent/memory/current-state.md docs/agent/memory/active-work.md
```

## Completion evidence

- Exact commands and outcomes: focused DSC/ComputeRun/CLI/Agent/evidence/writing matrix passed `120 passed, 3 skipped`; task verifier and quality/preprocessing gates passed; real six-sample read-only isothermal smoke completed all six files with complete baseline projections.
- Known limitations: scientific promotion and paper-use decisions remain human/ARS review boundaries.
- Pre-existing changes left untouched: `active_run.json`, `runs/`, `tests/_tmp_phase3/`, historical replay packages and raw datasets.
