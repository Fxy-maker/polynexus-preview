---
task_id: 2026-08-04-saxs-idf-axis-label-regression
kind: scientific
status: completed
date: 2026-08-04
title: Preserve SAXS correlation and IDF axis semantics
---

## Goal

Ensure published/static, temperature, and strain SAXS correlation and IDF
figures retain distance-space axis labels after shared publication polishing.

## Non-goals

- Do not change correlation or IDF calculations.
- Do not relabel raw `I(q)` or Kratky `I(q)q^2` figures as Fourier outputs.
- Do not edit historical generated figure assets.

## Affected boundaries

- `polynexus/core/saxs_engine/figure_common.py`
- `polynexus/core/saxs_engine/figure_provider.py`
- focused SAXS figure regression tests

## Root cause

The shared/public axis-label normalizers recognize correlation/gamma labels but
fall through to generic SAXS labels for an `IDF` y-axis. Existing generated
assets can therefore show `q`/`I` labels on distance-space traces, even though
their source columns are `r_idf`/`idf`.

## Implementation plan

1. Add a public-route regression for formatted correlation and IDF labels.
2. Teach both shared/public label normalizers to preserve formatted distance and
   IDF labels.
3. Run focused SAXS figure tests and the task-scoped repository verifier.

## Acceptance criteria

- [x] Public strain correlation uses `r (nm)` and `gamma(r)` labels.
- [x] Public strain IDF uses `r (nm)` and `IDF`/`g1(r)` labels.
- [x] Static and temperature Fourier/IDF routes preserve the same semantics.
- [x] Raw intensity remains `I (a.u.)`; Kratky remains `I(q)q^2`.

## Evidence

- Public strain probe now emits `$r$ (nm)`/`$\\gamma(r)$` for correlation,
  `$r$ (nm)`/`$\\mathrm{IDF}(r)$ (a.u.)` for IDF, and retains
  `$q$ (nm$^{-1}$)`/`$I(q)q^2$` for Kratky.
- Focused SAXS figure/document/evidence tests: `87 passed`, 4 pre-existing
  font warnings.
- UTF-8 task verifier: passed; quality gate `297 passed`; preprocess gate
  `106 passed`.
- `git diff --check`: passed.

## Verification

```powershell
python -m pytest -q tests/test_saxs_iq2_fourier_figures.py
python scripts/verify.py --task docs/agent/tasks/2026-08-04-saxs-idf-axis-label-regression.md --changed --types
python -X utf8 scripts/verify.py --task docs/agent/tasks/2026-08-04-saxs-idf-axis-label-regression.md --changed --types
git diff --check
```

## Pre-existing state

The worktree contains unrelated staged, unstaged, deleted, and untracked user
changes. They remain untouched and are outside this task's allowlist.
