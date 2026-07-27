# SAXS Strain Herman Orientation Table Design

**Date:** 2026-07-27
**Status:** Implementation basis completed locally; human scientific review remains open
**Goal:** Complete the existing data path that exposes the calculated Herman orientation factor for each in-situ tensile SAXS frame while preserving an explicit unavailable state when no 2D sector evidence exists.

## Context

The strain result-table template already declares `f_Herman` as the per-frame
field and `f_Herman_mean` as the series hero metric. The strain engine already
accepts an optional `sector_data_list` and computes `StrainPointResult.f_herman`
when a sector map is supplied. The missing path is in the SAXS wrapper: it
does not retain the per-frame `sector_data` returned by preprocessing, does not
pass that list into `analyze_strain_series`, and does not copy the resulting
per-frame factor into `_batch_params`.

## Selected approach

Keep the scientific calculation in the existing strain engine and complete the
wrapper transport boundary. The GUI continues to consume the established
`f_Herman` table field; it does not recalculate orientation or interpret
`orientation_evidence` as a numeric factor.

The data flow becomes:

```text
preprocess_pipeline(frame)
    -> sector_data (or None for 1D input)
    -> SAXS engine _sector_data_list
    -> analyze_strain_series(sector_data_list=...)
    -> StrainPointResult.f_herman
    -> _batch_params["f_Herman"]
    -> existing SAXS strain result table
```

The direct `SAXSEngine.analyze_strain()` entry point uses the same retained
list, so GUI directory analysis and direct programmatic strain analysis have
the same behavior.

## Alternatives considered

1. **Recommended: complete core transport and verify the existing GUI table.**
   This is the smallest change that preserves the current algorithm and keeps
   scientific behavior in core. It requires no GUI production-code change.
2. **Recompute Herman values in the GUI from stored images.** Rejected because
   it duplicates scientific logic, makes GUI behavior dependent on raw-detector
   availability, and violates the core/service boundary.
3. **Derive a numeric factor from `orientation_evidence`.** Rejected because
   evidence describes applicability and provenance; it is not a replacement for
   the existing sector-integrated Herman calculation.

## Data and scientific semantics

- `f_Herman` is the existing Herman orientation factor, not an orientation
  percentage. Its existing convention remains unchanged: `1` is alignment
  along the reference direction, `0` is random orientation, and `-0.5` is
  perpendicular orientation.
- A 2D frame with valid sector data may produce a numeric `f_Herman`.
- A 1D frame, an absent sector map, or a failed sector calculation leaves the
  factor as NaN/None and the table renders an em dash. No zero is substituted.
- Mixed 1D/2D sequences preserve per-frame missingness. The series mean and
  range use only finite calculated factors, as the existing aggregate code
  already does.
- Existing `orientation_evidence` transport remains unchanged and remains a
  diagnostic/provenance channel separate from the numeric table field.

## Boundaries and files

- Modify `polynexus/core/saxs.py` to retain sector data, pass it to the strain
  analyzer, and publish each frame's factor into `_batch_params`.
- Keep `polynexus/core/saxs_engine/saxs_strain.py` unchanged unless a focused
  compatibility fix is required; its optional input contract already exists.
- Keep `polynexus/gui/result_table_templates.py` and
  `polynexus/gui/saxs_results_table_service.py` unchanged in production; add
  presentation assertions in `tests/test_saxs_results_table_service.py`.
- Add core regression coverage in `tests/test_saxs_batch_parameters.py` or a
  focused new test module if the existing fixture boundary cannot express the
  transport without broad setup.
- Record the task and implementation plan under `docs/agent/tasks/` and
  `docs/superpowers/plans/`.

## Error handling

- Missing `sector_data` is normal for 1D input and must not fail the strain
  analysis.
- A malformed individual sector entry is treated as unavailable for that frame;
  other frames continue through the existing strain analysis path.
- Legacy 1D fields, frame order, strain-axis metadata, and existing evidence
  payloads remain unchanged.

## Acceptance criteria

1. A strain series with valid sector maps produces finite per-frame
   `f_Herman` values in the core result payload and in the result table.
2. The series payload exposes `f_Herman_mean`, `f_Herman_span`, and
   `f_Herman_range` when at least one finite frame value exists.
3. A 1D-only strain series keeps the Herman cells and summary absent/unavailable
   rather than displaying zero or a guessed value.
4. A mixed series retains em dashes only on frames without valid sector data,
   while finite frames remain numeric.
5. Existing table localization and column order remain unchanged.
6. Focused tests, the SAXS test matrix, and the structured repository verifier
   pass; the task creates one atomic checkpoint with an explicit file allowlist.

## Verification commands

```powershell
python -m pytest tests/test_saxs_batch_parameters.py tests/test_saxs_results_table_service.py -q
python -m pytest (Get-ChildItem tests/test_saxs_*.py | ForEach-Object { $_.FullName }) -q
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-strain-herman-table.md --changed --types
```
