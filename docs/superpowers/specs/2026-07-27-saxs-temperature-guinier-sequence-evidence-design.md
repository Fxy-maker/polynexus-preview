# SAXS Temperature Guinier Sequence Evidence Design

## Status

Approved working design for the 2026-07-27 atomic task. This slice makes the
existing conservative sequence evidence observable and traceable; it does not
introduce a new physical analysis method.

## Goal

Expose the existing temperature-series Guinier sequence evidence through the
same parameter, Workbench, History, DataFrame, and Export boundaries used by
frame-level evidence, while preserving the original source-frame identity.

## Current evidence and gap

`build_guinier_sequence_evidence()` already consumes observed temperatures and
existing frame Guinier evidence. It preserves missing/diagnostic frames,
rejects invalid or duplicate/non-monotonic axes, reports continuity breaks, and
never interpolates or deletes observations. `analyze_temperature_series()`
already stores the result on `TempSeriesResult`.

The current transport path exposes the common `metric_evidence` summary but
does not expose the detailed `guinier_sequence_evidence` in
`SAXSEngine.get_parameters()`. The sequence builder also only retains sorted
sequence positions; it does not carry the existing `TemperaturePointResult`
`source_index`, so a diagnostic index cannot be traced back to the input frame.

## Design

1. Extend `GuinierSequenceEvidence` with a JSON-safe `frame_source_indices`
   tuple. The builder accepts optional source indices, preserves their input
   order, and defaults to an empty tuple when the caller has no source mapping.
   A length mismatch is recorded as a diagnostic reason and never repaired.
2. Pass `TemperaturePointResult.source_index` into the builder after the
   existing temperature sort. Thus sequence positions remain in analysis-axis
   order, while every position can be traced to its original input frame.
3. Add the detailed sequence payload to temperature `get_parameters()` and to
   the existing copied quality fields used for frame-row transport. History
   persistence therefore receives the same JSON-safe payload without a new
   persistence schema.
4. Add a dedicated Workbench review fragment for sequence evidence. It reports
   only existing level/count/reason data and source-position context; it never
   upgrades frame evidence, changes figure roles, or recommends automatic
   rescue. Existing metric review remains unchanged.
5. Add `source_index` to the temperature DataFrame output so table rows and
   sequence evidence share an explicit trace key. Export already serializes
   `guinier_sequence_evidence`; tests will lock its source-index mapping and
   strict JSON behavior.

## Safety and scientific boundary

- No new q-window, qRg, R², uncertainty, continuity, or acceptance threshold.
- No interpolation, sorting beyond the existing analysis sort, frame repair,
  neighboring evidence copy, or AI execution.
- Existing `Quantitative`/`Trend`/`Diagnostic`/`Unusable` levels remain the
  sole quality levels. Sequence `Trend` remains advisory and cannot promote a
  frame or a result to `Quantitative`.
- Missing, duplicate, invalid, and diagnostic frames remain visible and retain
  their original positions/source indices.
- This task is temperature Guinier only; Porod/Kratky/invariant/lamellar,
  strain, raw detector geometry, orientation algorithms, and publication roles
  remain separate stages.

## Verification boundary

The focused matrix will cover the contract builder, temperature propagation,
parameter/Workbench/History/Export consumers, and DataFrame source mapping.
The structured verifier will run with an isolated pytest basetemp when the
repository's pre-existing `.pytest_tmp` lock is present. A full/boundary run is
evidence for the repository state, not a substitute for scientific review.
