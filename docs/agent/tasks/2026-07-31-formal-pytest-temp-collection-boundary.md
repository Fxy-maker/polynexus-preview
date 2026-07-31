---
task_id: 2026-07-31-formal-pytest-temp-collection-boundary
kind: test-infrastructure
status: in_progress
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
- [ ] Full verifier returns a complete pytest summary with wrapper exit code
      `0`; the single-process attempt reached the tool timeout instead.
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

## Explicit changed-file allowlist

- `pytest.ini`
- `docs/superpowers/specs/2026-07-31-formal-pytest-temp-collection-boundary-design.md`
- `docs/superpowers/plans/2026-07-31-formal-pytest-temp-collection-boundary.md`
- `docs/agent/tasks/2026-07-31-formal-pytest-temp-collection-boundary.md`
- `docs/acceptance/2026-07-31-formal-pytest-temp-collection-boundary.md`

The shared `docs/agent/memory/active-work.md` contains concurrent SAXS and
Results entries and is intentionally outside this checkpoint to avoid mixing
parallel task state. Its boundary entry is already updated in the worktree.
