---
task_id: 2026-07-31-saxs-post-workbench-real-boundary
kind: scientific-verification
status: completed
date: 2026-07-31
title: Refresh post-Workbench real SAXS boundary evidence
---

# Post-Workbench Real SAXS Boundary Recheck

## Goal

Refresh automated evidence for the existing PAD8 2D acceptance contract and
real SAXS Static/Temperature/Strain lifecycle after checkpoint `0abc550`.

## Non-goals

- No production code, algorithm, threshold, quality level, physical gate,
  rescue, AI, Figure, Manifest, Export, or publication-role change.
- No detector calibration, beam-center inference, mask validity decision,
  orientation assignment, interpolation, frame repair, or reviewer decision.
- No edits to real fixtures, generated outputs, D: test directories, or
  parallel memory/worktree files.

## Affected boundaries

- `tests/test_saxs_real_2d_scientific_acceptance.py`: existing PAD8 contract.
- `tests/test_real_published_run_walkthrough.py`: existing SAXS lifecycle
  selector for Static, Temperature, and Strain.
- This task's spec, plan, acceptance record, and task evidence only.

## Implementation plan

1. Run the existing PAD8 2D acceptance test with a dedicated external D:
   basetemp and retain its complete pytest summary and exit code.
2. Run the existing real SAXS lifecycle selector for Static, Temperature, and
   Strain with a separate external D: basetemp and retain its complete summary
   and exit code.
3. Record only actual outcomes and limitations, run the structured verifier,
   diff check, and storage dry-runs, then create the four-document checkpoint.

## Acceptance criteria

- [x] PAD8 2D contract produces a complete pytest summary and exit code `0`.
- [x] Real SAXS Static/Temperature/Strain selector produces a complete pytest
      summary and exit code `0`.
- [x] Results are classified from actual output; timeout/setup/crash/no-summary
      is recorded as incomplete, never as pass.
- [x] Existing conservative quality, physical-gate, detector/orientation, and
      publication limitations remain explicit.
- [x] Task verifier, diff check, storage report/clean dry-run, and explicit
      allowlist checkpoint are recorded; no storage apply is run.

## Evidence

- PAD8: `python -m pytest -q tests/test_saxs_real_2d_scientific_acceptance.py
  -vv --basetemp=D:\PolyNexus-test-runs\saxs-post-workbench-pad8-20260731`
  → `4 passed in 18.60s`, exit code `0`.
- Real lifecycle: `python -m pytest -q
  tests/test_real_published_run_walkthrough.py -k saxs -vv
  --basetemp=D:\PolyNexus-test-runs\saxs-post-workbench-lifecycle-20260731`
  → `3 passed, 12 deselected in 90.79s`, exit code `0`.
- Task verifier exited `0`: quality gate `297 passed`, preprocessing gate
  `106 passed`, task/memory, Ruff, compile, type baseline, and whitespace
  checks passed.
- `git diff --check` exited `0`.
- Storage `report --json` and `clean --older-than-hours 24 --json` exited `0`
  in dry-run mode. The clean inventory reported `88` artifacts,
  `24,069,661,628` bytes total, `22,700,847,442` eligible bytes,
  `45` emergency-eligible artifacts, and `removed_count=0`. No `--apply` ran.
- The explicit four-document documentation checkpoint is created after the
  final allowlist review; no production or test source file is in this task.

## Verification

```powershell
python -m pytest -q tests/test_saxs_real_2d_scientific_acceptance.py -vv --basetemp=D:\PolyNexus-test-runs\saxs-post-workbench-pad8-20260731
python -m pytest -q tests/test_real_published_run_walkthrough.py -k saxs -vv --basetemp=D:\PolyNexus-test-runs\saxs-post-workbench-lifecycle-20260731
python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-post-workbench-real-boundary.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24 --json
git diff --check
```

Each pytest command counts only with a complete summary and exit code `0`.
The storage commands are non-destructive dry-runs. `test_storage.py --apply`
is not part of this task.

## Explicit changed-file allowlist

- `docs/superpowers/specs/2026-07-31-saxs-post-workbench-real-boundary-design.md`
- `docs/superpowers/plans/2026-07-31-saxs-post-workbench-real-boundary.md`
- `docs/agent/tasks/2026-07-31-saxs-post-workbench-real-boundary.md`
- `docs/acceptance/2026-07-31-saxs-post-workbench-real-boundary.md`

`docs/agent/memory/active-work.md`, `docs/agent/memory/current-state.md`,
`pytest.ini`, all scratch/test-storage directories, and unrelated GUI/NMR
changes are outside this checkpoint.

## Current status

Automated evidence recording is complete. Human restarted-GUI review,
instrument-aware detector/orientation review, temperature/strain scientific
meaning review, and final publication/release approval remain open regardless
of automated outcomes.
