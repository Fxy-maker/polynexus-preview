# SAXS Results Frame and Tracking Row Separation Design

**Date:** 2026-08-07
**Status:** Approved for implementation
**Approval source:** User confirmation that result-row counts must follow the
actual number of analyzed frames rather than a fixed five-row limit

## Goal

Keep the SAXS strain results table aligned one-to-one with the analyzed input
frames while retaining orientation-tracking evidence without presenting its
observations as additional sample frames.

## Observed failure

The SAXS presentation adapter currently builds its detail and diagnostic table
rows from the frame-level `_batch_data`, appends a batch-summary row, and then
appends every flattened `_orientation_tracking_rows` observation. A five-frame
strain sequence can therefore appear as many repeated strain sequences. The
tracking observations carry strain and orientation fields but do not carry
frame structure fields such as `file`, `L_nm`, or `q_peak_total_nm1`, so the
mixed table displays misleading rows filled with unavailable markers.

The analysis payload itself is correct: the EDF 8 replay contains five frame
rows with finite tracked long periods and total-profile peak positions. The
defect is confined to the GUI presentation projection.

## Chosen approach

Build primary, detail, and diagnostic tabular rows only from `_batch_data` plus
the existing single batch-summary row. Do not append flattened orientation
track observations to those row collections.

Keep `orientation_tracking_evidence` and `_orientation_tracking_rows` in the
detached result payload. The nested tracking evidence remains available to the
existing diagnostic serialization and to data export/history consumers; only
the misleading projection into the frame table is removed.

Row counts are dynamic. A sequence with N analyzed frame rows displays N rows
in the primary table, whether N is 1, 5, 20, or another valid count. Separate
sample runs retain their own frame counts.

## Data and architecture boundary

- Analysis engines and scientific tracking algorithms do not change.
- `SAXSAnalyzer.get_parameters()` continues transporting frame rows and
  orientation-tracking evidence without mutation.
- `build_saxs_results_presentation()` owns the presentation-only separation.
- No tensile-axis, orientation, peak-selection, or reliability semantics are
  inferred or altered.

## Acceptance criteria

1. A SAXS strain payload with N `_batch_data` mappings produces exactly N
   primary frame rows.
2. Detail and diagnostic sections contain the N frame rows and at most the one
   existing batch-summary row; orientation observations do not create rows.
3. Repeated condition values from `_orientation_tracking_rows` cannot appear
   as duplicate frame rows.
4. `orientation_tracking_evidence` remains present and serializable in the
   diagnostic section and the input payload remains unchanged.
5. Existing SAXS result-table behavior for static and temperature modes remains
   unchanged.

## Non-goals

- Do not add a dedicated orientation-track table in this repair.
- Do not aggregate multiple orientation tracks into a new scientific metric.
- Do not alter file loading, sample grouping, feature tracking, or export
  contracts.

## Verification

Add a focused regression test that supplies five frame rows and repeated
tracking observations, verifies the dynamic frame count and absence of
tracking-only rows, and verifies preservation of detached tracking evidence.
Run the focused SAXS result-table tests followed by the repository changed-file
verification command.

## Spec self-review

- The design contains no placeholder or unresolved scientific choice.
- The change is restricted to the GUI presentation boundary where the defect
  was reproduced.
- Dynamic row-count semantics and evidence preservation are explicit.
