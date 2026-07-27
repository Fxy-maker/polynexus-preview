# SAXS Temperature Condition-Axis Evidence

## Goal

Attach existing sorted temperature-axis provenance to every temperature-series
SAXS metric summary so Porod, Kratky, invariant, lamellar, and Guinier
evidence can be read as diagnostic sequence evidence without guessing.

## Non-goals

- Do not change metric calculations, levels, physical gates, thresholds, or
  publication roles.
- Do not interpolate, repair, delete, reorder, or replace frames.
- Do not add strain-axis semantics, AI execution, or rescue behavior.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `polynexus/core/saxs_engine/saxs_temperature.py`
- `tests/test_saxs_series_metric_evidence.py`
- `tests/test_saxs_temperature_guinier_evidence.py`
- this task card, spec/plan, and durable memory

## Acceptance criteria

- [x] Existing metric summaries optionally contain strict-JSON `condition_axis`
  evidence with name, values, status, and defect positions.
- [x] Invalid, duplicate, non-monotonic, empty, and mismatched axes remain
  explicit and position-preserving.
- [x] Existing summary levels/counts/applicability and frame/source evidence
  remain unchanged.
- [x] Temperature summaries carry the existing sorted `temperature_C` values
  alongside original `source_index` mapping.
- [x] TDD RED/GREEN, focused consumer tests, isolated SAXS matrix, task checks,
  and scoped code checks are run with exact results recorded.
- [x] One explicit-allowlist checkpoint is created without parallel files.

## Implementation plan

1. Add condition-axis contract, defect, mismatch, JSON, and temperature
   propagation RED tests.
2. Implement the frozen nested axis mapping and deterministic builder logic.
3. Pass the existing temperature array through the current aggregation call.
4. Run focused/SAXS/task verification, record limitations, and create one
   allowlist checkpoint.

## Verification

```powershell
python -m pytest tests/test_saxs_series_metric_evidence.py tests/test_saxs_temperature_guinier_evidence.py tests/test_saxs_mode_evidence_propagation.py tests/test_saxs_workbench_series_evidence.py tests/test_saxs_export_bundle.py -q
python -m pytest (Get-ChildItem tests/test_saxs_*.py | ForEach-Object { $_.FullName }) -q
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-temperature-condition-axis-evidence.md --changed --types
git diff --check
```

Recorded results:

- TDD RED: `4 failed, 13 passed`; focused GREEN: `17 passed`.
- Consumer matrix: `41 passed`.
- Isolated full SAXS matrix: `356 passed, 4 warnings`.
- Task-scoped verifier with isolated `PYTEST_ADDOPTS=--basetemp`:
  task/memory checks, changed Ruff/compile/type, quality `282 passed`,
  preprocessing `106 passed`, and whitespace all passed.
- Prescribed verifier without the isolated basetemp reached `229 passed, 53
  errors`; all errors were pre-existing `.pytest_tmp` cleanup
  `PermissionError: [WinError 5]`, so that run is recorded as environment
  blocked rather than a code failure.
- Fresh `python scripts/verify.py --changed --types --full --boundary` with an
  isolated basetemp exited `0`, reported the selected checks passed, and the
  boundary audit passed. Its middle full-pytest count was truncated by the
  tool output and is intentionally not reconstructed from historical runs.
- Scoped Ruff, compile, and `git diff --check` passed.

## Known limitations

This task reports condition-axis provenance only. It does not prove a physical
transition, calibrate a method, or authorize rescue/publication. Strain-axis
semantics require a separate task because loading paths may be intentionally
non-monotonic.

## Changed-file allowlist

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `polynexus/core/saxs_engine/saxs_temperature.py`
- `tests/test_saxs_series_metric_evidence.py`
- `tests/test_saxs_temperature_guinier_evidence.py`
- `docs/agent/tasks/2026-07-27-saxs-temperature-condition-axis-evidence.md`
- `docs/superpowers/specs/2026-07-27-saxs-temperature-condition-axis-evidence-design.md`
- `docs/superpowers/plans/2026-07-27-saxs-temperature-condition-axis-evidence.md`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`
