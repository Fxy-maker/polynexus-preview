---
task_id: 2026-08-28-generic-isothermal-event-candidates
kind: scientific
status: proposed
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

## Acceptance criteria

- [ ] All calculable event candidates are retained with source ranges and quality metadata.
- [ ] Default recommendation is shape-driven and material-neutral.
- [ ] PA6-DWJJ no longer uses the initial switching transient as its main crystallization event.
- [ ] Default Avrami fit range is `Xt=5%–80%`, recorded in the plan and result.
- [ ] Structural invalid data still blocks; calculable but uncertain data returns values with warnings.
- [ ] Shared Core/AI/CLI/Batch/GUI/evidence projections remain identical.

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

- Exact commands and outcomes: pending implementation.
- Known limitations: default candidate-ranking semantics and scientific promotion remain human-reviewable.
- Pre-existing changes left untouched: `active_run.json`, `runs/`, `tests/_tmp_phase3/`, historical artifacts and old replay packages.
