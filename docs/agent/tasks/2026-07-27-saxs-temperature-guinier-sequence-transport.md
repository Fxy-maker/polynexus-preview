# SAXS temperature Guinier sequence evidence transport

## Goal

Make the existing conservative temperature Guinier sequence evidence
source-traceable and visible through SAXS parameter, Workbench, History,
DataFrame, and Export boundaries.

## Non-goals

- No new Guinier fitting, q-window, qRg, R², uncertainty, continuity, or
  physical acceptance threshold.
- No interpolation, frame repair, neighboring evidence copy, or AI execution.
- No changes to Porod, Kratky, invariant, lamellar, strain, raw detector,
  orientation algorithms, figure roles, or publication policy.

## Affected boundaries

- `GuinierSequenceEvidence` contract and builder source-index mapping.
- Temperature-series propagation and DataFrame output.
- SAXS parameter/History transport, Workbench review/Diagnostics, and Export
  provenance.
- Focused regression tests and durable agent records.

## Acceptance criteria

- [x] Existing sequence evidence accepts an optional source-index mapping and
  round-trips it as strict JSON-safe data.
- [x] Source-index length mismatch remains explicitly diagnostic; no source
  index or frame is invented, reordered, or silently dropped.
- [x] Unsorted input retains the existing sorted analysis axis while each
  sequence position remains traceable to its original `source_index`.
- [x] Temperature `get_parameters()` exposes the detailed sequence payload;
  History and Export retain it unchanged.
- [x] Workbench shows sequence level, valid/total counts, missing/diagnostic
  counts, source-index context, and reason codes without calling it a physical
  pass or enabling rescue.
- [x] Temperature DataFrame rows expose the same source index.
- [x] Existing frame evidence, metric evidence, figure roles, static behavior,
  and strain behavior remain unchanged.
- [x] TDD RED is observed for each new boundary and GREEN after implementation.

## Implementation order

1. Add contract tests and source-index mapping.
2. Propagate existing `TemperaturePointResult.source_index` and DataFrame key.
3. Transport and present the existing sequence payload.
4. Run focused/structured/full verification, update memory, and checkpoint with
   an explicit changed-file allowlist.

## Implementation plan

1. Write contract RED tests for source-index round-trip and mismatch downgrade.
2. Add the optional source mapping without changing the existing sequence
   level calculation or frame values.
3. Write temperature propagation RED tests, then pass existing source indices
   and expose them in the DataFrame.
4. Write parameter/Workbench RED tests, then transport the existing detailed
   sequence payload and render it as diagnostic review evidence.
5. Verify all consumer boundaries and checkpoint only the explicit allowlist.

## Verification commands

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus-saxs-temperature-guinier-sequence'
python -m pytest -q tests/test_saxs_guinier_sequence_evidence.py tests/test_saxs_temperature_guinier_evidence.py tests/test_saxs_batch_parameters.py tests/test_saxs_workbench_series_evidence.py tests/test_saxs_export_bundle.py
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-temperature-guinier-sequence-transport.md --changed --types
git diff --check
```

## Verification

The focused command above must show all new contract, temperature propagation,
parameter, Workbench, History, and Export regressions passing. The structured
verifier must pass task/memory checks, changed-file Ruff/compile/type checks,
quality and preprocessing gates, and whitespace checks. Any default pytest
basetemp lock or full-suite environmental failure must be recorded with its
exact output and must not be presented as a code pass.

Required structured command:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-temperature-guinier-sequence-transport.md --changed --types
```

## Verification result

- TDD RED: the new contract/propagation/parameter/Workbench assertions
  produced `5 failed, 51 passed`; failures were the expected missing source
  mapping and consumer transport/display behavior.
- TDD GREEN and post-change focused matrix: `56 passed`.
- Complete SAXS matrix (`tests/test_saxs_*.py`): `311 passed, 4 warnings`.
- Isolated task-scoped verifier: task/memory checks passed; changed Ruff,
  compile/type baseline, quality `282`, preprocessing `106`, and whitespace
  checks passed.
- A fresh full/boundary invocation was started with an isolated basetemp but
  exceeded the tool's `124` second execution window while the
  `verify.py -> quality_gate.py --all-tests -> pytest -q` process chain was
  still running. It was terminated without a final test count; this task does
  not claim a full/boundary pass.
- Fresh revalidation on 2026-07-27 found no remaining verifier or pytest
  process, and reran the task-scoped verifier (`282` quality tests, `106`
  preprocessing tests) plus the exact SAXS matrix (`311 passed, 4 warnings`).
- Implementation checkpoint: `b7bad1c` (`feat(saxs): expose temperature
  guinier sequence provenance`). This documentation update records the
  checkpoint and its allowlist; it does not expand the implementation scope.

## Changed-file allowlist for checkpoint b7bad1c

- `polynexus/core/saxs.py`
- `polynexus/core/saxs_batch_helpers.py`
- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `polynexus/core/saxs_engine/saxs_temperature.py`
- `polynexus/gui/saxs_results_table_service.py`
- `tests/test_saxs_batch_parameters.py`
- `tests/test_saxs_export_bundle.py`
- `tests/test_saxs_guinier_sequence_evidence.py`
- `tests/test_saxs_temperature_guinier_evidence.py`
- `tests/test_saxs_workbench_series_evidence.py`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`
- `docs/agent/tasks/2026-07-27-saxs-temperature-guinier-sequence-transport.md`
- `docs/superpowers/plans/2026-07-27-saxs-temperature-guinier-sequence-evidence.md`
- `docs/superpowers/specs/2026-07-27-saxs-temperature-guinier-sequence-evidence-design.md`

## Known limitations

This task does not constitute real-data scientific sign-off, expert calibration,
AI candidate execution, detector/geometry acceptance, or final release approval.
