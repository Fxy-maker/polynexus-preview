# Joint Selection and Result Semantics

## Goal

Make Joint comparisons explicit and source-auditable: the user selects the
batches, Joint exposes the exact runs/files being compared, missing inputs are
`SKIP` rather than conflicts, and no automatic consensus Xc is produced.

## Non-goals

- Do not change DSC, WAXS, SAXS, or NMR technique-specific Xc formulas.
- Do not infer sample identity from filenames.
- Do not assign or calibrate NMR solid-C peaks.
- Do not add a technique-priority rule or publication approval.

## Boundaries

- Core: `polynexus/core/joint/dataset.py` and `validation.py` keep one row per
  explicit batch, retain source provenance, and distinguish `DIFF`, `SKIP`, and
  `NOT_COMPARABLE`.
- GUI: `polynexus/gui/widgets/joint_analysis_hub.py` does not auto-check rows on
  refresh and exposes selected-source preflight data.
- Main-window integration: `polynexus/gui/main_window_joint_diagnostics_mixin.py`
  persists the preflight fields without changing the figure lifecycle.
- Real fixture: `tests/test_joint_real_data_lifecycle.py` selects the PA6 SAXS
  file under `测试数据/saxs/普通小角` rather than PAD8 `8-000-s...edf`.
- Tests: focused Joint dataset, validation, GUI, and real-data lifecycle tests.

## Affected boundaries

- Joint core dataset assembly, provenance projection, validation status, and
  conclusion issue counting.
- Joint selector widget and main-window artifact export.
- Joint focused tests, the PA6 real-data fixture resolver, and acceptance
  evidence.

## Implementation plan

1. Add RED tests for explicit selection, source preflight, status separation,
   assignment-limited NMR Xc exclusion, condition incompatibility, and the
   corrected PA6 SAXS fixture.
2. Implement the smallest core and GUI changes that satisfy those contracts,
   preserving batch boundaries and existing figure publication behavior.
3. Run focused Joint regressions, the structured verifier, boundary audit, and
   diff checks; record exact results and create one explicit allowlist
   checkpoint.

## Acceptance criteria

- [x] Refresh leaves every Joint row unchecked; explicit checkbox or Sample
   Browser selection is required before report generation.
- [x] A Joint row never combines runs from different batches.
- [x] Every selected source includes sample/batch, technique/submodule, run ID,
   created time, input path when available, condition values, and evidence
   status/reasons.
- [x] Missing inputs/method outputs are `SKIP` and excluded from conflict counts.
- [x] Non-comparable source conditions remain visible and do not receive automatic
   precedence.
- [x] No solid-C `assignment_limited` Xc enters Joint Xc comparison.
- [x] The real Joint fixture uses a PA6 SAXS source and all focused regressions
   pass.

## Acceptance checklist

- [x] Refresh requires explicit batch selection.
- [x] Selected source provenance is report- and export-visible.
- [x] `SKIP`, `DIFF`, and `NOT_COMPARABLE` remain distinct.
- [x] Assignment-limited solid-C Xc is excluded from Joint comparison.
- [x] Focused Joint regressions pass with exit code `0`.

## Verification

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-08-01-joint-selection-and-semantics.md --changed --types
python scripts/boundary_audit.py --root D:\PolyNexus --json
git diff --check
```

## Explicit allowlist

The implementation checkpoint must list only the changed core, GUI, test,
task, and acceptance files actually modified by this task. Existing user
changes, real datasets, and temporary test directories are excluded.

## Implementation Status

- [x] Refresh leaves all Joint candidate rows unchecked; recommended selection
  remains an explicit user action.
- [x] Selected source runs expose detached batch, technique, submodule, run,
  path, condition, and evidence fields in the report and CSV export.
- [x] Validation distinguishes `DIFF`, `SKIP`, and `NOT_COMPARABLE`; skipped
  checks do not count as conflicts.
- [x] Assignment-limited or uncalibrated solid-C Xc is retained as evidence but
  excluded from Joint Xc comparison.
- [x] The real PA6 fixture selects the static SAXS source under
  `测试数据/saxs/普通小角` and preserves its diagnostic validation result.

Focused verification: `33 passed in 31.07s`, exit code `0`.

This task does not assign NMR peaks, calibrate ppm, choose a technique winner,
or authorize publication. Existing unrelated workspace changes were left
untouched.
