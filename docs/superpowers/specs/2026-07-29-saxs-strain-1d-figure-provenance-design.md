# SAXS strain 1D Figure projection provenance design

## Decision

Expose deterministic q/I projection counts in the strain 1D main evolution and
ordinary/diagnostic sequence Figure recipes. The provider continues using its
existing `_profile_values()` filter; provenance is an audit projection, not a
scientific validity decision.

## Data flow

`_profile_source()` remains the single source builder. The main and sequence
builders compute a detached quality map only when a 1D profile source is
actually emitted, keyed by `str(frame.index)`, and place that map under
`recipe["parameters"]["profile_projection_quality"]`. The detector-capable
2D path does not receive this 1D field. The q-strain heatmap keeps its current
finite-pair/interpolation/clipping behavior and is not reinterpreted by this
task.

## Evidence shape

Each emitted frame entry contains JSON-native integers for:

- `input_pair_count`: aligned q/I prefix length;
- `retained_pair_count`: pairs passing finite q/I, positive q, and positive I;
- `nonfinite_pair_count`: pairs with non-finite q or intensity;
- `nonpositive_pair_count`: finite pairs rejected by the existing positivity
  filter;
- `status`: `complete` when no pair is rejected, otherwise `partial_invalid`.

The shape matches the existing static 1D Figure contract. Curves that the
existing provider omits because they are insufficient remain omitted and do
not receive fabricated entries.

## Invariants

- No raw q/I arrays are mutated.
- No new q or intensity threshold is introduced.
- No sequence sorting, common-q interpolation, heatmap clipping, quality
  level, physical gate, AI/rescue decision, or publication role changes.
- Recipe metadata stays strict JSON-safe and detached from source arrays.

## Verification boundary

TDD RED/GREEN, strain Figure regressions, task-scoped structured verification,
fresh SAXS matrix, diff/allowlist audit, and storage report/clean dry-runs are
required. `test_storage.py --apply` is prohibited.

## Recorded evidence

- TDD RED/GREEN and the related strain slice passed as recorded in the task
  card.
- Structured quality/preprocessing gates passed at `287` and `106` tests.
- Fresh SAXS matrix passed `551 tests` with `6 warnings` and exit code `0`.
- Storage report/clean remained dry-run only with `301 artifacts`, `29
  eligible`, and no removal.
