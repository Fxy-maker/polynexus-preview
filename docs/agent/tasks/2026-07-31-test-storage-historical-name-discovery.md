---
kind: task
status: completed
date: 2026-07-31
title: Discover historical test-storage directory names
---

# Historical test-storage name discovery

## Goal

Make `scripts/test_storage.py` report the historical PolyNexus test
directories that were previously missed, while keeping real data and evidence
paths protected.

## Non-goals

- Do not delete or move any real data, source, memory, evidence, or worktree.
- Do not change retention, emergency timing, active-process, Git, symlink, or
  approved-root cleanup gates.
- Do not run `clean --apply` as part of implementation verification.

## Affected boundaries

- `scripts/test_storage.py`: bounded legacy-name classification.
- `tests/test_test_storage.py`: discovery and protected-name regression.
- Task design, implementation plan, and durable memory.

## Implementation plan

1. Add a failing discovery test for the observed historical directory families
   and protected names.
2. Extend `_is_known_legacy_name()` with the bounded historical prefixes while
   keeping protected-name rejection first.
3. Run focused storage tests, task-scoped verification, diff checks, and the
   real report/clean dry-run; review eligible paths before any apply.
4. Create one checkpoint with the explicit changed-file allowlist.

## Acceptance criteria

- [x] `full_boundary*`, `native_*_basetemp`, `gallery_*`, `saxs_*_matrix`, and
  the observed `Saxs*` test families appear in the inventory.
- [x] `测试数据`, archive, review, evidence, and baseline names remain absent
  from cleanup candidates.
- [x] Focused storage tests, task verifier, and diff check pass.
- [x] Real report and clean remain dry-run and their JSON inventory is reviewed.
- [x] One explicit changed-file allowlist checkpoint is created.

## Verification

```powershell
python -m pytest -q tests/test_test_storage.py
python scripts/task_check.py --task docs/agent/tasks/2026-07-31-test-storage-historical-name-discovery.md
python scripts/verify.py --task docs/agent/tasks/2026-07-31-test-storage-historical-name-discovery.md --changed --types
git diff --check
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24 --json
```

## Verification evidence

- RED focused test failed before implementation because the new historical
  families were absent from discovery.
- Focused storage test passed: `1 passed in 0.31s`.
- Full storage test passed: `39 passed, 1 skipped in 3.71s`.
- Task check, compile, `git diff --check`, and structured verifier passed.
  The verifier reported quality `297 passed`, preprocessing `106 passed`, and
  no changed type-baseline targets.
- Final report inventory: `240` artifacts, `55,660,682,837` bytes total,
  `117` eligible artifacts and `26,825,556,265` eligible bytes.
- Final clean dry-run inventory: `241` artifacts, `56,658,056,745` bytes
  total, `117` eligible artifacts and `26,825,556,265` eligible bytes;
  `removed=0`, `failures=0`, and `protected_eligible=0` for the explicit
  `测试数据/archive/review/evidence/baseline` audit.
- No `clean --apply` was run in this task.

## Explicit changed-file allowlist

- `scripts/test_storage.py`
- `tests/test_test_storage.py`
- `docs/superpowers/specs/2026-07-31-test-storage-historical-name-discovery-design.md`
- `docs/superpowers/plans/2026-07-31-test-storage-historical-name-discovery.md`
- `docs/agent/tasks/2026-07-31-test-storage-historical-name-discovery.md`

## Pre-existing workspace changes

The shared checkout contains concurrent SAXS/Results changes, memory updates,
many historical test directories, and an in-progress formal pytest collection
task. They remain outside this task's checkpoint.
