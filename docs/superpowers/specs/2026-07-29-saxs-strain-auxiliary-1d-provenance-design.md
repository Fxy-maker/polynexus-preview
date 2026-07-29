# SAXS strain auxiliary 1D Figure provenance design

## Decision

Record deterministic projection counts for the existing strain low-q,
Correlation, and IDF Figure sources. The provider keeps its current filters and
only exposes their audit provenance in recipe parameters.

## Data flow

The low-q builder continues to call `_profile_values()` and receives a detached
`profile_projection_quality` map for frames whose low-q source is emitted. The
trace builder continues to call `_analysis_trace()` and receives a detached
`trace_projection_quality` map for frames whose Correlation or IDF source is
emitted. No shared analysis result or raw array is mutated.

## Evidence shapes

Low-q entries contain `input_pair_count`, `retained_pair_count`,
`nonfinite_pair_count`, `nonpositive_pair_count`, and `status` using the
existing positive-q/positive-intensity profile predicate. Correlation/IDF
entries contain `input_pair_count`, `retained_pair_count`,
`nonfinite_pair_count`, and `status` using the existing finite x/y predicate;
partial traces use `partial_nonfinite`.

## Invariants and boundaries

- Counts are calculated on the aligned prefix before filtering and are strict
  JSON-native integers.
- Source tuples, minimum-point omission, recipe roles, and display ordering do
  not change.
- Heatmap, detector, azimuthal, orientation, phase, static, and temperature
  behavior remains outside this task.
- Recipe metadata is diagnostic provenance, not a scientific validity gate.

## Verification boundary

TDD RED/GREEN, focused strain regressions, task-scoped structured verification,
fresh SAXS matrix, diff/allowlist audit, and storage report/clean dry-runs are
required. `test_storage.py --apply` is prohibited.

## Recorded evidence

- TDD RED/GREEN and the related strain slice are recorded in the task card.
- Structured quality/preprocessing gates passed at `287` and `106` tests.
- Fresh SAXS matrix passed `553 tests` with `6 warnings` and exit code `0`.
- Storage report/clean remained dry-run only with `278 artifacts`, `6
  eligible`, and no removal.
