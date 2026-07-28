# SAXS 1D physical-helper dirty-input guard design

## Context

The main `analyze_single()` path already creates a detached sanitized profile,
but low-level physical helpers are also called by temperature, strain, and
batch code. Those callers can reach invariant, Porod, or Kratky calculations
with non-finite, non-positive, or unsorted pairs. The existing helpers then
have inconsistent behavior: integration can include invalid/unsorted values,
Porod's plateau can contain NaN, and Kratky can retain NaN or raise on empty
input.

## Design

At the beginning of `scattering_invariant()`, `porod_analysis()`, and
`kratky_analysis()`, call the existing `sanitize_1d_profile(q, I)`. Use only
its detached `q` and intensity arrays for the existing calculation. This
centralizes the already-approved deterministic policy:

- use the aligned prefix;
- drop non-finite or non-positive q/I pairs;
- stable-sort by q;
- retain duplicate q observations;
- never mutate caller arrays.

Invariant continues to apply its caller/configured q bounds after sanitation;
Porod continues to use the configured Porod window and existing ten-point
gate; Kratky keeps its current peak window and output keys. If the sanitized
profile is empty, Kratky returns `q`, `kratky`, `kratky_norm` as empty arrays
and `q_peak_kratky` as NaN. No helper derives a new quality level or reason
code. In normal analysis, the existing `DataQualityReport` still records the
actions from the main boundary.

## Compatibility and failure behavior

Clean inputs follow the same numerical path except for a detached copy and
stable ordering that is a no-op for already clean monotonic data. Insufficient
survivors retain the existing NaN/empty result behavior. The change is limited
to 1D numeric helper inputs and does not touch 2D detector/orientation data.

## Testing

Use a dirty profile with NaN q/I, a negative intensity, and deliberately
unsorted q. Assert finite sorted survivors, finite invariant/Porod/Kratky
outputs, empty Kratky fail-closed behavior, and unchanged caller arrays. Run
the existing 1D evidence regressions to prove evidence gates and legacy output
contracts remain intact.
