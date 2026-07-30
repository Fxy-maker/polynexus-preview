---
task_id: 2026-07-30-current-head-saxs-verification-recheck
kind: verification-audit
status: completed
date: 2026-07-30
title: Recheck current SAXS matrix and classify full-boundary failures
---

# Current-head SAXS verification recheck

## Goal

Record fresh current-head SAXS evidence after the dirty Figure projection
checkpoints and classify the repository-wide full/boundary outcomes without
turning native Qt crashes, tool aborts, or setup errors into test passes.

## Non-goals

- No production SAXS, GUI, scientific threshold, quality level, publication,
  AI, rescue, or reviewer policy change.
- No real dataset, generated output, scratch directory, or test-storage
  cleanup change.
- No claim of full repository release approval from the SAXS-only matrix.

## Affected boundaries

- Fresh SAXS test matrix on the current `b5cbc92` checkout.
- Full/boundary verification classification and its Qt/environment evidence.
- Durable verification memory and acceptance handoff only.

## Acceptance criteria

- [x] A fresh SAXS matrix completes with a final pytest summary and exit code.
- [x] The earlier full run's `Qt6Widgets.dll` access violation is recorded as
      a verification failure, not a test pass.
- [x] The offscreen full run aborted without a result and is recorded as
      unknown, not as a pass.
- [x] Basetemp permission setup errors are separated from production failures.
- [x] Storage cleanup remains dry-run only and no `--apply` is executed.

## Implementation plan

1. Inspect the current process state and run a fresh SAXS matrix with an
   isolated offscreen Qt environment and a writable workspace basetemp.
2. Reproduce or isolate the full-suite failure boundary without changing
   production code.
3. Record exact summaries, exit codes, warnings, and limitations in the task,
   acceptance note, and durable active-work memory.
4. Run the task-scoped verifier and diff hygiene checks, then create one
   explicit documentation-only checkpoint.

## Verification

```powershell
$env:QT_QPA_PLATFORM='offscreen'
$env:QT_OPENGL='software'
& 'D:\PolyNexus\Python\pythoncore-3.14-64\python.exe' -m pytest -q (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName }) -o addopts= --basetemp=D:\PolyNexus\.pytest-run-current\pytest\saxs_matrix_post_b5_offscreen_20260730
python scripts/verify.py --task docs/agent/tasks/2026-07-30-current-head-saxs-verification-recheck.md --changed --types
& 'D:\PolyNexus\Python\pythoncore-3.14-64\python.exe' scripts/verify.py --task docs/agent/tasks/2026-07-30-current-head-saxs-verification-recheck.md --changed --types
git diff --check
& 'D:\PolyNexus\Python\pythoncore-3.14-64\python.exe' scripts/test_storage.py report --json
& 'D:\PolyNexus\Python\pythoncore-3.14-64\python.exe' scripts/test_storage.py clean --older-than-hours 24
```

The SAXS matrix counts as passed only because it produced a complete summary
and exit code `0`. The full/boundary outcomes below remain limitations.

## Evidence

- Fresh SAXS matrix: `594 passed, 8 warnings in 524.50s`, exit code `0`, using
  repository Python 3.14, `QT_QPA_PLATFORM=offscreen`, `QT_OPENGL=software`,
  and a writable workspace basetemp.
- The first fresh full/boundary attempt passed focused quality `290` and
  preprocessing `106`, then crashed at about 27% of full pytest with Windows
  access violation `0xC0000005`; WER identified
  `PySide6\Qt6Widgets.dll`. It exited `1` without a final pytest summary or
  boundary result.
- The isolated `tests/test_chart_editor_workflow.py` probe passed `57` tests
  with `4` existing warnings, so no stable single-test assertion failure was
  reproduced.
- A second full/boundary attempt with offscreen Qt was aborted by the tool and
  left no pytest process or final summary; it is classified `aborted/unknown`.
- An initial SAXS attempt using a basetemp outside the writable workspace
  produced `514 passed, 80 errors` from `PermissionError [WinError 5]` during
  pytest setup. It is environment setup evidence, not a production failure.
- The latest storage dry-run reported `54` artifacts, `eligible_bytes=13390550`,
  `eligible=6`, and `removed=0`; `test_storage.py --apply` was not run.
- The task-scoped verifier completed task-card, memory, Ruff, compile, and
  type-baseline checks, but its focused quality gate returned `288 passed, 2
  failed, 3 warnings` and exit code `1`. Both failures are pre-existing locale
  expectation mismatches in `tests/test_history_table_service.py`: the tests
  expect English `Scientific review` while the current locale emits Chinese
  `科学复核`. The initial standard invocation also exposed the runner's missing
  `ruff`/external-basetemp permissions; the rerun used the already-installed
  repository executables and a workspace test root to reach the actual tests.

## Known limitations

This recheck strengthens SAXS-only evidence but does not close the full
repository boundary. Native Qt full-suite stability, restarted-GUI visual
review, reviewer-owned scientific values, and final release authorization
remain separate gates.

## Explicit changed-file allowlist

- `docs/agent/tasks/2026-07-30-current-head-saxs-verification-recheck.md`
- `docs/acceptance/2026-07-30-current-head-saxs-verification-recheck.md`
- `docs/superpowers/plans/2026-07-30-current-head-saxs-verification-recheck.md`
- `docs/agent/memory/active-work.md`
