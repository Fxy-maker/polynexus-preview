# SAXS metric-evidence DataFrame projection design

## Goal

Make the existing frame-level Porod, Kratky, invariant, and lamellar quality
evidence directly readable in temperature and strain DataFrames. The
projection is an audit view of existing evidence, not a second analysis path.

## Scope

`TempSeriesResult.to_dataframe()` and `StrainSeriesResult.to_dataframe()` will
add stable columns for each of the four existing method keys:

- `<Metric>_level`
- `<Metric>_coverage`
- `<Metric>_reason_codes`

The labels are `Porod`, `Kratky`, `Invariant`, and `Lamellar`. Coverage is
copied only when it is finite; reason-code sequences are copied as the existing
pipe-delimited table representation. A missing or malformed metric payload
produces empty fields and never fabricates a level or coverage value.

## Non-goals and scientific boundary

- Do not add or change Porod, Kratky, invariant, or lamellar calculations.
- Do not add thresholds, interpolation, frame repair, source-index inference,
  rescue, AI decisions, or publication eligibility.
- Do not change the existing `Metric_evidence_levels` compatibility column or
  the dedicated Guinier/Rg columns.
- Do not change static analysis, Figure recipes, Manifest, Export, or GUI
  behavior beyond consumers seeing the existing DataFrame fields.
- Do not edit memory files, real datasets, generated output, or parallel files.

## Data flow and failure behavior

The shared quality-contract helper reads one frame's existing `metric_evidence`
mapping and returns detached scalar/string fields. Temperature and strain
DataFrame builders attach those fields beside their current rows. Invalid
coverage is represented as an empty value; invalid or missing reason-code
payloads are represented without raising. The caller-owned nested mapping is
not mutated.

## Acceptance criteria

- Complete and diagnostic frame evidence is projected for all four methods in
  both temperature and strain DataFrames.
- Missing method payloads yield empty fields and preserve row count.
- Existing values, levels, reason codes, DataFrame shape, and compatibility
  columns remain unchanged.
- TDD RED/GREEN, task-scoped verification, SAXS regression verification,
  storage dry-run, diff audit, and an explicit allowlist checkpoint are
  recorded.
