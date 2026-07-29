---
task_id: 2026-07-29-test-storage-apply-fail-soft
kind: maintenance
status: completed
date: 2026-07-29
title: Make test-storage apply fail-soft and observable
---

# Test-storage apply fail-soft and observable

## Goal

Allow the managed test-storage apply command to continue deleting independent
eligible directories after one ACL/runtime deletion failure, while returning a
non-zero status and reporting every failed path.

## Non-goals

- No ACL repair, elevation, forced ownership, or broad deletion.
- No changes to eligibility, retention, approved-root, active-process,
  protected-path, Git-tracked, or symlink safety rules.
- No changes to real datasets, source files, generated outputs, or runtime
  directories.
- No breaking change to the existing `apply_cleanup(...) -> list[Path]` helper.

## Affected boundaries

- `scripts/test_storage.py`: detailed fail-soft apply result and CLI reporting.
- `tests/test_test_storage.py`: simulated deletion-failure and CLI regressions.
- this task's design and implementation plan.

## Implementation plan

1. Add regressions for continuing after one deletion failure and for CLI
   partial-result reporting.
2. Add immutable detailed apply results while preserving the existing helper
   return type and safety gates.
3. Route the CLI through the detailed result, emit failure records, and return
   a non-zero status for partial apply.
4. Run focused/full storage tests, the structured verifier, and storage
   report/dry-run before the allowlist checkpoint.

## Acceptance criteria

- [x] One failed eligible deletion does not prevent later eligible paths from
  being attempted.
- [x] Each deletion failure records its path, exception type, and message.
- [x] CLI apply emits partial results and exits non-zero when failures exist.
- [x] Successful removals remain reported as removed.
- [x] Dry-run and all existing safety gates remain unchanged.
- [x] TDD RED/GREEN, task verifier, focused storage tests, diff audit, and an
  explicit allowlist checkpoint are recorded.

## Verification evidence

- TDD RED for the detailed operation: `1 failed, 27 deselected`; the failure
  was the expected missing `apply_cleanup_detailed` capability assertion.
- TDD RED for the CLI contract: `1 failed, 28 deselected`; the old CLI
  returned `0` and emitted no `failures` field after a simulated permission
  failure.
- TDD GREEN: the two new regressions passed; the complete storage suite passed
  `28 passed, 1 skipped`.
- Task-scoped verifier passed: quality `287 passed`, preprocessing `106
  passed`, task/memory checks, Ruff, compile, type baseline, and whitespace
  checks all passed.
- Storage report/dry-run completed without deletion: `301` artifacts,
  `15683176309` total bytes, `8` eligible bytes, `18` eligible entries,
  `283` younger-than-retention entries, and `0` cleanup failures.
- The real `--apply` command is intentionally not repeated by this code task;
  its earlier ACL failure remains recorded in
  `docs/agent/tasks/2026-07-30-test-storage-apply-attempt.md`.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PN_storage_apply_fail_soft'
python -m pytest -q tests/test_test_storage.py -k apply
python -m pytest -q tests/test_test_storage.py
python scripts/verify.py --task docs/agent/tasks/2026-07-29-test-storage-apply-fail-soft.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
git diff --check
```

The storage commands in this task are dry-run only; the user-authorized
real-data cleanup was a separate maintenance action and is not repeated here.

## Explicit changed-file allowlist

- `scripts/test_storage.py`
- `tests/test_test_storage.py`
- `docs/agent/tasks/2026-07-29-test-storage-apply-fail-soft.md`
- `docs/superpowers/specs/2026-07-29-test-storage-apply-fail-soft-design.md`
- `docs/superpowers/plans/2026-07-29-test-storage-apply-fail-soft.md`

## Pre-existing workspace changes

The modified `docs/agent/memory/current-state.md`, historical test/storage
directories, and all other parallel files remain outside this checkpoint.
