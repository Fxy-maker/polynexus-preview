# Task: SAXS empty temperature series fail-closed boundary

**Status:** checkpointed locally; 2026-07-28

## Goal

Keep an empty temperature acquisition as an explicit, strict-JSON-safe
`TempSeriesResult` with unusable sequence evidence instead of indexing a
nonexistent reference frame.

## Root-cause evidence

`analyze_temperature_series([], [], [], cfg=SAXSConfig())` currently raises
`IndexError: list index out of range` when it unconditionally reads
`q_sorted[0]` for the solid-state reference invariant and long-period checks.
Single empty frames already fail closed through `analyze_single()`; the empty
series boundary does not.

## Design decision

After the existing length validation and before sorting/reference-frame work,
return an empty `TempSeriesResult` populated with empty numeric tracking arrays,
empty status/candidate arrays, existing `Unusable` Guinier sequence evidence
(`guinier_sequence_no_valid_frames`), and existing per-metric empty-series
evidence (`series_no_frames`). Reuse the current evidence builders and keep
length mismatch validation unchanged.

## Non-goals

- No interpolation, frame fabrication, neighbor copy, or synthetic condition.
- No new quality level, numerical threshold, physical gate, rescue, AI, or
  publication-role change.
- No changes to non-empty temperature-series ordering, frame source indices, or
  single-frame fail-closed behavior.
- No changes to static, strain, detector, or GUI consumers.

## Acceptance criteria

- [x] Empty temperature inputs return without exception and preserve an empty
  frame axis.
- [x] The returned Guinier sequence is `Unusable` with the existing
  `guinier_sequence_no_valid_frames` reason.
- [x] Existing per-metric series evidence remains `Unusable` with
  `series_no_frames`; no rescue candidates or derived transition values are
  fabricated.
- [x] Mismatched temperatures/q/I lengths still raise the existing
  `ValueError`.
- [x] Focused RED/GREEN, exact SAXS matrix, structured verifier, diff check,
  and one explicit allowlist checkpoint are recorded.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_temperature.py`
- `tests/test_saxs_temperature_empty_series_fail_closed.py`
- This task card, its design/spec/plan, and durable agent memory.

## Implementation plan

1. Add a focused empty-series regression and verify the current `IndexError`.
2. Add the minimal empty `TempSeriesResult` branch after length validation.
3. Run focused tests, the complete SAXS matrix, task-scoped verification, and
   diff checks.
4. Record exact evidence and create one explicit allowlist checkpoint.

## Verification evidence

- TDD RED: `1 failed, 1 passed`; the empty-series test reproduced the
  `IndexError` at `q_sorted[0]`, while the existing length mismatch contract
  remained green.
- Focused GREEN: `22 passed` across the empty-series, temperature Guinier,
  and temperature-status suites.
- Exact SAXS matrix: `415 passed, 6 warnings`. Warnings are the existing Arial
  glyph notices and EDF geometry-default notices; no test failed.
- The structured verifier and `git diff --check` are the remaining
  pre-checkpoint commands for this task. Full/boundary repository verification
  is not part of this scoped boundary task.
- No interpolation, frame fabrication, transition inference, rescue, AI,
  publication promotion, push, or merge is implied.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_temperature_empty_series_red'
python -m pytest -q tests/test_saxs_temperature_empty_series_fail_closed.py

$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_temperature_empty_series_focus'
python -m pytest -q tests/test_saxs_temperature_empty_series_fail_closed.py tests/test_saxs_temperature_guinier_evidence.py tests/test_saxs_temperature_status.py

$saxsTests = Get-ChildItem tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests --basetemp=D:\PolyNexus_saxs_temperature_empty_series_matrix

$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_temperature_empty_series_verify'
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-temperature-empty-series-fail-closed.md --changed --types
git diff --check
```

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/saxs_temperature.py`
- `tests/test_saxs_temperature_empty_series_fail_closed.py`
- `docs/agent/tasks/2026-07-28-saxs-temperature-empty-series-fail-closed.md`
- `docs/superpowers/specs/2026-07-28-saxs-temperature-empty-series-fail-closed-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-temperature-empty-series-fail-closed.md`
- `docs/agent/memory/current-state.md`
- `docs/agent/memory/active-work.md`
