# Task: SAXS invalid temperature-axis values fail closed

**Status:** checkpointed locally; 2026-07-28

## Goal

Keep a temperature-series frame whose condition value is a string, `None`, or
another non-finite scalar at its original frame position while downgrading the
condition axis through the existing Guinier sequence evidence contract.

## Root-cause evidence

`analyze_temperature_series(["170", "bad"], [q, q], [I, I], ...)` currently
raises `ValueError: could not convert string to float: 'bad'` at the bulk
`np.array(temperatures, dtype=float)` conversion. The same series with an
explicit `np.nan` already proceeds and emits invalid-axis evidence.

## Design decision

Replace the bulk conversion with an elementwise conversion through the
existing `_coerce_optional_float()` helper. Valid numeric strings remain
numeric; invalid or non-finite values become `np.nan`. Sorting, frame count,
source-index mapping, and all existing sequence evidence builders then operate
unchanged. The invalid frame is retained and the existing
`guinier_sequence_temperature_axis_invalid` reason records the limitation.

## Non-goals

- No inference of a missing temperature from filename, neighboring frames, or
  sequence order.
- No interpolation, frame deletion, condition fabrication, or new threshold.
- No changes to q/I analysis, physical gates, times/Avrami handling, or
  non-invalid temperature behavior.
- No changes to the separate mismatched `times` boundary.

## Acceptance criteria

- [x] Numeric strings are accepted as their numeric temperature value.
- [x] Invalid/non-finite temperature values become NaN without dropping their
  frame or source index.
- [x] Existing sequence evidence reports invalid temperature-axis evidence and
  remains fail-closed; no trend is promoted from an invalid axis.
- [x] Existing temperatures/q/I length mismatch validation remains unchanged.
- [x] Focused RED/GREEN, exact SAXS matrix, structured verifier, diff check,
  and one explicit allowlist checkpoint are recorded.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_temperature.py`
- `tests/test_saxs_temperature_invalid_axis_fail_closed.py`
- This task card, design/spec/plan, and durable agent memory.

## Implementation plan

1. Add a regression for numeric-string coercion and invalid-value preservation;
   run RED against the current bulk conversion.
2. Use `_coerce_optional_float()` elementwise at the temperature-axis boundary.
3. Run focused temperature tests, the exact SAXS matrix, structured verifier,
   and diff checks.
4. Record evidence and create one explicit allowlist checkpoint.

## Verification evidence

- TDD RED: `1 failed`, reproducing `ValueError: could not convert string to
  float: 'bad'` at the bulk temperature conversion.
- Focused GREEN: `23 passed` across invalid-axis, empty-series, temperature
  Guinier, and temperature-status tests.
- Exact SAXS matrix: `416 passed, 6 warnings`. Warnings are the existing Arial
  glyph notices and EDF geometry-default notices; no test failed.
- The separate mismatched `times` failure remains outside this task. Full/
  boundary repository verification is not claimed.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_temperature_invalid_axis_red'
python -m pytest -q tests/test_saxs_temperature_invalid_axis_fail_closed.py

$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_temperature_invalid_axis_focus'
python -m pytest -q tests/test_saxs_temperature_invalid_axis_fail_closed.py tests/test_saxs_temperature_empty_series_fail_closed.py tests/test_saxs_temperature_guinier_evidence.py tests/test_saxs_temperature_status.py

$saxsTests = Get-ChildItem tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests --basetemp=D:\PolyNexus_saxs_temperature_invalid_axis_matrix

$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_temperature_invalid_axis_verify'
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-temperature-invalid-axis-fail-closed.md --changed --types
git diff --check
```

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/saxs_temperature.py`
- `tests/test_saxs_temperature_invalid_axis_fail_closed.py`
- `docs/agent/tasks/2026-07-28-saxs-temperature-invalid-axis-fail-closed.md`
- `docs/superpowers/specs/2026-07-28-saxs-temperature-invalid-axis-fail-closed-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-temperature-invalid-axis-fail-closed.md`
- `docs/agent/memory/current-state.md`
- `docs/agent/memory/active-work.md`
