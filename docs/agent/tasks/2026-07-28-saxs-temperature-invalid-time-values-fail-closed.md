# Task: SAXS invalid temperature-time values fail-closed

**Status:** checkpointed locally in `c07d49a`

## Goal

Keep temperature-frame analysis available when a correctly-sized optional
`times` list contains non-numeric or non-finite elements, while explicitly
disabling Avrami evidence.

## Root-cause evidence

`analyze_temperature_series([180.0, 170.0], [q, q], [I, I],
times=["0.0", "bad"], exp_type="cooling")` currently raises
`ValueError: could not convert string to float: 'bad'` at the bulk time cast.
An explicit NaN time currently runs but does not expose why Avrami is
unavailable.

## Design decision

For a correctly-sized supplied `times` list, convert values elementwise with
the existing `_coerce_optional_float()` helper before applying the temperature
sort index. If any converted time is non-finite, retain the aligned frame
analysis, set `result.avrami` to `{"valid": False, "reason":
"temperature_time_axis_invalid_values"}`, and skip Avrami fitting. Numeric
strings remain valid. The existing mismatch reason remains authoritative when
length is wrong.

## Non-goals

- No interpolation, positional-index substitution, or fabricated time value.
- No changes to temperature sorting, frame source indices, q/I analysis,
  Guinier evidence, physical gates, rescue, AI, or publication roles.
- No changes to the already-implemented time-length mismatch contract.

## Acceptance criteria

- [x] Numeric-string times are converted and retain existing behavior.
- [x] Invalid/non-finite times no longer raise and retain all temperature
  frames/source indices.
- [x] Avrami is explicitly invalid with
  `temperature_time_axis_invalid_values` and is not promoted.
- [x] Existing time-length mismatch behavior remains unchanged.
- [x] Focused RED/GREEN, exact SAXS matrix, structured verifier, diff check, and
  the explicit allowlist checkpoint are recorded.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_temperature.py`
- `tests/test_saxs_temperature_invalid_time_values_fail_closed.py`
- This task card, design/spec/plan, and durable agent memory.

## Implementation plan

1. Add a regression for numeric-string and invalid time elements; run RED.
2. Add elementwise time coercion and explicit invalid-value Avrami status.
3. Run focused temperature tests, exact SAXS matrix, structured verifier, and
   diff checks.
4. Record evidence and create one explicit allowlist checkpoint.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_temperature_invalid_time_red'
python -m pytest -q tests/test_saxs_temperature_invalid_time_values_fail_closed.py

$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_temperature_invalid_time_focus'
python -m pytest -q tests/test_saxs_temperature_invalid_time_values_fail_closed.py tests/test_saxs_temperature_time_axis_fail_closed.py tests/test_saxs_temperature_invalid_axis_fail_closed.py tests/test_saxs_temperature_empty_series_fail_closed.py tests/test_saxs_temperature_guinier_evidence.py tests/test_saxs_temperature_status.py

$saxsTests = Get-ChildItem tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests

$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_temperature_invalid_time_verify'
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-temperature-invalid-time-values-fail-closed.md --changed --types
git diff --check
```

## Evidence before checkpoint

- RED: `1 failed` with the expected bulk-cast `ValueError` for
  `times=["0.0", "bad"]`.
- Focused GREEN: `25 passed`.
- Exact SAXS matrix: `418 passed, 6 warnings` in 30.85s. Warnings are the
  existing Arial glyph and missing-geometry warnings.
- Structured verifier:
  `python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-temperature-invalid-time-values-fail-closed.md --changed --types`
  passed with quality gate `283`, preprocessing gate `106`, Ruff, compile,
  memory/task checks, and whitespace checks.
- Full/boundary verification is a separate release gate and is not claimed by
  this task.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/saxs_temperature.py`
- `tests/test_saxs_temperature_invalid_time_values_fail_closed.py`
- `docs/agent/tasks/2026-07-28-saxs-temperature-invalid-time-values-fail-closed.md`
- `docs/superpowers/specs/2026-07-28-saxs-temperature-invalid-time-values-fail-closed-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-temperature-invalid-time-values-fail-closed.md`
- `docs/agent/memory/current-state.md`
- `docs/agent/memory/active-work.md`
