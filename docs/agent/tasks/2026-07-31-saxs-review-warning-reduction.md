# Task: SAXS review warning reduction and strain-axis provenance

**Status:** completed

## Goal

Reduce misleading and duplicated SAXS review warnings while preserving
fail-closed scientific gates and using the confirmed filename strain values for
the `610` four-frame series.

## Scope

- Parse `610-000-S_0_00000.edf`-style filename strain values before the enclosing
  directory code, but only when `SAXSConfig.experiment_type == "strain"`.
- Prevent strain/temperature-specific default patterns from being used by an
  unrelated static route.
- Classify declared background-floor pixels and shape-matched configured masks
  as expected exclusions; retain their counts and retain unexpected
  nonpositive-pixel diagnostics.
- Represent complete EDF geometry metadata as structurally complete without
  claiming physical calibration approval.
- Deduplicate repeated detector provenance audit text per presentation field.

## Affected boundaries

`polynexus/core/saxs_engine/config.py` and `io.py` recover the experiment
condition; `preprocess.py` and `saxs_quality_contracts.py` classify raw EDF
quality evidence; `saxs_results_table_service.py` renders detector audit
summaries; focused SAXS tests cover each boundary.

## Non-goals

- Do not infer strain from EDF pixels, pressure, timestamps, or an unconfirmed
  filename.
- Do not treat the public Pilatus PONI file as EIGER geometry.
- Do not promote raw EDF metadata to publication acceptance or scientific
  calibration approval.
- Do not change q conversion, integration formulas, background subtraction,
  or the actual detector mask pixels.
- Do not edit real datasets or generated output directories.

## Acceptance criteria

- [x] `recover_condition_axis()` returns `5.0` and source key
  `strain_dash_S_suffix` for `610-005-S_0_00000.edf` in strain mode.
- [x] The same path is unresolved for static mode unless an explicit static
  condition source is provided.
- [x] A complete EDF header reports geometry provenance as structurally complete,
  while the audit text still describes it as structural evidence rather than
  physical calibration approval.
- [x] A frame whose nonpositive pixels are all the declared background floor and
  whose configured mask shape matches is not downgraded solely for those
  expected exclusions; counts remain available in the report.
- [x] Unexpected nonpositive pixels remain a diagnostic reason.
- [x] A four-frame detector audit is rendered once per risk/next field rather than
  repeated once per frame and then repeated again in the next-step text.
- [x] The four-frame regression covers `000`, `005`, `060`, and `200`.

## Implementation plan

1. Add RED tests for strain filename precedence, static pattern scoping,
   expected detector exclusions, structural metadata statuses, and audit
   deduplication.
2. Implement the smallest condition parser, raw report, provenance status, and
   presentation changes needed by those tests.
3. Run focused SAXS tests, the structured verifier, and a real four-frame EDF
   replay; record exact outcomes below.

## Verification

```powershell
python -m pytest -q tests/test_saxs_condition_recovery.py tests/test_saxs_edf_metadata_quality.py tests/test_saxs_raw_detector_quality_transport.py tests/test_saxs_workbench_detector_provenance_audit.py
python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-review-warning-reduction.md --changed --types
git diff --check
```

## Changed-file allowlist

- `docs/agent/tasks/2026-07-31-saxs-review-warning-reduction.md`
- `docs/superpowers/specs/2026-07-31-saxs-review-warning-reduction-design.md`
- `docs/superpowers/plans/2026-07-31-saxs-review-warning-reduction.md`
- `polynexus/core/saxs_engine/config.py`
- `polynexus/core/saxs_engine/io.py`
- `polynexus/core/saxs_engine/preprocess.py`
- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `polynexus/gui/saxs_results_table_service.py`
- `tests/test_saxs_condition_recovery.py`
- `tests/test_saxs_edf_metadata_quality.py`
- `tests/test_saxs_workbench_detector_provenance_audit.py`

## Verification evidence

- TDD RED: the initial focused run reported `15 passed, 4 failed`; failures
  covered the intended missing provenance statuses, unexpected nonpositive
  count, and audit deduplication behavior. The strain precedence and static
  isolation regressions already passed against the shared implementation.
- Focused SAXS matrix: `28 passed, 2 warnings` for condition recovery, EDF
  metadata quality, raw-detector transport, and Workbench detector audit.
- Structured verifier: exit `0`; task card and memory checks passed, Ruff and
  compile passed, no changed type baseline was required, quality gate was
  `297 passed`, preprocessing gate was `106 passed`, and whitespace passed.
- `git diff --check`: passed after the lint-only import/name cleanup in
  `polynexus/core/saxs_engine/io.py`.
- Test-storage report and clean dry-run: `68` artifacts, `5,089,755,229`
  bytes total, `17` emergency-eligible artifacts (`2,948,589,610` bytes),
  `0` removed. No `--apply` was used; no test directory was deleted or moved.
- Full SAXS and full/boundary release verification were not rerun in this
  atomic task and are not claimed as passing here.
