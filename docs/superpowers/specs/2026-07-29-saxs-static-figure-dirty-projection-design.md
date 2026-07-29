# SAXS Static Figure Dirty Projection Design

## Goal

Keep the static SAXS publication-figure provider usable when a frame contains
individual non-numeric q or intensity tokens, while preserving the existing
fail-closed behavior for frames with too few plottable points.

## Scope

The change is limited to the `figure_static` numeric-pair boundary used by
static SAXS figure definitions. Each input element is coerced independently;
conversion failures become `NaN` at the same position, and the existing
finite/positive filtering decides whether any profile remains plottable.

## Invariants and non-goals

- Preserve input length and ordering until the existing filtering/sorting
  stage; never interpolate, pad, infer, duplicate, or repair observations.
- Preserve caller-owned arrays and the immutable `SAXSFrameView` contract.
- Keep existing minimum-point, positivity, uniqueness, and role rules.
- Do not alter SAXS analysis algorithms, DataQualityReport levels, physical
  thresholds, AI/rescue behavior, evidence payloads, or publication roles.
- Do not change temperature, strain, detector, GUI, export, or real datasets.

## Design

Add a private elementwise numeric coercion helper in
`polynexus/core/saxs_engine/figure_static.py` and use it inside
`_numeric_pairs`. The helper returns a fresh float array and catches only
per-element conversion failures (`TypeError`, `ValueError`, and
`OverflowError`). The existing pair-length and finite/positive checks remain
the sole eligibility decisions. Thus a dirty profile with enough valid pairs
still emits its static figure, while an all-invalid or undersized profile
continues to return `None`.

## Evidence and verification

The regression test will exercise the real static provider with one dirty frame
and one clean frame, assert that the static comparison remains available and
contains only the surviving valid pairs, and assert that an all-invalid frame
does not create a sample profile. The focused test, task-scoped verifier,
`git diff --check`, exact SAXS matrix when bounded execution produces a final
pytest summary, and storage report/clean dry-run provide evidence. No
`test_storage.py --apply` command is permitted.
