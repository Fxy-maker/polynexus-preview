---
task_id: 2026-08-04-saxs-configured-qmin-semantics
kind: scientific
status: completed
date: 2026-08-04
title: Respect configured SAXS valid q minimum
---

## Goal

Treat the configured `SAXSConfig.q_min` as the experiment's declared valid
lower q bound. Remove lower-q input points before analysis and avoid reporting
known configured truncation as unexpected beamstop contamination.

## Non-goals

- Do not change detector geometry calibration.
- Do not invent a q minimum when the configuration does not provide one.
- Do not suppress a beamstop warning when auto-detection finds a boundary
  above the configured q minimum.
- Do not change Porod, invariant, or long-period physical formulas.

## Affected boundaries

- `polynexus/core/saxs_engine/core.py`
- focused SAXS analysis tests

## Root cause

The 2D integration/profile path used the default `q_min=0.05` even though this
experiment's valid profile begins at `0.125 nm^-1`. `analyze_single()` retained
the lower-q prefix, auto-detected an effective edge near `0.125`, and then
turned the expected configured truncation into `ERROR:qstar_contaminated`.

## Implementation plan

1. Add regressions for explicit q-min trimming and quality classification.
2. Trim external 1D profiles below configured `q_min` before analysis.
3. Treat an auto-detected edge at the configured floor as known truncation;
   retain a warning but do not emit the unexpected contamination error.
4. Verify the focused SAXS matrix and task-scoped repository gates.

## Acceptance criteria

- [x] Input q values below configured `q_min` do not enter `SAXSResult.q` or
  Kratky/correlation/IDF payloads.
- [x] A configured q minimum at the detected edge does not emit
  `ERROR:qstar_contaminated`.
- [x] A genuinely higher auto-detected edge still emits the contamination
  error.
- [x] Existing q-min propagation and invalid-profile behavior remain intact.

## Verification

```powershell
python -m pytest -q tests/test_saxs_configured_qmin_semantics.py
python scripts/verify.py --task docs/agent/tasks/2026-08-04-saxs-configured-qmin-semantics.md --changed --types
python -X utf8 scripts/verify.py --task docs/agent/tasks/2026-08-04-saxs-configured-qmin-semantics.md --changed --types
git diff --check
```

On this Windows workspace, use the UTF-8 invocation above when the plain
command inherits the system GBK encoding.

## Evidence

- Focused regression: `3 passed`.
- Focused SAXS compatibility matrix: `22 passed`.
- UTF-8 task verifier: quality gate `297 passed`, preprocessing gate `106
  passed`, Ruff/compile/type-baseline/whitespace checks passed.
- `git diff --check` passed as part of the verifier.

## Known limitations

- Existing historical run assets are unchanged; regenerate/publish a new run
  to observe the corrected q-domain and quality state.
- A frame whose detected edge is materially above the configured floor remains
  diagnostic/error by design; the 200% sample's independent long-period range
  issue is unrelated and remains.

## Pre-existing state

The worktree contains unrelated staged, unstaged, deleted, and untracked user
changes. They remain untouched and are outside this task's allowlist.
