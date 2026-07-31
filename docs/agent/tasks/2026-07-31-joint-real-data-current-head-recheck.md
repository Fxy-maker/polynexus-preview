---
task_id: 2026-07-31-joint-real-data-current-head-recheck
kind: scientific-verification
status: completed
date: 2026-07-31
title: Recheck Joint real-data transport at current HEAD
---

# Joint real-data current-HEAD recheck

## Goal

Re-run the existing Joint real-data lifecycle contract for DSC, SAXS, and WAXS
source runs and verify transport into SampleDB, the Joint report, Figure
Manifest, and active Gallery entries.

## Non-goals

- No production code, numeric formula, conflict tolerance, evidence weight, or
  publication-role change.
- No automatic conflict precedence or scientific Joint conclusion.
- No edits to real fixtures, source data, memory files, or SAXS parallel work.

## Affected boundaries

- `tests/test_joint_real_data_lifecycle.py` existing real-data contract.
- SampleDB, Joint report, Figure Manifest, and active Gallery provenance
  consumers exercised by that contract.
- This task's three documentation files only; no production implementation
  boundary changes.

## Implementation plan

1. Run the existing real-data lifecycle test with a C: basetemp and disabled
   pytest cache so the full-D workspace is not used for temporary output.
2. Record the complete pytest summary and exit code, including any fixture skip.
3. Run task verifier, boundary audit, and diff check, then checkpoint only this
   task's three documents.

## Acceptance criteria

- [x] The Joint real-data contract returns a complete pytest summary and exit
      code `0`.
- [x] Source-run provenance reaches SampleDB, Joint report, Figure Manifest,
      and active Gallery entries.
- [x] Scientific conflict interpretation and final release remain explicitly
      open.
- [x] Verifier, boundary audit, and diff check have exact outcomes.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_joint_real_data_lifecycle.py -vv --basetemp=C:\PolyNexus-test-runs\joint-real-data-current-head-20260731
python scripts/verify.py --task docs/agent/tasks/2026-07-31-joint-real-data-current-head-recheck.md --changed --types
python scripts/boundary_audit.py --root D:\PolyNexus --json
git diff --check
```

## Explicit changed-file allowlist

- `docs/superpowers/plans/2026-07-31-joint-real-data-current-head-recheck.md`
- `docs/agent/tasks/2026-07-31-joint-real-data-current-head-recheck.md`
- `docs/acceptance/2026-07-31-joint-real-data-current-head-recheck.md`

Parallel SAXS source, tests, memory, and temporary directories remain outside
this allowlist.

## Evidence

- `python -m pytest -p no:cacheprovider -q tests/test_joint_real_data_lifecycle.py -vv --basetemp=C:\PolyNexus-test-runs\joint-real-data-current-head-20260731` returned `1 passed in 15.55s`, exit `0`.
- The test covers real DSC/SAXS/WAXS engine outputs, SampleDB persistence,
  Joint report publication, Figure Manifest, and active Gallery run identity.
- This is transport/provenance evidence only. Scientific conflict precedence,
  unresolved conflict interpretation, and final release remain open.
