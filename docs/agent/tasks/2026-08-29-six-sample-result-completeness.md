---
task_id: 2026-08-29-six-sample-result-completeness
kind: scientific
status: completed
date: 2026-08-29
title: Close provider result completeness gaps found by six-sample replay
---

# Close provider result completeness gaps found by six-sample replay

## Goal

Ensure calculated provider metrics remain visible through `ComputeRun`, the
provider capability projection, result tables, and the evidence package.

## Scope

- Treat null provider aliases as unavailable rather than completed.
- Add aliases only for metrics already emitted by a provider.
- Preserve WAXS static peak/decomposition, Williamson–Hall, and unit-cell fields.
- Preserve SAXS Porod, Kratky, and Guinier scalar outputs.
- Re-run the six-sample project read-only after the changes.

## Non-goals

- No raw-data edits, threshold relaxation, material inference, or automatic
  publication decisions.
- Do not fabricate metrics that the provider did not calculate.

## Affected boundaries

- Provider capability registry and `CapabilityExecutor`.
- SAXS/WAXS public parameter projections consumed by `ComputeRun`.
- Six-sample project workflow, evidence package, and result-table projection.

## Implementation plan

1. Add regression coverage for null aliases and emitted provider fields.
2. Update capability aliases and public SAXS/WAXS projections without changing
   numerical algorithms.
3. Re-run the six-sample project read-only and rebuild its evidence package.
4. Audit run statuses, raw hashes, capability items, result tables, and package
   links; record the external acceptance report.

## Acceptance criteria

- [x] Null aliases do not produce a completed capability item.
- [x] Existing emitted DSC/SAXS/WAXS fields have deterministic capability
  aliases.
- [x] WAXS and SAXS public parameter projections retain the emitted scalar and
  peak/evidence fields.
- [x] Fresh six-sample replay has no unexplained provider failures or missing
  persisted result fields; all 42 runs are `review_required` with no run-level
  failure or block.
- [x] Evidence package and result-table audit is recorded externally at
  `D:\PolyNexus-six-sample-replay-20260829-v011\replay-audit-v011-final.json`.

## Replay evidence

- Package: `D:\PolyNexus-six-sample-replay-20260829-v011\.polynexus\evidence\pa6-six-sample-v011-v001`
- 42 runs, 270 evidence items, 558 indexed figures, and 3,640 copied assets.
- Raw copy contains 270 files and is SHA-256 identical to the v007 raw tree.
- Provider capability gaps are now explicit: SAXS Porod/Kratky/Guinier and
  WAXS peak decomposition/Williamson–Hall are completed where finite values
  exist; unavailable DSC values remain `needs_input` rather than null-valued
  `completed` items.

## Verification

```powershell
pytest -q tests/test_capability_execution.py tests/test_saxs_batch_parameters.py tests/test_waxs_temperature.py
python scripts/verify.py --task docs/agent/tasks/2026-08-29-six-sample-result-completeness.md --changed --types
```
