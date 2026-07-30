---
task_id: 2026-07-30-saxs-current-head-matrix-audit
kind: verification-audit
status: completed
date: 2026-07-30
title: Audit current-head SAXS matrix after Workbench provenance checkpoint
---

# Current-head SAXS Matrix Audit

## Goal

Establish fresh SAXS-only regression evidence for the current checkout after
the Workbench detector provenance checkpoint `fd9bb3d`.

## Non-goals

- No production SAXS, GUI, scientific threshold, quality-level, publication,
  AI, rescue, or reviewer-policy changes.
- No full-repository release approval claim.
- No edits to real datasets, generated outputs, test storage, or parallel
  Scientific Review files.

## Affected boundaries

- All repository tests matching `tests/test_saxs_*.py`.
- Task-scoped verifier and diff hygiene only.
- This task's documentation and acceptance evidence.

## Implementation plan

1. Enumerate the current repository `test_saxs_*.py` file set and run the
   complete SAXS-only matrix with offscreen Qt and a writable basetemp.
2. Classify the result from the complete pytest summary, exit code, and any
   emitted warnings or failures.
3. Run the structured verifier and diff hygiene checks, then record the
   evidence and create a documentation-only checkpoint.

## Acceptance criteria

- [x] The current complete SAXS test-file set is executed.
- [x] Pytest produces a complete summary and exit code is recorded.
- [x] Failures, setup errors, crashes, and timeouts are classified from actual
      output and are not relabeled as passes.
- [x] Task verification and `git diff --check` are complete.
- [x] An explicit documentation-only allowlist checkpoint is created.

## Verification commands

```powershell
$env:QT_QPA_PLATFORM='offscreen'
$env:QT_OPENGL='software'
& 'D:\PolyNexus\Python\pythoncore-3.14-64\python.exe' -m pytest -q (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName }) -o addopts= --basetemp=D:\PolyNexus\.pytest-run-current\pytest\saxs_current_head_matrix_20260730
python scripts/verify.py --task docs/agent/tasks/2026-07-30-saxs-current-head-matrix-audit.md --changed --types
git diff --check
```

The SAXS matrix is accepted only with a complete pytest summary and exit code
`0`. This task does not run `test_storage.py --apply` or claim full/boundary
release evidence.

## Verification

The exact commands above are the authoritative matrix and structured verifier
commands. A timeout, setup error, crash, or process exit without a complete
pytest summary is recorded as incomplete rather than passed.

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-30-saxs-current-head-matrix-audit.md --changed --types
git diff --check
```

## Explicit changed-file allowlist

- `docs/superpowers/specs/2026-07-30-saxs-current-head-matrix-audit-design.md`
- `docs/superpowers/plans/2026-07-30-saxs-current-head-matrix-audit.md`
- `docs/agent/tasks/2026-07-30-saxs-current-head-matrix-audit.md`
- `docs/acceptance/2026-07-30-saxs-current-head-matrix-audit.md`
