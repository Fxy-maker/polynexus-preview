# SAXS temperature 1D Figure projection provenance design

## Decision

Record deterministic q/I pair counts for the existing temperature
representative-profile and waterfall Figure projections. The Figure provider
keeps its current finite/intensity-positive filter and only exposes the filter
provenance in recipe metadata.

## Evidence shape

Each emitted frame entry contains JSON-native integers for:

- `input_pair_count`: aligned prefix length;
- `retained_pair_count`: pairs surviving the existing finite/intensity-positive
  filter before sort/unique;
- `nonfinite_pair_count`: pairs with non-finite q or intensity;
- `nonpositive_intensity_pair_count`: finite pairs rejected because intensity
  is not positive;
- `status`: `complete` or `partial_invalid`.

The same mapping shape is used in the evolution and waterfall recipes. Missing
or insufficient curves remain omitted and do not get fabricated metadata.

## Invariants

- No raw q/I arrays are mutated.
- No q positivity threshold is introduced by this task.
- Existing common-q heatmap interpolation and temperature/Guinier evidence
  remain untouched.
- Recipe metadata is an audit projection, not a scientific validity decision.

## Verification boundary

TDD RED/GREEN, temperature Figure regressions, task-scoped structured
verification, fresh SAXS matrix, diff/allowlist audit, and storage report/clean
dry-runs are required. `test_storage.py --apply` is prohibited.

## Recorded evidence

- Focused TDD RED/GREEN and the temperature Figure/provider slice are recorded
  in the task card.
- Structured quality/preprocessing gates passed at `287` and `106` tests.
- The fresh SAXS matrix passed `549 tests` with `6 warnings` and exit code `0`.
- Test-storage report/clean remained dry-run only with `removed_count=0`.
- The checkpoint is restricted to the source, regression test, task, spec, and
  plan files named by the task allowlist.
