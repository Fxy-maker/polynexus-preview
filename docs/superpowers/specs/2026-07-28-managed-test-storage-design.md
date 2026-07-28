---
kind: design
status: approved
date: 2026-07-28
title: Managed test storage and cleanup
---

# Managed test storage and cleanup

## Goal

Prevent repeated pytest and acceptance runs from filling repository or system
disks by giving every default test process an external, per-run basetemp and a
safe retention-based cleanup command.

## Design

The repository-local `conftest.py` assigns a unique basetemp under
`POLYNEXUS_TEST_ROOT` when the caller did not explicitly pass `--basetemp`.
The default root is `<project-drive>:\PolyNexus-test-runs`, so the current D:
worktree uses `D:\PolyNexus-test-runs`. Explicit basetemps remain supported for
specialized acceptance runs.

`scripts/test_storage.py` reports and cleans two classes of artifacts:

- legacy top-level repository directories whose names contain `pytest_tmp` or
  `tmp_pytest`;
- managed per-run directories under `<test-root>\pytest\run-*`.

Cleanup is dry-run by default. `--apply` removes only directories older than
the retention period, outside protected paths, not tracked by Git, and not
referenced by a currently running process command line. Failed or skipped
removals are reported rather than silently retried.

## Non-goals and protections

- Never delete `tests/eval`, real datasets, source files, worktrees, or Git
  branches.
- Never terminate test processes.
- Never remove an explicitly supplied basetemp during the same run.
- Do not clean the existing legacy directories until the active-process and
  retention checks have produced a dry-run report.
