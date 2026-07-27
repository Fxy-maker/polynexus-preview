# SAXS Series Metric Position Evidence Design

Date: 2026-07-27
Status: approved working design

## Goal

Make the existing SAXS series-level metric summaries traceable to their
original frame positions. A consumer must be able to distinguish missing,
diagnostic, unusable, and invalid-level frames without re-walking or guessing
from the frame payloads.

## Scope

Extend the immutable `MetricEvidenceSummary` contract and its existing
`build_series_metric_evidence()` builder with deterministic positional lists:

- positions with a metric payload;
- missing positions;
- diagnostic positions;
- unusable positions;
- invalid-level positions; and
- an optional `frame_source_indices` mapping supplied by a caller that already
  owns source ordering.

Temperature aggregation passes its existing sorted point order and
`TemperaturePointResult.source_index`. Static batch and strain callers do not
invent source indices and continue to use positional evidence only.

## Non-goals

- no new Porod, Kratky, invariant, lamellar, or Guinier calculation;
- no new physical or quality threshold;
- no interpolation, frame deletion, reordering, repair, or neighboring-frame
  substitution;
- no trend calculation or promotion of a series above its existing level;
- no AI call, rescue execution, publication-role change, or GUI-specific
  scientific interpretation.

## Contract and downgrade behavior

`MetricEvidenceSummary.to_dict()` remains strict JSON-safe and
`from_dict()` restores the positional tuples. Position lists refer to the
input sequence order used by the builder. A mapping payload with an explicit
`Unusable` level appears in both evidence and unusable positions; an absent or
invalid level is additionally listed as invalid. A missing metric payload is
not evidence and appears only in missing positions.

When `frame_source_indices` is omitted, the summary contains no source
mapping. When it is supplied with the wrong length, the builder emits no
partial mapping and adds `series_metric_source_index_mismatch`; it never
invents or truncates source indices.

The existing summary level, coverage, counts, reason codes, frame payloads,
DataFrame values, and publication roles retain their current semantics.

## Verification boundary

Focused contract tests prove position classification, strict JSON round-trip,
source-index mapping, and mismatch downgrade. Temperature tests prove sorted
`source_index` alignment. The complete SAXS matrix and task-scoped verifier
remain required; real-data scientific sign-off remains separate.
