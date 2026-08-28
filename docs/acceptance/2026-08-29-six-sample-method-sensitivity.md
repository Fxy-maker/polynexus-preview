# Six-sample replay and method-sensitivity boundary — 2026-08-29

## Replay scope

The read-only replay used `D:\PolyNexus-six-sample-replay-20260827-v007` and
its persisted `replay-run-summary.json`. The `raw/` tree was not modified.
The replay contains DSC, FTIR/IR, SAXS, and WAXS inputs; it contains no NMR
input or NMR run, so NMR remains a contract-only verification boundary here.

## Persisted coverage audit

Every persisted workflow step inspected a shared `compute_run.result` with a
`metric_manifest`. No step had a provider failure or canonical block in the
v009 replay log. The manifest contains explicit `computed`/`unavailable`
states and the provider capability items retain `completed` versus
`needs_input`; no missing value was fabricated.

| technique | workflow steps | manifest leaves | computed scalar leaves | method-sensitivity entries |
|---|---:|---:|---:|---:|
| DSC | 12 | 1,908 | 1,752 | 0 persisted in this historical replay |
| FTIR/IR | 246 step projections | 14,760 | 14,760 | 0 |
| SAXS | 6 | 1,500 | 1,272 | 0 |
| WAXS | 6 | 30 | 30 | 0 |

The zero sensitivity count is expected for this historical replay: the
persisted providers did not publish the new explicit `method_variants` or
`AnalysisResult.method_sensitivities` payload. DSC baseline variants remain
available inside its parameter payload and are now adapted when a fresh
ComputeRun is built.

## Contract changes validated

- `ProjectWorkflowService.analyze_project()` now emits one shared result table
  per provider step when scalar manifest values are available. The condition
  key is the explicit workflow `step_id`; no temperature/time/material axis is
  inferred.
- Evidence packages persist the same tables at `result-tables.json` and link
  them from `manifest.json`, so GUI/CLI/ARS consume one table contract.
- `AnalysisResult.method_sensitivities` is an explicit provider input. The
  shared layer normalizes it, recursively adapts DSC baseline variants, fills
  missing sensitivity source with the run artifact path, and exposes the same
  DTO to ARS writing metrics.
- All method alternatives remain diagnostic observations. This layer never
  promotes a candidate to Results or chooses a scientific winner.

## Remaining boundary

Technique-specific candidate calculators for FTIR, SAXS, WAXS, and NMR must
publish explicit alternative values before those methods appear in replay
sensitivity counts. Adding those candidates requires provider-level scientific
review and focused tests; it is not safe to infer them from method names or
single scalar outputs.
