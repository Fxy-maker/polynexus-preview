# SAXS temperature Guinier metric evidence design

Date: 2026-07-27
Status: approved working design

## Goal

Close the first vertical SAXS quality route by making existing temperature
frame-level Guinier evidence available through the same series metric contract
used by Porod, Kratky, invariant, and lamellar evidence.

## Scope

The temperature analysis already emits `TemperaturePointResult.guinier_evidence`
and `TempSeriesResult.guinier_sequence_evidence`. This task adds a
`metric_evidence["guinier"]` series summary derived only from the existing
frame-level `guinier_evidence["metric"]` payloads. The richer sequence payload
remains separate and is still exported unchanged.

The existing SAXS parameter transport, Workbench review text, History
persistence, and quality Export path will carry the new summary through their
existing contracts. No new analysis method or GUI-specific scientific logic is
introduced.

## Non-goals

- no change to Guinier window selection, `qRg < 1.3`, R², or applicability;
- no interpolation, sorting, smoothing, frame deletion, or fabricated Rg;
- no promotion of a series above `Trend`;
- no automatic rescue execution, AI model call, publication authorization, or
  figure-role change;
- no strain-level Rg sequence semantics in this task.

## Data contract

For each temperature frame, the series builder receives a mapping containing
the existing method metrics plus a `guinier` entry copied from
`guinier_evidence["metric"]` when that entry is a mapping. A failed or missing
frame contributes a missing Guinier metric at the original frame index.

`TempSeriesResult.metric_evidence["guinier"]` is produced by the existing
`build_series_metric_evidence` policy. It therefore preserves coverage,
missing/diagnostic/unusable counts, deterministic reason codes, and the
Trend cap. `TempSeriesResult.guinier_sequence_evidence` remains the authority
for temperature-axis continuity and Rg relative-change diagnostics.

The two contracts are complementary:

- `metric_evidence["guinier"]`: common per-metric coverage and level summary;
- `guinier_sequence_evidence`: Rg-specific sequence axis and continuity detail.

## Data flow

```text
analyze_single().guinier_evidence["metric"]
        -> TemperaturePointResult.guinier_evidence
        -> derived per-frame metric mapping
        -> TempSeriesResult.metric_evidence["guinier"]
        -> SAXS.get_parameters()
        -> Workbench / History / Export
```

The derivation is read-only. The original frame evidence and sequence
evidence are retained for Diagnostics and `quality_evidence.json`.

## Failure and downgrade behavior

- Missing `guinier_evidence`, missing nested `metric`, or a non-mapping nested
  value counts as missing for the common summary and remains visible in the
  original quality payload.
- An invalid level is handled by the existing series builder as unusable and
  receives its existing reason codes.
- A complete multi-frame set remains `Trend`, even when every frame is
  quantitative.
- The common summary does not override the separate sequence level; a valid
  frame coverage summary can coexist with a diagnostic sequence axis.

## Acceptance criteria

- Temperature series expose `metric_evidence["guinier"]` when frame Guinier
  metric evidence exists or when frames are present and therefore missingness
  must be represented.
- The summary counts frame coverage and downgrades using the existing builder.
- Existing `guinier_sequence_evidence` and frame DataFrame values are byte-for-
  byte equivalent after JSON normalization.
- `SAXS.get_parameters()`, Workbench, History, and Export preserve the common
  summary and the detailed sequence payload.
- Static and strain behavior remains unchanged.
- Focused tests, SAXS regression tests, task verifier, whitespace checks, and
  the explicit checkpoint command all pass with exact results recorded.
