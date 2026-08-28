---
task_id: 2026-08-28-generic-isothermal-event-candidates
kind: scientific
status: completed
date: 2026-08-28
title: 通用等温 DSC 候选事件计算
---

# 通用等温 DSC 候选事件计算

## Goal

让 Core 对每个等温 DSC 段识别并计算全部候选事件，由 AI/用户选择研究相关事件，避免瞬态误判造成数量级错误。

## Non-goals

- 不添加材料专属温度或时间规则。
- 不修改原始数据。
- 不删除兼容入口。
- 不让 Core 自动决定论文采用范围。

## Shared objects and entry points

- Objects: canonical DSC segment, candidate event, AnalysisPlan, ComputeRun, evidence package。
- Producers: canonical DSC conversion, new event detector, DSCEngine。
- Consumers: ComputeRunService、项目流程、Agent/Codex、CLI、Batch、GUI、evidence package、ARS writing input。
- Cross-entry rule: all consumers use the same candidate and frozen AnalysisPlan projection.

## Affected boundaries

- Core DSC kinetics and public `AvramiResult`/candidate contracts.
- Deterministic result projection used by DSCEngine, ComputeRun, CLI/Batch, GUI,
  Agent/Codex, evidence packages, and ARS writing inputs.
- Existing non-DSC techniques and raw artifacts are out of scope.

## Implementation plan

1. Add a material-neutral candidate detector and preserve candidate provenance.
2. Select a settled candidate for the compatibility `avrami_from_dsc` projection
   while retaining all candidates in series results.
3. Standardize the Avrami fit window at Xt=5%–80% and expose it in result rows.
4. Propagate the shared fields through all existing result/evidence consumers.
5. Replay synthetic and six-sample PA6 data, then run focused and repository checks.

## Acceptance criteria

- [x] All calculable event candidates are retained with source ranges and quality metadata.
- [x] Default recommendation is shape-driven and material-neutral.
- [x] PA6-DWJJ no longer uses the initial switching transient as its main crystallization event.
- [x] Default Avrami fit range is `Xt=5%–80%`, recorded in the plan and result.
- [x] Structural invalid data still blocks; calculable but uncertain data returns values with warnings.
- [x] Shared Core/AI/CLI/Batch/GUI/evidence projections remain identical.

## Verification

```powershell
python -m pytest -q tests/test_dsc_kinetics.py tests/test_dsc_canonical_isothermal_conversion.py
python scripts/verify.py --task docs/agent/tasks/2026-08-28-generic-isothermal-event-candidates.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "fix(dsc): compute material-neutral isothermal event candidates" `
  --files polynexus/core/dsc_engine/dsc_kinetics.py tests/test_dsc_kinetics.py docs/superpowers/specs/2026-08-28-generic-isothermal-event-candidates-design.md docs/agent/tasks/2026-08-28-generic-isothermal-event-candidates.md
```

## Completion evidence

- Exact commands and outcomes: focused DSC/canonical/ComputeRun matrix passed `66 passed, 3 skipped`; final DSC kinetics/canonical matrix passed `28 passed`; real six-sample isothermal ComputeRun smoke completed all six files with status `completed`; `git diff --check` passed.
- Known limitations: default candidate-ranking semantics and scientific promotion remain human-reviewable.
- Pre-existing changes left untouched: `active_run.json`, `runs/`, `tests/_tmp_phase3/`, historical artifacts and old replay packages.
