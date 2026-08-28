# Maximum Calculation Output Design

## Goal

Ensure every deterministically computable provider result is discoverable,
traceable, and exportable through the shared `ComputeRun`/evidence contracts,
then expose per-file and group-level result tables for real multi-sample work.

## Scope

- Inventory declared and observed result fields for DSC, FTIR, SAXS, WAXS, and
  NMR.
- Preserve finite results even when quality or evidence warnings apply.
- Add a technique-neutral result-field manifest and group-table projection.
- Replay six real samples and record missing, failed, or unexposed outputs.

## Non-goals

- No RAG, material database, automatic grouping, literature assignment, or
  Results/Discussion decision.
- No algorithm, threshold, preprocessing default, or raw-data modification.
- No automatic averaging across different experimental conditions.

## Contract

Each emitted field must identify its source run/file, measurement or row,
method/configuration, unit, finite value or explicit unavailable status, and
quality/evidence reason codes. A group table may aggregate only rows selected by
the caller with an explicit condition key; it must retain the underlying rows.

## Data flow

```text
provider result -> ComputeRun/result parameters -> field manifest
                                      -> per-file table
                                      -> explicit group statistics
                                      -> JSON/CSV/evidence consumers
```

## Acceptance

1. Every supported technique has a documented field inventory with gaps called
   out explicitly.
2. Existing finite values are not hidden because their writing eligibility is
   diagnostic-only.
3. Group statistics retain source rows and never merge unlike conditions.
4. Six-sample replay produces an auditable report of completed, unavailable,
   and failed fields without changing raw files.
