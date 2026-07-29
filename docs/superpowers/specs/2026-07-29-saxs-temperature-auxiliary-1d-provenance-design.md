# SAXS temperature auxiliary 1D Figure provenance design

## Goal

Record deterministic projection quality for the existing temperature Avrami
series Figure and selected-frame Correlation/IDF Figures so a dirty input is
visible in Figure evidence without changing analysis or publication roles.

## Scope and contract

The Avrami recipe records one `avrami_projection_quality` mapping with aligned
condition/Xc pair counts. Selected-frame evidence recipes record a
`trace_projection_quality` mapping for each emitted Correlation or IDF trace.
Each mapping contains Python integer `input_pair_count`, `retained_pair_count`,
`nonfinite_pair_count`, and `status` (`complete` or `partial_nonfinite`).

Counts are taken before the existing finite projection. Only emitted sources
receive metadata; omitted or malformed traces do not receive fabricated
entries.

## Non-goals and scientific boundary

- No new Avrami, correlation, or IDF calculation.
- No interpolation, padding, sorting, minimum-point relaxation, frame
  fabrication, rescue, AI decision, or publication-role change.
- No change to existing source values, axis definitions, selection order,
  quality gates, or temperature analysis results.
- No static/strain Figure or memory/generated-data changes.

## Acceptance criteria

- Dirty and clean Avrami condition/Xc projections expose deterministic counts.
- Dirty and clean selected Correlation/IDF traces expose deterministic counts.
- Existing finite filtering and omission behavior remains unchanged.
- Recipes remain strict JSON-safe and only emitted sources receive entries.
- TDD RED/GREEN, task-scoped/SAXS verification, storage dry-run, diff audit,
  and explicit allowlist checkpoint are recorded.
