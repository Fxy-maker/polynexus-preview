---
kind: task
status: completed
date: 2026-07-28
title: Manage pytest storage and clean stale test artifacts
---

# Managed test storage and cleanup

## Goal

Move default pytest temporary storage outside the repository onto the current
project drive, and add a dry-run-first command to clean stale legacy and
managed test directories without touching protected data.

## Non-goals

- Do not delete test source, real regression data, worktrees, branches, or user
  files outside the test-storage roots.
- Do not terminate or modify a running test process.
- Do not rewrite every historical task card that contains an explicit basetemp.
- Do not automatically clean directories younger than the configured retention.

## Acceptance criteria

- [x] Default pytest runs use a unique external basetemp under
      `D:\PolyNexus-test-runs` unless `--basetemp` is explicitly supplied.
- [x] `scripts/test_storage.py report` lists size, age, class, and active/young
      protection for legacy and managed test artifacts.
- [x] `scripts/test_storage.py clean` is dry-run by default and `--apply` only
      removes eligible stale directories.
- [x] Focused tests cover root resolution, artifact classification, retention,
      active-process protection, and dry-run behavior.
- [x] Existing source/data/worktree paths remain protected.

## Affected boundaries

- Pytest startup configuration (`pytest.ini`, `conftest.py`)
- Local test artifact storage and cleanup CLI
- Maintenance documentation and agent contract
- Focused storage regression tests

## Implementation plan

1. Add the storage task/spec/plan and validate the task card.
2. Write failing tests for storage-root resolution and safe cleanup planning.
3. Implement external per-run basetemp selection and the report/clean CLI.
4. Run verification, inspect the report while the active pytest process is
   protected, remove only eligible stale test artifacts, and checkpoint the
   owned files.

## Verification

```bash
pytest tests/test_test_storage.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-28-managed-test-storage.md --changed --types
python scripts/verify.py --changed --types
```

## Completion report

- Changed: default pytest basetemp now uses unique external directories under
  `D:\PolyNexus-test-runs` (or `POLYNEXUS_TEST_ROOT`); added
  `scripts/test_storage.py` report/clean commands and 7 focused tests; updated
  `AGENTS.md` and `README.md`.
- Verification: `pytest tests/test_test_storage.py -q` passed (`7 passed`);
  structured verification passed with quality `283` and preprocessing `106`.
- Cleanup: the explicit 24-hour cleanup removed eligible legacy test scratch;
  active, young, protected, and failed/blocked paths were retained. D: free
  space increased from about 215.85GB to 220.24GB.
- Known limitation: historical commands with explicit `--basetemp=C:\Temp\...`
  still control their own location; the new default only applies when no
  explicit basetemp is supplied.
- Pre-existing changes left untouched: current SAXS/GUI/history edits,
  existing task/acceptance drafts, active worktrees, and recent test artifacts.
