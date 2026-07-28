# Task: SAXS strain-axis fail-closed boundaries

**Status:** checkpointed locally after verification

## Goal

Make strain-series analysis survive malformed, non-finite, and empty strain
axes while preserving frame positions and emitting the existing diagnostic
condition-axis evidence.

## Non-goals

- Do not interpolate, infer, reorder, or fabricate strain values.
- Do not change SAXS physical metrics, phase thresholds, quality thresholds,
  rescue, AI, publication roles, or figure semantics.
- Do not delete frames because their strain label is invalid; retain their
  profile-level analysis and mark the axis evidence diagnostic.
- Do not modify temperature behavior or concurrent GUI/Joint files.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_strain.py`: input coercion, empty reference
  handling, condition-axis evidence, and phase-boundary bookkeeping.
- `tests/test_saxs_strain_axis_fail_closed.py`: malformed and empty-axis
  regressions.

## Acceptance criteria

- [ ] Numeric strings remain numeric; malformed and non-finite strain values
  become `NaN` in the retained axis without raising.
- [ ] All input frames remain represented in `strain_points`, in original
  order, and invalid axis positions are reported through the existing
  `condition_axis` evidence as diagnostic.
- [ ] Invalid axis positions do not create `NaN` phase-boundary values.
- [ ] An empty strain series returns an empty `StrainSeriesResult` with
  `Unusable` series metric evidence and `series_no_frames`, without indexing a
  missing reference frame.
- [ ] Existing clean and dirty profile behavior remains green.
- [ ] Focused tests, exact SAXS matrix, structured verifier, diff check, and
  test-storage dry-run evidence are recorded before checkpointing.

## Implementation plan

1. Add RED tests for malformed/non-finite axis values and an empty series.
2. Normalize each strain with a local finite-float coercion helper, retain
   invalid positions as `NaN`, and add the existing series condition-axis
   fields to strain metric evidence.
3. Avoid empty-reference indexing and skip invalid axis values when recording
   phase boundaries; leave per-frame profile analysis and existing phase
   classification unchanged.
4. Run the focused strain matrix, full SAXS matrix, task verifier, diff check,
   and storage report, then create one explicit allowlist checkpoint.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_strain_axis_red'
python -m pytest -q tests/test_saxs_strain_axis_fail_closed.py

$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_strain_axis_focus'
python -m pytest -q tests/test_saxs_strain_axis_fail_closed.py tests/test_saxs_strain_dirty_frame_postprocessing.py tests/test_saxs_1d_quality_provenance.py tests/test_saxs_2d_evidence_propagation.py

$saxsTests = Get-ChildItem tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests

python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-strain-axis-fail-closed.md --changed --types
git diff --check
python scripts/test_storage.py report --json
```

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/saxs_strain.py`
- `tests/test_saxs_strain_axis_fail_closed.py`
- `docs/agent/tasks/2026-07-28-saxs-strain-axis-fail-closed.md`
- `docs/superpowers/specs/2026-07-28-saxs-strain-axis-fail-closed-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-strain-axis-fail-closed.md`

The concurrently modified `docs/agent/memory/active-work.md`,
`docs/agent/memory/current-state.md`, Workspace files, generated captures,
scratch directories, and `.superpowers/` are outside this checkpoint.

## Verification evidence before checkpoint

- RED: `2 failed in 0.85s`; malformed strain input raised the existing
  `ValueError`, and an empty series raised the existing `IndexError`.
- Focused strain/2D/quality matrix: `22 passed in 0.65s`.
- Downstream strain consumer matrix (batch, export, Workbench, Figure, and
  related provenance): `147 passed in 6.01s`.
- Structured verifier exited `0`: task-check valid, Ruff/compile/type baseline
  passed, quality gate `287 passed`, preprocessing gate `106 passed`, and
  whitespace passed.
- Fresh exact SAXS collection found `458 tests`; the bounded run reached the
  tool limit after about `304s` with exit `124` and no pytest summary. No
  Python/pytest process remained. This is an incomplete diagnostic, not a
  pass or failure result.
- Test-storage report exited `0` in dry-run mode: `471` artifacts and `89`
  eligible candidates; no test data was deleted or moved.
- `git diff --check` passed. The concurrent `active-work.md` and
  `current-state.md` changes remain untouched.
