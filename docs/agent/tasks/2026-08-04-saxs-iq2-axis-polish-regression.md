---
task_id: 2026-08-04-saxs-iq2-axis-polish-regression
kind: scientific
status: ready_for_review
date: 2026-08-04
title: Preserve SAXS Iq2 axis labels through publication polishing
---

## Goal

Keep the `I(q)q^2` meaning visible in published/gallery previews for static,
temperature, and strain SAXS figure routes.

## Non-goals

- Do not change SAXS analysis, smoothing, or Kratky calculations.
- Do not rewrite existing generated figure assets or historical runs.
- Do not change Fourier/correlation data semantics.

## Affected boundaries

- `polynexus/core/saxs_engine/figure_common.py`
- `polynexus/core/saxs_engine/figure_provider.py`
- `tests/test_saxs_iq2_fourier_figures.py`
- `docs/agent/memory/active-work.md`

## Root cause

The public figure polishing helpers recognized only generic intensity labels.
The specialized `I(q) q^2` label therefore fell through to the generic SAXS
intensity label `$I$ (a.u.)`, even though the plot object remained bound to
`intensity_q2`.

## Change

- Preserve a dedicated `I(q)q^2` label in the shared static polish helper.
- Preserve the same label in the legacy/public SAXS provider polish helper.
- Add a public-route regression covering source values and labels for strain,
  plus label coverage for static and temperature routes.

## Implementation plan

1. Reproduce the public-route label regression with a focused test.
2. Teach both publication polish helpers to preserve q-squared y-axis labels.
3. Run the focused SAXS figure matrix and the task-scoped repository verifier.

## Acceptance criteria

- [x] Public `saxs.strain.kratky`, `saxs.temperature.kratky`, and static Kratky
  definitions retain a q-squared y-axis label.
- [x] Public strain data remains bound to `intensity_q2`, not raw `intensity`.
- [x] Existing correlation/Fourier labels and unrelated intensity labels remain
  unchanged.

## Verification

```powershell
python -m pytest -q tests/test_saxs_iq2_fourier_figures.py tests/test_saxs_temperature_figure_provider.py tests/test_saxs_figure_document.py tests/test_saxs_figure_evidence_binding.py
python scripts/verify.py --task docs/agent/tasks/2026-08-04-saxs-iq2-axis-polish-regression.md --changed --types
python -X utf8 scripts/verify.py --task docs/agent/tasks/2026-08-04-saxs-iq2-axis-polish-regression.md --changed --types
git diff --check
```

## Limitations

Existing exported PNG/PDF artifacts are immutable historical outputs; the GUI
must publish a new run to regenerate previews with the corrected label.

## Pre-existing state

The worktree contains unrelated staged, unstaged, deleted, and untracked user
changes. They remain untouched and are outside this task's allowlist.
