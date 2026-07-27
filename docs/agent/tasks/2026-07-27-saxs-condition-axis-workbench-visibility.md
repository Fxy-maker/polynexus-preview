# SAXS Condition-Axis Workbench Visibility

## Goal

Make existing `MetricEvidenceSummary.condition_axis` defects visible in the
SAXS Workbench review channels while keeping the complete evidence payload
available through Diagnostics, History, and Export.

## Non-goals

- Do not recompute, sort, repair, interpolate, or delete condition values.
- Do not add physical thresholds or change metric levels, counts, or gates.
- Do not interpret a condition-axis hint as a physical transition or pass.
- Do not apply the temperature ordering rule to strain axes.
- Do not change the existing evidence/History/Export contracts.

## Affected boundaries

- `polynexus/gui/saxs_results_table_service.py`
- `tests/test_saxs_workbench_series_evidence.py`
- this task card, spec/plan, and durable memory

## Acceptance criteria

- [x] A `diagnostic` or `empty` existing `condition_axis` produces a clear
  Workbench review hint naming the metric and condition axis.
- [x] The hint reports defect counts and representative positions without
  changing the source mapping; Diagnostics retains the complete arrays.
- [x] A clean `ordered` axis adds no risk warning and does not alter existing
  metric review text.
- [x] English and Chinese review text remain non-physical and localized.
- [x] Existing parameters, Diagnostics, History, Export, metric levels, and
  strain-axis behavior remain unchanged.
- [x] TDD RED/GREEN, focused Workbench matrix, isolated SAXS matrix, task
  verifier, and explicit allowlist checkpoint have exact recorded evidence.

## Implementation plan

1. Add Workbench RED tests for defective, clean, and localized condition axes.
2. Add a presentation-only formatter that consumes the existing nested axis
   mapping, emits a bounded hint, and leaves full arrays in Diagnostics.
3. Compose the hint with current metric and Guinier sequence review text.
4. Run focused/SAXS/task verification, update memory, and checkpoint only the
   explicit allowlist.

## Verification

```powershell
python -m pytest tests/test_saxs_workbench_series_evidence.py -q
python -m pytest (Get-ChildItem tests/test_saxs_*.py | ForEach-Object { $_.FullName }) -q
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_saxs_condition_axis_workbench_verify'
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-condition-axis-workbench-visibility.md --changed --types
git diff --check
```

## Verification evidence (2026-07-27)

- TDD RED with the default repository temp path: `2 failed, 12 passed, 2
  errors`; the failures were the expected missing Workbench condition-axis
  hint, and the errors were the pre-existing `.pytest_tmp` cleanup
  `PermissionError: [WinError 5]` in two history tests.
- GREEN focused Workbench matrix: `16 passed` with an isolated basetemp.
- Workbench/consumer matrix: `56 passed` with an isolated basetemp.
- Complete isolated SAXS matrix: `359 passed, 4 warnings`; warnings are the
  existing Arial CJK glyph warnings from SAXS figure layout.
- Task-scoped verifier with isolated `PYTEST_ADDOPTS`: task/memory checks,
  changed Ruff/compile/type, quality `282 passed`, preprocessing `106 passed`,
  and whitespace all passed.
- `git diff --check` passed. The formatter is presentation-only; full nested
  axis arrays remain in Diagnostics and no analysis/persistence/export code
  changed.

## Known limitations

This task only makes existing axis provenance visible. It does not determine
whether a material transition is real, authorize rescue, or validate strain
loading semantics; those remain scientific review boundaries.

## Changed-file allowlist

- `polynexus/gui/saxs_results_table_service.py`
- `tests/test_saxs_workbench_series_evidence.py`
- `docs/agent/tasks/2026-07-27-saxs-condition-axis-workbench-visibility.md`
- `docs/superpowers/specs/2026-07-27-saxs-condition-axis-workbench-visibility-design.md`
- `docs/superpowers/plans/2026-07-27-saxs-condition-axis-workbench-visibility.md`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`
