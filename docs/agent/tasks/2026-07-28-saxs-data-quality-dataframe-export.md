# Task: SAXS data-quality report in DataFrame and CSV exports

**Status:** checkpointed at `b0c63d7`

## Goal

Expose the existing per-frame `DataQualityReport` in temperature/strain
DataFrames and static parameter CSV exports so dirty q/I inputs remain
traceable outside nested JSON evidence and the GUI.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_output_helpers.py`: shared flat projection.
- `polynexus/core/saxs_engine/saxs_temperature.py`: temperature rows.
- `polynexus/core/saxs_engine/saxs_strain.py`: strain rows.
- `tests/test_saxs_data_quality_dataframe.py`: focused regressions.

## Non-goals

- No change to `build_data_quality_report`, cleaning, sorting, fitting, or
  physical thresholds.
- No new quality level, reason code, rescue behavior, AI behavior, or figure
  publication role.
- No inference from counts; the projection copies existing report fields only.
- No changes to real datasets, generated outputs, or parallel GUI/scratch files.

## Acceptance criteria

- [x] Temperature and strain DataFrames expose stable data-quality level,
  reasons, actions, counts, flags, and source/reference fields per row.
- [x] Static `_result_to_params_dict` and `export_parameters_csv` expose the
  same flat fields without replacing the nested report.
- [x] Missing reports preserve row count and source order while producing empty
  fields; no frame is invented, copied, interpolated, or dropped.
- [x] Reason/action ordering and field names are deterministic; enum levels and
  boolean flags retain their emitted values.
- [x] Existing DataFrame/CSV columns, physical gates, and metric semantics are
  unchanged.
- [x] Focused, exact SAXS, structured verifier, diff, and explicit checkpoint
  evidence are recorded.

## Implementation plan

1. Add RED tests for populated and missing temperature/strain rows and static
   parameter projection.
2. Add `_data_quality_csv_fields(report)` beside the existing detector flat
   projection. It returns fixed keys and copies only a mapping's values.
3. Merge the helper into the three existing export consumers.
4. Run focused/SAXS/task verification, update durable memory, and checkpoint
   only the explicit allowlist below.

## Verification

```powershell
python -m pytest -q tests/test_saxs_data_quality_dataframe.py tests/test_saxs_output_helpers.py tests/test_saxs_mode_evidence_propagation.py --basetemp C:\Temp\PolyNexus_saxs_data_quality_dataframe
$saxsTests = Get-ChildItem -Path tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests --basetemp C:\Temp\PolyNexus_saxs_data_quality_saxs_matrix
$env:PYTEST_ADDOPTS = '--basetemp=C:\Temp\PolyNexus_saxs_data_quality_verify'; python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-data-quality-dataframe-export.md --changed --types; $exit = $LASTEXITCODE; Remove-Item Env:PYTEST_ADDOPTS -ErrorAction SilentlyContinue; exit $exit
git diff --check
```

## Recorded evidence

- TDD RED: `3 failed, 18 passed`; failures were the expected absent
  `Data_quality_*` projections.
- GREEN and focused consumer matrix: `21 passed in 0.25s`; Ruff and compile
  both exited `0`.
- Exact SAXS matrix, split across four external basetemps: `383 passed, 6
  warnings` (`106 + 92 + 100 + 85`). Warnings are existing Arial glyph and
  EDF geometry-header warnings.
- Structured verifier exited `0` with quality `283 passed`, preprocessing `106
  passed`, task/memory, Ruff, compile/type, and whitespace checks.
- The first verifier invocation found only a task-card heading mismatch
  (`Verification commands` versus required `Verification`); the corrected
  fresh rerun above is authoritative.
- Explicit allowlist checkpoint: `b0c63d7` (created by
  `scripts/auto_commit.py`; no push).

## Scientific limitation

The flat fields are an audit projection of the existing report. They do not
decide whether a curve is scientifically usable, do not promote a metric, and
do not authorize rescue or publication.

## Explicit changed-file allowlist

- `docs/agent/tasks/2026-07-28-saxs-data-quality-dataframe-export.md`
- `docs/superpowers/specs/2026-07-28-saxs-data-quality-dataframe-export-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-data-quality-dataframe-export.md`
- `polynexus/core/saxs_engine/saxs_output_helpers.py`
- `polynexus/core/saxs_engine/saxs_temperature.py`
- `polynexus/core/saxs_engine/saxs_strain.py`
- `tests/test_saxs_data_quality_dataframe.py`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`
