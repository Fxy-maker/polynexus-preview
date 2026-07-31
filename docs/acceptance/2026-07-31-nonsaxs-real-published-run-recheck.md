---
kind: acceptance
status: recorded
date: 2026-07-31
title: Non-SAXS real published-run lifecycle recheck
task: docs/agent/tasks/2026-07-31-nonsaxs-real-published-run-recheck.md
---

# Acceptance record

## Scope

This record covers the existing real-fixture shared lifecycle for non-SAXS
cases selected by `tests/test_real_published_run_walkthrough.py -k "not saxs"`.
The test is expected to exercise DSC standard/isothermal/non-isothermal, WAXS
static/temperature/strain, IR standard/temperature-2D, and NMR liquid/solid
H/C routes when their fixtures are present.

## Evidence rule

Only a complete pytest summary together with exit code `0` is recorded as a
pass. Process termination, partial output, timeout, setup failure, or missing
summary is recorded as incomplete.

## Scientific boundary

This verifies software transport and lifecycle persistence through
Manifest/Gallery, Editor, Export, and History. It does not establish vendor
calibration, IR mapping coordinate semantics, NMR assignment truth, Joint
conflict precedence, scientific correctness, restarted-GUI acceptance, or
final publication approval. Existing diagnostic-only, SI-only,
validation-required, and assignment-limited roles remain unchanged.

## Observed results

- The first D: run returned `11 passed, 1 failed, 3 deselected, 11 warnings`;
  WAXS strain stopped at TIFF export because D: had no free space.
- A C: rerun reached all 12 `PASSED` cases but pytest could not write the
  repository `.pytest_cache` on full D:, so it was not counted as a pass.
- After the explicitly authorized storage apply and use of
  `-p no:cacheprovider`, the complete C: rerun returned:
  `12 passed, 3 deselected, 11 warnings in 291.31s`, exit code `0`.

This proves the non-SAXS real-fixture lifecycle on the current HEAD through
Manifest/Gallery, Editor working and published revisions, Export provenance,
and History restore. It does not close scientific, vendor-semantic,
restarted-GUI, or final release gates.

## Storage cleanup evidence

The storage tool was run with the user's explicit prior `--apply` authorization
after reviewing its JSON inventory and confirming no active Python/pytest
process. It removed eligible managed/legacy test artifacts. The command exited
`1` only because permission-locked historical directories were skipped by the
tool's safety checks. Afterward D: had approximately `21.16 GB` free and the
report contained `50` artifacts, `1,368,544,565` bytes, and zero eligible
bytes. No manual deletion was performed.

## Verification commands

```powershell
python -m pytest -q tests/test_real_published_run_walkthrough.py -k "not saxs" -vv --basetemp=D:\PolyNexus-test-runs\nonsaxs-real-published-20260731
python scripts/verify.py --task docs/agent/tasks/2026-07-31-nonsaxs-real-published-run-recheck.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24 --json
git diff --check
```

The final lifecycle command used:

```powershell
python -m pytest -p no:cacheprovider -q tests/test_real_published_run_walkthrough.py -k "not saxs" -vv --basetemp=C:\PolyNexus-test-runs\nonsaxs-real-published-20260731-c-after-clean
```

## Structured verification

- `python scripts/verify.py --task docs/agent/tasks/2026-07-31-nonsaxs-real-published-run-recheck.md --changed --types` exited `0`; quality `297 passed`, preprocessing `106 passed`, task/memory, Ruff, compile, type baseline, and whitespace checks passed.
- `python scripts/boundary_audit.py --root D:\PolyNexus --json` exited `0`.
- `git diff --check` exited `0`.

## Workspace boundary

No production files, real fixtures, generated outputs, or parallel memory files
are included in the checkpoint. The authorized storage cleanup was executed by
the repository tool; no manual deletion or safety-rule bypass was used.
