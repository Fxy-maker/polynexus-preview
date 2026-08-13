---
task_id: 2026-08-13-writing-metric-provenance
kind: scientific
status: completed
date: 2026-08-13
title: Project writing metric provenance and evidence relations
---

# Writing Metric Provenance and Evidence Relations

## Goal

Add a machine-readable, ARS-facing numerical evidence projection to each
project package.  Every projected value must carry its value, unit, method,
source evidence/run/raw hash, status, review boundary, and package-relative
figure/table links.

## Non-goals

- Do not change a DSC, IR, SAXS, or WAXS calculation.
- Do not calibrate FTIR crystallinity, repair SAXS background, or improve WAXS
  peak support in this task.
- Do not turn review-required observations into publication approval.
- Do not draft Results/Discussion text or alter raw PA6 sources.

## Affected boundaries

- `polynexus/core/project_workflow/`: metric projection and immutable package
  materialization.
- Package JSON/Markdown writing handoff, focused tests, acceptance, and memory.

## Scientific projection rules

1. DSC isothermal segment values (`T_iso_C`, `DHc_iso_Jg`, `Avrami_n`,
   `Avrami_k`, `Avrami_R2`, `t_half_min`) are Results candidates only when
   their existing provider segment is finite.  They retain the isothermal
   Avrami-fit method, segment source, and review status.
2. FTIR peak locations and FWHM values use `cm^-1`; assigned-peak count uses
   `count`.  An `Xc_pct` with `Xc_calibration_status=uncalibrated_index` is
   emitted as an uncalibrated band index with unit `index`, marked
   `diagnostic_only`, and explicitly prohibited as an absolute crystallinity.
3. SAXS metric-evidence records retain their provider-provided unit, method
   source, applicability, and reason codes.  A metric whose `applicable` flag
   is false is `diagnostic_only`, even when it has a finite number.
4. WAXS `Xc_pct` and `D_Scherrer_nm` use the provider method and support
   evidence.  Failed physical support or low size reliability makes the record
   `diagnostic_only`; it remains visible for audit rather than disappearing.
5. No value is a numeric writing record if its unit or method cannot be
   resolved by a documented rule.  It is omitted with an item-level omission
   reason instead of receiving a guessed unit.

## Acceptance criteria

- [x] A package writes versioned `citation-metrics.json` and declares it in
  `manifest.json`.
- [x] Each metric has a stable ID, technique, value, unit, method, evidence ID,
  run ID, raw source hash, status, writing eligibility, and figure/table links.
- [x] DSC/FTIR/SAXS/WAXS synthetic evidence produces the correct unit/method
  projection and eligibility boundary.
- [x] FTIR uncalibrated `Xc_pct` is never emitted as a percent crystallinity
  Results value.
- [x] SAXS/WAXS unsupported values remain diagnostic-only with existing
  reasons, not omitted or promoted.
- [x] `writing-evidence.json` references its metric IDs, and `writing-input.md`
  gives ARS the path and the count by eligibility.
- [x] External PA6 four-technique replay proves the package contains all four
  techniques' records and preserves their review boundaries.

## Implementation plan

1. Define JSON-safe metric records and deterministic extraction for each
   technique using existing provider evidence only.
2. Attach package-relative figure/table links and add the package manifest and
   writing handoff projections.
3. Add focused regression tests for units, methods, eligibility, omission, and
   source provenance.
4. Run the bounded PA6 replay, record acceptance, update durable memory, run
   structured verification, and checkpoint an explicit allowlist.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_project_writing_metrics.py tests/test_project_workflow_package.py tests/test_ai_native_project_entrypoint.py
python scripts/verify.py --task docs/agent/tasks/2026-08-13-writing-metric-provenance.md --changed --types
git diff --check
```
