# SAXS detector Figure dirty projection design

## Decision

The strain Figure provider may retain finite detector pixels when a loaded 2D
detector image contains a mixture of finite and non-finite values. This is a
projection-only recovery: original pixel coordinates are preserved, invalid
pixels are omitted from the diagnostic detector source, and no pixel is
interpolated, inferred, or replaced.

The existing anisotropy/orientation analysis boundary remains fail-closed for
non-finite required inputs. This change does not alter detector quality reports,
mask or saturation semantics, publication roles, physical thresholds, or AI /
rescue behavior. A detector image with no finite pixels remains unavailable.

## Scope and invariants

- Modify only the strain detector Figure projection and its focused regression.
- Keep the existing 256-by-256 deterministic sampling grid for valid images.
- Filter non-finite sampled pixels after sampling; preserve the sampled source
  coordinates for every retained value.
- Continue to use the existing log-count display transform for retained pixels.
- Keep conversion, dimensionality, empty-image, and all-invalid failure paths
  fail-closed.
- Do not touch analysis calculations or the existing orientation evidence path.

## Verification boundary

TDD RED/GREEN, the focused SAXS detector/strain Figure matrix, the structured
task verifier, a fresh SAXS matrix summary when available, `git diff --check`,
and test-storage report/clean dry-runs are required. `test_storage.py --apply`
is prohibited.
