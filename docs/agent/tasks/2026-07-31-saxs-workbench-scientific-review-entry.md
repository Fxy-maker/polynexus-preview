---
task_id: 2026-07-31-saxs-workbench-scientific-review-entry
kind: scientific-cross-module
status: in_progress
date: 2026-07-31
title: Add reviewer-selected SAXS scientific review entry to Workbench
---

# SAXS Workbench Scientific Review Entry

## Goal

Let a reviewer select the existing SAXS 1D or 2D scientific-review scope from
the Results Workbench and persist a validated, source-linked record against the
selected analysis run.

## Non-goals

- No q/I recalculation, fitting, interpolation, frame repair, rescue, AI
  candidate execution, quality-level change, physical-gate change, or
  publication-role change.
- No automatic inference of 1D versus 2D meaning from mode, detector, mask,
  beam center, orientation, or algorithm state.
- No default reviewer decisions or changes to real data, generated outputs,
  scratch, storage, or parallel NMR/GUI work.

## Affected boundaries

- `polynexus/core/scientific_review.py`: ordered reviewer scope options.
- `polynexus/gui/main_window_results_mixin.py`: explicit scope chooser and
  existing run-scoped persistence path.
- `polynexus/gui/i18n.py`: generic chooser strings.
- Existing ScientificReviewDialog and SampleDB contracts, consumed without
  changing their validation or transaction semantics.
- Focused scientific-review and Workbench tests plus documentation evidence.

## Implementation plan

1. Add RED tests for ordered SAXS scope options, selected 2D persistence, and
   cancelled scope selection.
2. Add the core options helper, generic translated chooser, and Workbench
   integration while preserving the existing single-scope paths.
3. Run focused GREEN tests and the complete SAXS matrix with a complete
   pytest summary and exit code.
4. Run the structured verifier, diff/storage dry-runs, update evidence, and
   create the explicit allowlist checkpoint.

## Acceptance criteria

- [x] SAXS exposes exactly `saxs.1d`, then `saxs.2d` as reviewer choices.
- [x] The existing single-scope IR/NMR/Joint behavior remains unchanged.
- [x] A cancelled choice, missing run, or rejected dialog performs no write.
- [x] A chosen scope is validated by `ScientificReviewRecord` and persisted
      with the existing source-linked promotion snapshot.
- [x] No SAXS analysis field, quality level, physical gate, rescue state, AI
      state, Figure, Manifest, Export, or publication role changes.
- [x] TDD RED/GREEN, task verifier, SAXS matrix, diff check, and storage
      dry-run are recorded; the explicit allowlist checkpoint follows the
      final cumulative-diff review.

## Verification commands

```powershell
python -m pytest -q tests/test_scientific_review.py tests/test_scientific_review_workbench.py -o addopts=
python -m pytest -q (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName }) -o addopts=
python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-workbench-scientific-review-entry.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24 --json
git diff --check
```

The SAXS matrix counts only a complete pytest summary with exit code `0`. No
`test_storage.py --apply` is part of this task.

## Verification

The authoritative structured check is:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-workbench-scientific-review-entry.md --changed --types
```

The task is complete only when the focused tests, SAXS matrix, structured
verifier, and `git diff --check` have actual successful results recorded below.

### Recorded implementation evidence

- RED: the newly added option-helper import failed during collection, before
  the helper existed.
- GREEN: `python -m pytest -q tests/test_scientific_review.py
  tests/test_scientific_review_workbench.py -o addopts=` completed with
  `49 passed` on 2026-07-31.
- Fresh SAXS matrix: `653 passed, 6 warnings in 505.81s`, exit code `0`.
- Structured verifier: exit `0`; quality gate `297 passed`, preprocessing gate
  `106 passed`, plus task/memory, Ruff, compile, type-baseline, and whitespace
  checks.
- `git diff --check`: exit `0`.
- Storage report and `clean --older-than-hours 24 --json` both ran in dry-run
  mode with exit `0`; the clean inventory had `88` artifacts,
  `24,069,661,628` bytes total, `45` emergency-eligible artifacts,
  `22,700,847,442` eligible bytes, and `removed_count=0`. No `--apply` ran.

## Explicit changed-file allowlist

- `polynexus/core/scientific_review.py`
- `polynexus/gui/main_window_results_mixin.py`
- `polynexus/gui/i18n.py`
- `tests/test_scientific_review.py`
- `tests/test_scientific_review_workbench.py`
- `docs/superpowers/specs/2026-07-31-saxs-workbench-scientific-review-entry-design.md`
- `docs/superpowers/plans/2026-07-31-saxs-workbench-scientific-review-entry.md`
- `docs/agent/tasks/2026-07-31-saxs-workbench-scientific-review-entry.md`
- `docs/acceptance/2026-07-31-saxs-workbench-scientific-review-entry.md`

## Pre-existing workspace changes

The shared checkout contains `docs/agent/memory/current-state.md`,
`docs/agent/memory/active-work.md`, `pytest.ini`, extensive scratch/test-storage
directories, and unrelated parallel work. They remain untouched and outside
this task's checkpoint because other tasks changed them concurrently.
