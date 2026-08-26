# Shared ComputeRun Canonical Routing Design

## Goal

Make `ComputeRunService` the first shared execution path that carries generic
IR/SAXS/WAXS canonical templates and finite capability items while preserving
legacy provider execution and vendor compatibility.

## Data flow

```text
raw path → RawArtifact → converter registry
                    ├─ generic ready → CanonicalExperiment → capability items
                    ├─ generic needs_input → stop before provider
                    └─ vendor/directory envelope → legacy provider path
                                      ↓
                              one ComputeRun
```

The existing direct `CanonicalDataset` and `AnalysisPlan` remain the legacy
provider execution envelope for this phase. `ComputeRun` gains an optional
canonical template reference; the template is source-bound to the same raw
artifact. Capability items are retained on completed runs and on provider
failures after successful conversion, but never on pre-conversion failures.

## Scope

Only Quick Analysis and single-file CLI are affected because both already call
`ComputeRunService`. Batch, Agent/Codex workflow, GUI persistence migration,
and DSC generalization remain later tasks. No provider algorithm is changed.

## Status behavior

- Generic `needs_input`: return before obtaining or invoking a provider.
- Generic ready + provider success: completed run with template and items.
- Generic ready + provider failure: failed run retaining template and items.
- Vendor/directory compatibility: completed/failed legacy run with no
  canonical template or items, as before.
