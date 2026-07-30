---
task_id: 2026-07-30-saxs-real-boundary-current-head-reaudit
kind: scientific-verification
status: completed
date: 2026-07-30
title: Re-audit current-head real SAXS lifecycle and 2D boundary
---

# Current-head Real SAXS Boundary Re-audit

## Goal

Refresh automated real-fixture evidence after the current SAXS and shared
Workbench checkpoints without changing scientific meaning.

## Non-goals

- No production code or scientific policy change.
- No edits to real fixtures, generated outputs, D: storage, or parallel files.
- No inference of calibration, mask validity, orientation meaning, or
  publication approval from a passing test.

## Affected boundaries

- `tests/test_saxs_real_2d_scientific_acceptance.py` PAD8 contract.
- SAXS cases in `tests/test_real_published_run_walkthrough.py`.
- This task's evidence documents only.

## Acceptance criteria

- [x] PAD8 2D boundary produces a complete pytest summary and exit code.
- [x] Static/Temperature/Strain lifecycle produces a complete pytest summary
      and exit code.
- [x] The evidence confirms conservative audit/publication behavior without
      promoting diagnostic results.
- [x] Human detector/scientific/release gates remain explicit.
- [x] Task checks, diff hygiene, and an explicit documentation checkpoint are
      recorded; no storage apply is run.

## Evidence

- PAD8 boundary: `python -m pytest -q tests/test_saxs_real_2d_scientific_acceptance.py -vv --basetemp=C:\Temp\PolyNexus_saxs_real_boundary_pad8_current` returned `4 passed in 17.35s`, exit code `0`.
- Real lifecycle: `python -m pytest -q tests/test_real_published_run_walkthrough.py -k saxs -vv --basetemp=C:\Temp\PolyNexus_saxs_real_boundary_lifecycle_current` collected 15 items, selected 3, and returned `3 passed, 12 deselected in 78.23s`, exit code `0`.
- Both runs used read-only existing fixtures and separate C: basetemps.
- No production files, real fixtures, generated outputs, or D: storage were
  changed. No `test_storage.py --apply` ran.

## Implementation plan

1. Run the PAD8 contract with a dedicated C: basetemp.
2. Run the three selected real SAXS lifecycle cases with a separate C:
   basetemp and require complete summaries.
3. Record exact outcomes and limitations, then run task/diff checks.
4. Create a four-file documentation-only allowlist checkpoint.

## Verification

```powershell
python -m pytest -q tests/test_saxs_real_2d_scientific_acceptance.py -vv --basetemp=C:\Temp\PolyNexus_saxs_real_boundary_pad8_current
python -m pytest -q tests/test_real_published_run_walkthrough.py -k saxs -vv --basetemp=C:\Temp\PolyNexus_saxs_real_boundary_lifecycle_current
python scripts/verify.py --task docs/agent/tasks/2026-07-30-saxs-real-boundary-current-head-reaudit.md --changed --types
git diff --check
```

Each pytest command counts only with a complete summary and exit code `0`.
`python scripts/test_storage.py --apply` is not part of this task.

## Explicit changed-file allowlist

- `docs/superpowers/specs/2026-07-30-saxs-real-boundary-current-head-reaudit-design.md`
- `docs/superpowers/plans/2026-07-30-saxs-real-boundary-current-head-reaudit.md`
- `docs/agent/tasks/2026-07-30-saxs-real-boundary-current-head-reaudit.md`
- `docs/acceptance/2026-07-30-saxs-real-boundary-current-head-reaudit.md`
