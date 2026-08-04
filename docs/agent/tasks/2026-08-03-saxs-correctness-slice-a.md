---
task_id: 2026-08-03-saxs-correctness-slice-a
kind: scientific
status: completed
date: 2026-08-03
title: Repair deterministic SAXS correctness contracts
---

## Goal

Fix deterministic SAXS physical-core and boundary inconsistencies identified in
the 2026-08-03 review, while deferring scientifically ambiguous model choices.

## Non-goals

- No change to the Porod-invariant crystallinity model or its coefficients.
- No change to strain-sector metric scope or negative-background residual policy.
- No GUI publication-policy change, dataset edit, cleanup, push, or deployment.

## Affected boundaries

- `polynexus/core/saxs_engine/config.py`
- `polynexus/core/saxs_engine/core.py`
- `polynexus/core/saxs_engine/io.py`
- `polynexus/core/saxs_engine/preprocess.py`
- `polynexus/core/saxs_engine/saxs_temperature.py`
- `polynexus/core/saxs.py`
- `tests/test_saxs_correctness_slice_a.py`
- `tests/test_saxs_temperature_invalid_time_values_fail_closed.py`

## Implementation plan

1. Add RED regressions for physical limits, sequence ordering, units, flags,
   I/O, normalized input, truncation, and provenance.
2. Implement the deterministic physical-core and I/O contract fixes.
3. Run the focused SAXS matrix and repair behavior regressions only within the
   affected boundaries.
4. Run the UTF-8 task verifier, diff check, and explicit allowlist checkpoint.

## Acceptance criteria

- [x] 2D single-frame and directory analysis consume the same corrected,
  normalized, unsmoothed intensity contract.
- [x] Polarization correction is unity at zero scattering angle and identity for
  zero polarization.
- [x] Cooling solid/melt labels are physically ordered and cooling/isothermal
  acquisition order is preserved for kinetic analysis.
- [x] Gibbs-Thomson reports SI-consistent surface energy and honors an optional
  fixed `Tm_inf`.
- [x] Correlation extrapolation flags change the executed path.
- [x] Declared I/O extensions are accepted consistently; directory truncation and
  incomplete geometry provenance are explicit.
- [x] Focused regressions run RED before implementation and GREEN after it.
- [x] `python -X utf8 scripts/verify.py --task docs/agent/tasks/2026-08-03-saxs-correctness-slice-a.md --changed --types` passes.

## Completed evidence

- Focused RED run reproduced polarization, cooling phase/order, Gibbs units,
  correlation flags, `.xy`, and batch input-layer failures.
- GREEN focused matrix currently covers the changed contracts and adjacent
  temperature, quality, batch, and strain transport tests.
- `10` slice-A tests pass; the adjacent focused matrix passes `60` tests and
  the scoring/figure/quality matrix passes `51` tests.
- UTF-8 task verifier passes: quality gate `297`, preprocessing gate `106`,
  Ruff, compile, memory, and whitespace checks all pass.

## Verification

- Focused SAXS regression matrix.
- Task-scoped structured verifier with explicit UTF-8 mode on Windows:
  `python scripts/verify.py --task docs/agent/tasks/2026-08-03-saxs-correctness-slice-a.md --changed --types`.
- `git diff --check`.
- Explicit changed-file allowlist checkpoint after verification.

## Pre-existing state

The worktree contains unrelated staged, unstaged, deleted, and untracked user
changes. They must remain untouched and must not enter the checkpoint.
