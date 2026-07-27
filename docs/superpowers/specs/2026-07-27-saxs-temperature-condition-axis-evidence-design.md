# SAXS Temperature Condition-Axis Evidence Design

Date: 2026-07-27
Status: approved working design

## Goal

Bind the existing temperature axis to the common per-metric series evidence
for Porod, Kratky, invariant, lamellar, and Guinier summaries. Consumers must
be able to see whether a metric summary has an ordered, duplicate-free,
finite temperature axis without reconstructing the frame sequence.

## Scope

Extend `MetricEvidenceSummary` with an optional strict-JSON `condition_axis`
mapping. The existing series builder accepts optional condition values and a
condition name, preserves every input position, and reports invalid,
duplicate, and non-monotonic positions. Temperature aggregation passes its
already sorted `temperatures` array as `temperature_C`; existing
`frame_source_indices` remain the original frame mapping.

## Non-goals

- no new Porod, Kratky, invariant, lamellar, or Guinier calculation;
- no new numerical or physical threshold;
- no interpolation, smoothing, frame deletion, reordering, repair, or source
  substitution;
- no automatic downgrade of the existing metric level and no publication,
  rescue, or AI behavior change;
- no strain-axis semantics in this temperature-only task.

## Contract

When no condition axis is supplied, `condition_axis` remains an empty mapping.
When supplied with matching length, it contains:

```text
condition_name: str
condition_values: list[float | null]
invalid_condition_indices: list[int]
duplicate_condition_indices: list[int]
nonmonotonic_condition_indices: list[int]
status: ordered | diagnostic | empty
```

Non-finite or non-numeric values become `null` at their original positions
and are listed as invalid. Duplicate positions follow the existing Guinier
axis convention and include both the earlier and current positions.
Non-monotonic positions compare adjacent finite values using the existing
strict ordering rule. A mismatched condition list produces no partial values,
sets `status=diagnostic`, and records
`series_metric_condition_axis_length_mismatch`.

The block is diagnostic provenance only. Existing summary counts, levels,
applicability, frame evidence, DataFrame values, and physical gates remain
unchanged.

## Verification boundary

Focused tests cover complete, invalid, duplicate, non-monotonic, mismatched,
empty, strict JSON, and temperature sorting cases. The full SAXS matrix and
task-scoped verification remain required; real-data scientific acceptance is
separate.
