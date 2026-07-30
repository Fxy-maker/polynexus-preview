---
task_id: 2026-07-30-current-head-full-boundary-post-cleanup-recheck
kind: release-verification-audit
status: in_progress
date: 2026-07-30
title: Current-head full and boundary recheck after test-storage rule update
---

# Current-head Full/Boundary Post-cleanup Recheck

## Goal

Establish fresh full/boundary evidence for the current checkout after the
updated test-storage rules and the completed fresh SAXS matrix.

## Non-goals

- No production, test, scientific-policy, quality-level, rescue, AI,
  publication, GUI, or detector-semantics changes.
- No deletion, migration, or `test_storage.py --apply`.
- No release approval or replacement of human scientific review.
- No edits to parallel NMR, Joint, GUI, scratch, real-data, or generated files.

## Affected boundaries

- `scripts/verify.py --changed --types --full --boundary`.
- `scripts/boundary_audit.py --root D:\PolyNexus --json`.
- Read-only test-storage report and cleanup plan.
- Documentation and durable audit memory only.

## Implementation plan

1. Inspect the current-head full/boundary verifier result without treating a
   missing pytest summary as a pass.
2. Run the boundary audit, storage report, and non-destructive clean plan;
   record eligible and removed counts separately.
3. Record the verification limitation and acceptance classification in the
   acceptance document and durable active-work memory.
4. Run task-scoped verification and `git diff --check`, then create one
   documentation-only allowlist checkpoint.

## Verification

```powershell
python scripts/verify.py --changed --types --full --boundary
python scripts/boundary_audit.py --root D:\PolyNexus --json
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24 --json
python scripts/verify.py --task docs/agent/tasks/2026-07-30-current-head-full-boundary-post-cleanup-recheck.md --changed --types
git diff --check
```

## Acceptance criteria

- [ ] Full verification produces a complete pytest summary and wrapper exit
      code; only exit `0` with complete output is a pass.
- [ ] Quality, preprocessing, and boundary outcomes are recorded separately.
- [ ] Any timeout, crash, setup error, disk error, or incomplete output is
      recorded as a limitation, not as a pass.
- [ ] Storage report and clean plan are dry-run only and record eligible and
      removed counts.
- [ ] Task-scoped verification and `git diff --check` pass.
- [ ] One explicit documentation-only allowlist checkpoint is created.

## Verification commands

```powershell
python scripts/verify.py --changed --types --full --boundary
python scripts/boundary_audit.py --root D:\PolyNexus --json
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24 --json
python scripts/verify.py --task docs/agent/tasks/2026-07-30-current-head-full-boundary-post-cleanup-recheck.md --changed --types
git diff --check
```

The verifier and boundary audit must be classified from their actual complete
output and exit codes. The storage commands are non-destructive; `--apply` is
not part of this task.

## Explicit changed-file allowlist

- `docs/superpowers/specs/2026-07-30-current-head-full-boundary-post-cleanup-recheck-design.md`
- `docs/superpowers/plans/2026-07-30-current-head-full-boundary-post-cleanup-recheck.md`
- `docs/agent/tasks/2026-07-30-current-head-full-boundary-post-cleanup-recheck.md`
- `docs/acceptance/2026-07-30-current-head-full-boundary-post-cleanup-recheck.md`
- `docs/agent/memory/active-work.md`

## Pre-existing workspace changes

The shared checkout contains parallel NMR/GUI/Joint source and test changes,
`docs/agent/memory/current-state.md`, many scratch/test-storage directories,
and other untracked task records. They remain untouched and outside this
checkpoint.
