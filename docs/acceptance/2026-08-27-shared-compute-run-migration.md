# Shared ComputeRun migration acceptance — 2026-08-27

## Scope

This checkpoint covers the staged migration of Batch, GUI persistence,
Codex/Agent workflow, DSC multi-program conversion, universal 1-D templates,
and opaque vendor-format envelopes to the shared
`CanonicalTemplate → CapabilityItems → ComputeRun` path.

The continuation also covers the AI-tuning bootstrap and CLI persistence:
valid tuning inputs now create one shared run projection, and persisted
analysis rows retain that projection beside the legacy report summary.

## Evidence

- Batch checkpoint: `570b0fc3`.
- GUI persistence checkpoint: `0e0eaf31`.
- Agent/Codex workflow checkpoint: `5c620d9b`.
- DSC thermal-program checkpoint: `8df35b4b`.
- Canonical routing checkpoint: `bc650989`.
- FTIR preamble and vendor-envelope checkpoint: `675824af`.
- Six-sample read-only replay:
  `D:\PolyNexus-six-sample-replay-20260827-v002\replay-report.json`.

## Replay observations

- All six selected real FTIR CSV files convert to `spectrum_1d.v1`; each
  completed run has two deterministic capability items.
- SAXS and WAXS provider runs complete through their existing compatibility
  readers and retain `saxs.profile.v1` / `waxs.profile.v1` envelopes on the
  shared run; no capabilities are fabricated from opaque bytes.
- PA6, PA6-50, and PA12 DSC inputs produce `thermal_program.v1` runs where
  qualified holds exist. PA11, PA11-50, and PA12-50 remain blocked by the
  existing qualification rules; this is a scientific-data limitation, not a
  reason to relax the gate or invent segments.
- GUI folder batch execution now uses `ComputeRunService` per file. Its
  displayed rows retain the compatibility `params` projection and the shared
  `compute_run` object together.
- Default file-backed Agent/Codex steps now invoke the provider through the
  shared service exactly once; explicit custom provider runners remain
  compatibility adapters.
- Agent replay-validated templates are passed directly to the shared service
  without reconversion. Agent and Compute now use the same source artifact
  identity, while mismatched templates still fail closed before provider
  execution.
- AI-tuning bootstrap now uses the shared service for valid source files and
  publishes its JSON-safe run projection; ambiguous canonical mappings fail
  closed before provider execution.
- AI-tune CLI persistence stores the same projection under
  `results_summary.compute_run` without removing historical fields.

## Focused verification

```text
canonical templates: 23 passed
shared producer/consumer matrix: 91 passed, 4 skipped
AI-tuning producer/persistence matrix: 134 passed, 3 skipped
quality gate: 310 passed
preprocessing gate: 157 passed
structured task verifier: passed
```

## Boundary

New runs from all migrated entry points use the shared public `ComputeRun`
projection. Legacy provider result fields and compatibility readers remain for
read compatibility. Deleting those paths is intentionally deferred until the
full boundary suite and human architecture/scientific review are green.

## Full boundary verification

Command:

```powershell
python scripts/verify.py --changed --types --full --boundary
```

Result: `4133 passed, 38 failed, 25 skipped, 25 warnings` in approximately
34 minutes. The failures are pre-existing release-readiness issues in chart
gallery/figure pipeline, historical GUI persistence and sample browser,
manifest/result-table, and SAXS legacy paths. They prevent a release-green
claim and keep legacy producer deletion open.
