---
task_id: 2026-07-31-formal-pytest-temp-collection-boundary
kind: test-infrastructure
status: completed
date: 2026-07-31
title: Exclude temporary diagnostic directories from formal pytest collection
---

# Formal pytest temporary-directory collection boundary

## Goal

Keep untracked temporary diagnostics from being collected by the formal
repository-wide pytest release gate, while retaining explicit direct-path
debugging behavior.

## Non-goals

- Do not edit, delete, migrate, or checkpoint `tests/_tmp_phase3`.
- Do not change production, scientific, GUI, SAXS, NMR, IR, or Joint logic.
- Do not run test-storage `--apply`.

## Affected boundaries

- `pytest.ini` formal collection configuration.
- Repository-wide `pytest -q` through `scripts/quality_gate.py`.
- Documentation and durable audit memory.

## Implementation plan

1. Reproduce the baseline collector and record the existing full-gate failure.
2. Add the narrow `_tmp*` collection exclusion to `pytest.ini`.
3. Verify formal collection, full/boundary release verification, and direct
   task-scoped checks.
4. Record exact evidence and create one explicit allowlist checkpoint.

## Acceptance criteria

- [x] Baseline collection includes `_tmp_phase3`, and the full run identifies
      its obsolete output-path assertion as the only failure.
- [x] Formal collection excludes `_tmp_phase3` while retaining the ordinary
      canonical test tree.
- [x] Full verifier returns a complete pytest summary with wrapper exit code
      `0`; the latest current-head run completed successfully.
- [x] Canonical tests were rerun in four explicit file slices with complete
      summaries, and the boundary audit passed.
- [x] Task-scoped verifier, diff check, and the scoped explicit allowlist
      checkpoint pass.

## Verification

```powershell
python -m pytest --collect-only -q
$env:POLYNEXUS_TEST_ROOT='D:\PolyNexus-test-runs-full-goal-20260731'
$env:POLYNEXUS_TEST_RETENTION='review'
python scripts/verify.py --changed --types --full --boundary
python scripts/verify.py --task docs/agent/tasks/2026-07-31-formal-pytest-temp-collection-boundary.md --changed --types
python scripts/boundary_audit.py --root D:\PolyNexus --json
git diff --check
```

The single-process full verifier attempt is recorded as a tool-level timeout:
exit `124` after the 30-minute command bound, with no pytest summary. It is not
classified as passed or failed. To obtain complete test summaries within the
available command bound, the canonical files were rerun in four explicit
pytest slices:

- Slice 1: `1006 passed, 4 warnings in 136.50s` (exit `0`).
- Slice 2: `709 passed in 498.25s` (exit `0`).
- Slice 3: `839 passed, 17 skipped, 2 warnings in 1037.97s` (exit `0`).
- Slice 4: `679 passed, 1 skipped, 6 warnings in 370.99s` (exit `0`).

The slice totals are `3233 passed, 18 skipped, 12 warnings`; no slice had a
failure. The task verifier passed with quality `297` and preprocessing `106`,
and the boundary audit returned exit `0`.

The prior timeout was superseded by the latest current-head wrapper run. With
`POLYNEXUS_TEST_ROOT=D:\PolyNexus-test-runs-full-goal-20260801-final` and
`POLYNEXUS_TEST_RETENTION=review`,
`python scripts/verify.py --changed --types --full --boundary` returned exit
code `0`. Its complete formal pytest summary was `3303 passed, 18 skipped, 12
warnings in 2244.54s (0:37:24)`. The focused quality gate passed `297`, the
preprocessing gate passed `106`, and the boundary audit returned exit `0`.
This is the authoritative full/boundary pass for this task; the older
tool-level timeout remains historical evidence only.

## Fresh rerun evidence (2026-07-31)

- `python scripts/verify.py --changed --types --full --boundary` reached the
  2104-second tool limit with no pytest summary and exit `124`; the spawned
  verifier/pytest processes were reaped afterward. This remains incomplete
  verification, not a pass or product-test failure.
- `python -m pytest --collect-only -q` returned exit `0` and reported
  `3275 tests collected in 3.50s`.
- The task-scoped verifier returned exit `0`, with quality `297 passed` and
  preprocessing `106 passed`; task, memory, Ruff, compile, type-baseline, and
  whitespace checks also passed.
- `python scripts/boundary_audit.py --root D:\PolyNexus --json` and
  `git diff --check` both returned exit `0`.
- Storage report and clean were both dry-run only: `64` artifacts,
  `22,285` eligible bytes, no cleanup failures, and no directories removed
  because `--apply` was not supplied. No
  `test_storage.py --apply` was run.

## Latest rerun evidence (2026-07-31)

- A fresh run used `POLYNEXUS_TEST_ROOT=D:\PolyNexus-test-runs-full-goal-20260731-rerun`
  with `POLYNEXUS_TEST_RETENTION=review`.
- `python scripts/verify.py --changed --types --full --boundary` reached the
  40-minute tool bound and returned exit `124` without a complete pytest
  summary. It is classified as tool-level timeout/incomplete evidence, not a
  pass or product-test failure.
- The verifier's own child processes were reaped after timeout; the separately
  shared SAXS pytest process was left untouched. No source or test file was
  changed by this rerun.
- The managed run manifest for the formal child records `status=failed` and
  `exit_code=3` at the timeout/reap boundary. Because no pytest summary or
  failure report was emitted, this is retained as incomplete tool evidence,
  not classified as a product-test failure. A second running manifest under
  the run directory came from the storage regression's mock pytest config and
  had no live PID; it is not evidence of an active formal run.

## Completion evidence (2026-08-01)

- Current-head full/boundary verification completed with exit code `0` and a
  complete pytest summary: `3303 passed, 18 skipped, 12 warnings in 2244.54s`.
- The task-scoped quality/preprocessing gates passed `297`/`106`; Ruff,
  compile, type-baseline, whitespace/diff, and boundary audit also passed.
- No pytest process remains active. The previous `124`/child-manifest `3`
  record is retained as historical incomplete evidence and is not used as the
  current classification.

## Explicit changed-file allowlist

- `pytest.ini`
- `docs/superpowers/specs/2026-07-31-formal-pytest-temp-collection-boundary-design.md`
- `docs/superpowers/plans/2026-07-31-formal-pytest-temp-collection-boundary.md`
- `docs/agent/tasks/2026-07-31-formal-pytest-temp-collection-boundary.md`
- `docs/acceptance/2026-07-31-formal-pytest-temp-collection-boundary.md`

The shared `docs/agent/memory/active-work.md` contains concurrent SAXS and
Results entries and is intentionally outside this checkpoint to avoid mixing
parallel task state. Its boundary entry is already updated in the worktree.
