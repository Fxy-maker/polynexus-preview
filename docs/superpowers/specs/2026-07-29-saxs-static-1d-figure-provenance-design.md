# SAXS static 1D Figure projection provenance design

## Decision

Expose deterministic provenance for the existing static q/I Figure projection
in the Figure recipe. The projection continues to use its current finite and
positive filters; the recipe records how many aligned pairs reached that
filter and why discarded pairs were not plotted.

## Evidence shape

The per-frame detached mapping contains JSON-native integers:

- `input_pair_count`: aligned prefix length;
- `retained_pair_count`: finite, positive q/I pairs emitted to the source;
- `nonfinite_pair_count`: aligned pairs with a non-finite q or intensity;
- `nonpositive_pair_count`: finite pairs rejected by the existing q/I
  positivity filter;
- `status`: `complete` when no pair was discarded, otherwise
  `partial_invalid`.

The mapping is attached only to an emitted static profile Figure. If the
existing minimum-point contract omits a profile, no source or fabricated
provenance is created.

## Invariants

- No raw q/I array is mutated.
- No pair is interpolated, reordered, copied, or replaced by this metadata.
- The recipe is audit metadata, not a scientific quality decision.
- Existing analysis, physical gates, publication roles, and consumer evidence
  remain authoritative.

## Verification boundary

TDD RED/GREEN, static Figure regressions, task-scoped structured verification,
fresh SAXS matrix, diff/allowlist audit, and storage report/clean dry-runs are
required. `test_storage.py --apply` is prohibited.

## Recorded evidence

- RED correctly exposed the missing recipe field; GREEN provenance tests
  passed `2` cases and the static Figure/publication matrix passed `24`.
- Structured verification passed quality `287` and preprocessing `106`.
- Fresh SAXS passed `547` tests with `6` existing warnings in `202.93s`.
- Storage stayed dry-run only: `350` artifacts, `57` eligible, `9` process
  referenced, `284` young, and `0` removed.
