# SAXS Strain Herman Orientation Table

## Goal

Complete the existing in-situ tensile SAXS path from preprocessed 2D sector
data to per-frame `f_Herman` values in the result table, while keeping the
value explicitly unavailable for 1D or missing-sector frames.

## Non-goals

- Do not rewrite the Herman algorithm, pyFAI integration, detector geometry,
  beam-center inference, or orientation thresholds.
- Do not convert the Herman factor into a percentage or invent a value from
  `orientation_evidence`.
- Do not move scientific computation into GUI event handlers.
- Do not change generic 1D metric review semantics, publication roles, AI
  behavior, raw regression datasets, or external data.
- Do not push, merge, deploy, or send external messages.

## Affected boundaries

- Core transport and strain parameters: `polynexus/core/saxs.py`.
- Existing strain calculation contract: `polynexus/core/saxs_engine/saxs_strain.py`
  (expected to remain behaviorally unchanged).
- Existing GUI presentation contract: `polynexus/gui/result_table_templates.py`
  and `polynexus/gui/saxs_results_table_service.py` (expected to remain
  production-unchanged).
- Regression tests: `tests/test_saxs_batch_parameters.py` and
  `tests/test_saxs_results_table_service.py`.
- Durable design and implementation records listed in the changed-file
  allowlist below.

## Acceptance criteria

- [x] Directory strain loading retains one sector-data entry per loaded frame,
  using `None` when the source is 1D or no sector map is available.
- [x] Strain analysis receives the retained list through its existing optional
  `sector_data_list` parameter.
- [x] Per-frame `_batch_params` contains `f_Herman` from the corresponding
  `StrainPointResult`, or None when unavailable.
- [x] Existing series aggregation emits finite `f_Herman_mean`, span, and range
  only when finite factor values exist.
- [x] Structured SAXS results display the existing Herman column and numeric
  cells for supplied values without GUI-side recalculation.
- [x] 1D-only and mixed 1D/2D cases preserve unavailable cells and do not use
  zero as a fallback.
- [x] Existing SAXS regression tests remain green.
- [x] `python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-strain-herman-table.md --changed --types` passes.
- [x] One atomic checkpoint is created using `scripts/auto_commit.py` with the
  explicit allowlist below.

## Implementation plan

1. Add failing core tests for sector-data retention/forwarding and per-frame
   parameter publication.
2. Run the focused tests and confirm the expected RED failures.
3. Add the minimal `_sector_data_list` lifecycle and pass it to the existing
   strain analyzer.
4. Add the minimal per-frame `f_Herman` row field, preserving missing values.
5. Add/adjust the structured-table assertion and run the GREEN focused tests.
6. Run the full SAXS matrix and the structured verifier.
7. Review the cumulative diff, update memory only with durable facts, and create
   the atomic checkpoint with the allowlist.

## Verification

```powershell
python -m pytest tests/test_saxs_batch_parameters.py tests/test_saxs_results_table_service.py -q
python -m pytest (Get-ChildItem tests/test_saxs_*.py | ForEach-Object { $_.FullName }) -q
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-strain-herman-table.md --changed --types
```

## Verification evidence (2026-07-27)

- TDD RED: the transport regressions failed because `SAXSEngine` had no
  `_sector_data_list`, the strain analyzer received `None`, and the strain row
  did not contain `f_Herman`; the table contract test passed after preserving
  its existing em-dash behavior.
- Focused transport/strain/table/2D matrix: `79 passed`.
- Complete SAXS matrix: `341 passed, 4 warnings`; warnings are the existing
  Arial CJK glyph warnings from SAXS figure layout.
- Structured verifier with `PYTEST_ADDOPTS='-o addopts= --basetemp=C:\Temp\PolyNexus_saxs_herman_verify_final'`:
  task card, memory, Ruff, compile/type baseline, quality gate `282`,
  preprocessing gate `106`, and whitespace checks passed.
- The first verifier attempt without an external basetemp encountered the
  pre-existing locked repository `.pytest_tmp` and produced setup errors;
  that directory was not modified or deleted.
- Direct `analyze_strain()` and directory-load transport are covered by the
  focused regressions.

## Known limitations

This task exposes only Herman factors calculated from sector data already
produced by the existing preprocessing path. It does not establish raw
detector geometry quality, calibrate orientation uncertainty, or authorize
scientific publication conclusions.

## Pre-existing workspace changes

The worktree already contains Origin/editor changes, SAXS AI rerun-safety
changes, memory edits, temporary pytest directories, and other untracked
diagnostics. They are outside this task and must remain untouched and outside
the atomic checkpoint.

## Changed-file allowlist

- `polynexus/core/saxs.py`
- `tests/test_saxs_batch_parameters.py`
- `tests/test_saxs_results_table_service.py`
- `docs/agent/tasks/2026-07-27-saxs-strain-herman-table.md`
- `docs/superpowers/specs/2026-07-27-saxs-strain-herman-table-design.md`
- `docs/superpowers/plans/2026-07-27-saxs-strain-herman-table.md`

The durable memory files currently contain a separate parallel full-software
release-audit diff. They are intentionally excluded from this checkpoint to
avoid mixing work; the Herman evidence and limitation are recorded in this
task card and the parallel memory update remains untouched.
