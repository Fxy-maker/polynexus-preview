# SAXS detector Figure projection provenance design

## Decision

Extend the existing strain detector Figure recipe with deterministic provenance
for the sampled detector projection. For each selected frame, record the
number of sampled pixels, retained finite pixels, and sampled non-finite pixels
plus a `complete` or `partial_nonfinite` status.

These are counts about the Figure projection only. They are not raw-detector
quality metrics, mask/saturation judgments, geometry validation, or new
physical thresholds. The existing anisotropy analysis remains fail-closed and
the existing finite-pixel projection remains unchanged.

## Invariants

- Counts refer to the deterministic sampled grid (at most 256 rows by 256
  columns), never to unsampled raw pixels.
- Retained coordinates and values are exactly the projection already emitted.
- A completely invalid sample remains unavailable with the existing failure
  reason; no provenance record is fabricated for it.
- The recipe is detached, JSON-safe, and keyed by the existing frame index.
- No quality level, publication role, Figure ID, analysis result, or physical
  decision changes.

## Verification boundary

TDD RED/GREEN, focused detector/Figure regressions, the structured verifier,
fresh SAXS matrix, `git diff --check`, and storage report/clean dry-runs are
required. `test_storage.py --apply` remains prohibited.
