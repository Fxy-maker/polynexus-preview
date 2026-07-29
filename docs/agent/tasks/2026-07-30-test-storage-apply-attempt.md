---
task_id: 2026-07-30-test-storage-apply-attempt
kind: maintenance
status: completed
date: 2026-07-30
title: Execute user-authorized stale test storage cleanup
---

# Test storage apply attempt

## Goal

Execute the user's explicit `--apply` request using the repository-managed
test-storage cleanup command, while preserving protected and permission-
restricted directories.

## Non-goals

- Do not bypass ACLs or use administrator-only deletion techniques.
- Do not delete source files, real datasets, Git-tracked files, or active test
  artifacts.
- Do not move the remaining artifacts to another drive as part of this attempt.

## Affected boundaries

- `scripts/test_storage.py` cleanup behavior and its externally discovered test
  artifact roots.
- Durable task, acceptance, and active-work evidence only; no production code
  or regression dataset changes.

## Implementation plan

1. Confirm that no Python or pytest process is active before cleanup.
2. Run the exact user-authorized `clean --older-than-hours 24 --apply`
   command.
3. Record the real exit result and the permission error without bypassing it.
4. Run a post-apply dry-run report and update durable evidence.

## Verification

- `python scripts/test_storage.py clean --older-than-hours 24 --apply`
  returned exit code `1` after a partial cleanup because the managed command
  hit `WinError 5`.
- `python scripts/test_storage.py report --json` was run after the attempt;
  the resulting state is recorded below.
- `python scripts/verify.py --task docs/agent/tasks/2026-07-30-test-storage-apply-attempt.md --changed --types`
  is the required task-scoped repository verification command.
- `git diff --check` is required before the checkpoint.

## Acceptance criteria

- [x] The apply command ran only after no Python/pytest process was active.
- [x] The exact command and exit result are recorded.
- [x] A post-apply report records the remaining artifacts and eligible bytes.
- [x] No ACL bypass, source/data deletion, migration, or manual broad cleanup
      was performed.

## Evidence

Before apply, the storage report showed `576` artifacts, `42` eligible, and
`33891211690` eligible bytes; C: had `0` eligible entries. The command was:

```powershell
python scripts/test_storage.py clean --older-than-hours 24 --apply
```

It partially removed eligible artifacts and returned exit code `1` after six
old zero-byte D:\PolyNexus legacy directories reported `WinError 5` (access
denied). No ACL escalation was attempted.

Successfully removed by the same command:

- `C:\TempPolyNexus_full_goal_recheck_20260730`
- `C:\TempPolyNexus_full_goal_recheck_20260730_bg_pytest`
- `C:\TempPolyNexus_pad8_acceptance_goal_recheck_20260730`
- `C:\TempPolyNexus_real_saxs_goal_recheck_20260730`
- `C:\TempPolyNexus_real_saxs_goal_recheck_20260730_bg_pytest`
- `C:\TempPolyNexus_saxs_quality_program_task_verify_20260730_bg_pytest`

The post-apply report (dry-run) showed `41` artifacts, `35` protected, and
`0` eligible bytes. Six zero-byte D: legacy directories remain eligible by
name but cannot release additional space; all non-zero artifacts are protected
by retention or active status. C: has no remaining eligible artifacts. C: free
space is `182.27 GB`; D: free space is `125.60 GB` at the time of recording.

## Known limitation

The six remaining eligible directories require a permission repair or explicit
administrator-side cleanup before they can be removed, but they are zero-byte
directories and do not affect disk capacity. The current agent did not bypass
ACLs or issue another delete command.

## Explicit changed-file allowlist

- `docs/agent/tasks/2026-07-30-test-storage-apply-attempt.md`
- `docs/acceptance/2026-07-30-test-storage-apply-attempt.md`
- `docs/agent/memory/active-work.md`
