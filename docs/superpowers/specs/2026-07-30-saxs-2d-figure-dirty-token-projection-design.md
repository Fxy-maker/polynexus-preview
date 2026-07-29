# SAXS 2D Figure dirty-token projection design

## Decision

Extend the existing read-only detector and azimuthal Figure projection
boundaries to coerce numeric tokens elementwise. A malformed token becomes
`NaN` in a detached projection; the existing finite-pixel or aligned chi/I
filter then omits only that pixel or pair. Existing provenance counts and
`complete`/`partial_nonfinite` statuses remain the source of truth for the
projection.

## Invariants

- Detector pixel coordinates remain the sampled source coordinates of every
  retained finite pixel.
- Azimuthal chi/I values use the existing aligned prefix; only finite pairs
  are retained.
- No interpolation, padding, token replacement, frame deletion, sorting, or
  re-analysis is introduced.
- All-invalid or malformed-shape inputs keep their existing fail-closed
  Figure behavior.
- Projection provenance remains detached and strict JSON-safe.
- Analysis quality levels, detector/orientation semantics, physical metrics,
  publication roles, and AI/rescue behavior do not change.

## Verification boundary

The task requires TDD RED/GREEN, focused detector/azimuthal Figure tests, the
structured verifier, a fresh SAXS matrix with an actual pytest summary,
`git diff --check`, and test-storage report/clean dry-runs. The storage
`--apply` operation is not part of this task.
