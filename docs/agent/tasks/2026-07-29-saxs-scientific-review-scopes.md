---
task_id: 2026-07-29-saxs-scientific-review-scopes
kind: scientific-schema
status: completed
date: 2026-07-29
title: Add independent SAXS 1D and 2D scientific review scopes
---

# SAXS scientific review scopes

## Goal

Add `saxs.1d` and `saxs.2d` to the shared reviewer-owned scientific review
record without changing any SAXS analysis or publication behavior.

## Non-goals

- No new physical threshold, fitting rule, rescue behavior, or publication
  upgrade.
- No engine, GUI, Figure, Manifest, Export, or Workbench integration.
- No inference of reviewer decisions from existing data.
- No edits to real datasets, generated outputs, scratch, or parallel GUI work.

## Affected boundaries

- `polynexus/core/scientific_review.py`: scope registry and required-key map.
- `tests/test_scientific_review.py`: focused contract regression tests.
- Documentation and durable task evidence only.

## Acceptance criteria

- [x] `REVIEW_SCOPES` contains `saxs.1d` and `saxs.2d` while retaining all
      existing scopes.
- [x] Non-pending `saxs.1d` records require the five documented 1D decisions.
- [x] Non-pending `saxs.2d` records require the six documented 2D decisions.
- [x] Pending records can be created without reviewer decision values.
- [x] Complete accepted records promote only for the matching scope/source.
- [x] Missing decision keys, malformed values, wrong scope, and all existing
      denied statuses remain fail-closed.
- [x] No SAXS engine result, quality level, physical gate, or publication role
      changes.
- [x] The checkpoint contains only the explicit allowlist below.

## Current TDD evidence

- RED: `5 failed, 10 passed`; failures were the expected unsupported SAXS
  scope errors before the production extension.
- GREEN: `15 passed in 0.13s` after adding only the scope registry and required
  decision-key tuples.

## Verification evidence

- Task-scoped verifier exited `0`: task/memory checks, Ruff, compile, quality
  `290 passed`, preprocessing `106 passed`, and whitespace all passed.
- Exact SAXS matrix exited `0`: `575 passed, 6 warnings in 518.52s`.
- `git diff --check` exited `0`.
- The allowlist audit found this task's three tracked and four untracked files;
  pre-existing `docs/agent/memory/current-state.md` stayed outside. Same-file
  policy/provenance edits remain outside this checkpoint; the SAXS hunks were
  selectively staged so no unrelated hunk was included.
- Storage report/clean were dry-run only: `40` artifacts, `0` eligible bytes,
  `6` zero-byte legacy entries classified eligible, `34` younger-than-retention
  entries, and `0` removed. `test_storage.py --apply` was not run.

## Implementation plan

1. Add real-record RED tests for both scope registrations, complete accepted
   records, pending records without decisions, missing required keys, and
   cross-scope denial.
2. Extend only the shared `REVIEW_SCOPES` registry and
   `_REQUIRED_DECISION_KEYS` map with the approved SAXS names and keys.
3. Run the focused review tests, task-scoped verifier, exact SAXS matrix, and
   diff audit; record final results and create the explicit checkpoint.

## Verification

```powershell
python -m pytest -q tests/test_scientific_review.py
python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-scientific-review-scopes.md --changed --types
python -m pytest -q (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName })
git diff --check
```

The SAXS matrix is counted only from a final pytest summary and exit code `0`.
Storage inspection remains dry-run only; no `test_storage.py --apply` is part
of this task.

## Verification commands

```powershell
python -m pytest -q tests/test_scientific_review.py
python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-scientific-review-scopes.md --changed --types
python -m pytest -q (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName })
git diff --check
```

The exact SAXS matrix must be counted only from a final pytest summary and
exit code 0. No historical or timeout-only output is evidence of a pass.

## Explicit changed-file allowlist

- `polynexus/core/scientific_review.py`
- `tests/test_scientific_review.py`
- `docs/superpowers/specs/2026-07-29-saxs-scientific-review-scopes-design.md`
- `docs/superpowers/plans/2026-07-29-saxs-scientific-review-scopes.md`
- `docs/agent/tasks/2026-07-29-saxs-scientific-review-scopes.md`
- `docs/acceptance/2026-07-29-saxs-scientific-review-scopes.md`
- `docs/agent/memory/active-work.md`

Pre-existing modifications to `docs/agent/memory/current-state.md`, GUI files,
untracked scientific-review visibility files, `.superpowers`, test-storage
directories, and all other untracked paths are intentionally excluded.
