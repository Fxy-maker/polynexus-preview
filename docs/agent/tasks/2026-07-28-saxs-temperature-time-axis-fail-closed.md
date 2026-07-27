# Task: SAXS mismatched temperature time axis fail-closed

**Status:** checkpointed locally; 2026-07-28

## Goal

Keep temperature-frame analysis available when an optional `times` list has a
different length, while explicitly disabling time-dependent Avrami evidence
instead of indexing a mismatched array.

## Root-cause evidence

`analyze_temperature_series([170.0, 180.0], [q, q], [I, I], times=[0.0],
cfg=SAXSConfig())` currently raises `IndexError` at
`np.array(times, dtype=float)[sort_idx]`. The time axis is optional and only
feeds Avrami kinetics; the temperature-frame analysis itself can still run.

## Design decision

Detect a supplied `times` length mismatch before sorting. For the mismatch,
use an all-NaN internal time array of the correct frame length solely to keep
array alignment safe, and set `result.avrami` to the strict JSON-safe failure
record `{"valid": False, "reason": "temperature_time_axis_length_mismatch"}`.
Do not use positional indices as synthetic times. Keep the existing behavior
for absent or correctly-sized `times`, and leave all temperature-frame and
Guinier analysis unchanged.

## Non-goals

- No interpolation or fabrication of time values.
- No changes to temperature sorting, source indices, q/I analysis, quality
  levels, physical gates, rescue, AI, or publication roles.
- No handling of invalid time elements in this task; that is a separate axis
  boundary.

## Acceptance criteria

- [x] A mismatched supplied `times` list no longer raises.
- [x] All temperature frames remain present with their original source indices.
- [x] Avrami is explicitly invalid with the existing reason string and cannot
  be promoted by `get_parameters()`.
- [x] Absent or correctly-sized time axes retain existing behavior.
- [x] Focused RED/GREEN, exact SAXS matrix, structured verifier, diff check,
  and one explicit allowlist checkpoint are recorded.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_temperature.py`
- `tests/test_saxs_temperature_time_axis_fail_closed.py`
- This task card, design/spec/plan, and durable agent memory.

## Implementation plan

1. Add a regression using a cooling series and a short `times` list; run RED.
2. Add the minimal mismatch guard and explicit Avrami failure record.
3. Run focused temperature tests, the exact SAXS matrix, structured verifier,
   and diff checks.
4. Record evidence and create one explicit allowlist checkpoint.

## Verification evidence

- TDD RED: `1 failed`, reproducing the `times` sort-index `IndexError`.
- Focused GREEN: `24 passed` across time-axis, invalid-temperature, empty-
  series, Guinier, and temperature-status tests.
- Exact SAXS matrix: `417 passed, 6 warnings`. Warnings are the existing Arial
  glyph notices and EDF geometry-default notices; no test failed.
- Full/boundary repository verification is not claimed. Invalid time elements
  (as opposed to a length mismatch) remain a separate future boundary.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_temperature_time_axis_red'
python -m pytest -q tests/test_saxs_temperature_time_axis_fail_closed.py

$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_temperature_time_axis_focus'
python -m pytest -q tests/test_saxs_temperature_time_axis_fail_closed.py tests/test_saxs_temperature_invalid_axis_fail_closed.py tests/test_saxs_temperature_empty_series_fail_closed.py tests/test_saxs_temperature_guinier_evidence.py tests/test_saxs_temperature_status.py

$saxsTests = Get-ChildItem tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests --basetemp=D:\PolyNexus_saxs_temperature_time_axis_matrix

$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_temperature_time_axis_verify'
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-temperature-time-axis-fail-closed.md --changed --types
git diff --check
```

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/saxs_temperature.py`
- `tests/test_saxs_temperature_time_axis_fail_closed.py`
- `docs/agent/tasks/2026-07-28-saxs-temperature-time-axis-fail-closed.md`
- `docs/superpowers/specs/2026-07-28-saxs-temperature-time-axis-fail-closed-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-temperature-time-axis-fail-closed.md`
- `docs/agent/memory/current-state.md`
- `docs/agent/memory/active-work.md`
