---
task_id: 2026-07-31-nonsaxs-real-published-run-recheck
kind: real-data-verification
status: completed
date: 2026-07-31
title: Recheck non-SAXS real published-run lifecycle
---

# Non-SAXS real published-run recheck

## Goal

Re-run the existing real-fixture lifecycle for DSC, WAXS, IR, and NMR on the
current HEAD, covering engine output, Manifest/Gallery, Editor revisions,
Export provenance, and History restore.

## Non-goals

- No production-code, algorithm, threshold, quality, physical-gate, rescue, or
  AI-policy change.
- No changes to real fixtures, vendor files, generated outputs, or source data.
- No scientific promotion of a diagnostic-only, SI-only, validation-required,
  or assignment-limited result.
- No SAXS test, source, memory, or parallel task changes.

## Affected boundaries

- `tests/test_real_published_run_walkthrough.py` non-SAXS parameter cases.
- Existing DSC, WAXS, IR, and NMR engine/publication contracts.
- This task's documentation and its explicit allowlist only.

## Implementation plan

1. Inspect the existing real-fixture parameterization and confirm that
   `-k "not saxs"` selects DSC, WAXS, IR, NMR, WAXS strain, and IR
   temperature-2D cases.
2. Run the selector with a dedicated external D: basetemp and retain the
   complete pytest summary and exit code.
3. Record the exact outcome and role limitations, then run the task verifier,
   storage report/clean dry-runs, and diff check.
4. Create one three-document allowlist checkpoint without touching parallel
   memory or SAXS files.

## Acceptance criteria

- [x] The non-SAXS selector emits a complete pytest summary and exit code `0`.
- [x] The summary covers DSC standard/isothermal/non-isothermal, WAXS static/
      temperature/strain, IR standard/temperature-2D, and NMR liquid/solid
      H/C cases available in the repository.
- [x] The lifecycle assertions cover Manifest/Gallery, Editor working and
      published revisions, Export `metadata/runs/` and active pointer, and
      History restore.
- [x] Diagnostic-only, SI-only, validation-required, and assignment-limited
      outcomes remain explicitly unpromoted.
- [x] Task verifier, storage audit, and diff check have exact outcomes.
- [x] Existing native non-SAXS route captures were visually reviewed for
      Results-state clarity and conservative scientific status labels.
- [x] One allowlist checkpoint contains only this task's plan, task card, and
      acceptance record.

## Verification

```powershell
python -m pytest -q tests/test_real_published_run_walkthrough.py -k "not saxs" -vv --basetemp=D:\PolyNexus-test-runs\nonsaxs-real-published-20260731
python scripts/verify.py --task docs/agent/tasks/2026-07-31-nonsaxs-real-published-run-recheck.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24 --json
git diff --check
```

Each test result counts only with a complete pytest summary and exit code `0`.
The user had explicitly authorized the repository storage `--apply` cleanup in
the surrounding task. The cleanup tool was used; no manual deletion or rule
bypass was performed.

## Explicit changed-file allowlist

- `docs/superpowers/plans/2026-07-31-nonsaxs-real-published-run-recheck.md`
- `docs/agent/tasks/2026-07-31-nonsaxs-real-published-run-recheck.md`
- `docs/acceptance/2026-07-31-nonsaxs-real-published-run-recheck.md`

## Pre-existing changes left untouched

The shared checkout contains parallel SAXS work, memory-file edits, historical
test directories, external basetemps, and unrelated GUI/NMR work. They remain
outside this task's allowlist.

## Evidence

- D: first run: `11 passed, 1 failed, 3 deselected, 11 warnings in 227.26s`;
  WAXS strain failed while writing a TIFF with `OSError: [Errno 28] No space
  left on device`.
- C: second run reached `12 passed` but pytest exited through a D:-resident
  `.pytest_cache` write and reported `OSError: [Errno 28] No space left on
  device`; this is incomplete environment evidence, not a product failure.
- After the authorized storage apply, the final command
  `python -m pytest -p no:cacheprovider -q
  tests/test_real_published_run_walkthrough.py -k "not saxs" -vv
  --basetemp=C:\PolyNexus-test-runs\nonsaxs-real-published-20260731-c-after-clean`
  returned `12 passed, 3 deselected, 11 warnings in 291.31s`, exit `0`.
- The storage apply removed eligible artifacts and reclaimed the eligible
  inventory. Its exit code was `1` because ten permission-locked historical
  directories were safely skipped. After apply, D: had about `21.16 GB` free;
  the report showed `50` artifacts, `1,368,544,565` bytes total, and
  `eligible_bytes=0`. No manual deletion was used.

## Checkpoint

The three documentation files are ready for an explicit allowlist checkpoint.

## Verification evidence

- `python scripts/verify.py --task docs/agent/tasks/2026-07-31-nonsaxs-real-published-run-recheck.md --changed --types` exited `0`; task/memory checks, Ruff, compile, type baseline, whitespace, quality `297 passed`, and preprocessing `106 passed` all passed.
- `python scripts/boundary_audit.py --root D:\PolyNexus --json` exited `0`.
- `git diff --check` exited `0`.
- Final real-fixture selector: `12 passed, 3 deselected, 11 warnings in 291.31s`, exit `0`.
- Storage apply was already executed under explicit user authorization; it reclaimed eligible artifacts, skipped ten permission-locked historical directories, and left zero eligible bytes in the subsequent inventory.
- Native visual evidence from
  `D:\PolyNexus_native_all_routes_current_nonsaxs_post_joint_display_20260730`
  shows IR mapping `Review required`, NMR solid-C `Review required`, Joint
  `2 errors, 2 warnings` with `blocked / allowed=false`, and WAXS strain
  `Not applicable` with a physical-support limitation. These are correct
  conservative states, not scientific approval.
