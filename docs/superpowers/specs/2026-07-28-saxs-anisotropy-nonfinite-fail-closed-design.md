# SAXS anisotropy non-finite input fail-closed design

## Decision

The public `analyze_anisotropy()` boundary will reject any non-finite value in
the five required numeric inputs: `I_2d`, `q`, `chi`, `q_1d`, and `I_1d`.
Non-finite values are a structural input failure for orientation analysis, not
a candidate for interpolation, pixel deletion, axis inference, or rescue.

The analyzer returns its existing empty `AnisotropyResult`, attaches the
existing sector-map `DetectorQualityReport`, and routes an empty metric payload
through `build_orientation_evidence`. The evidence is therefore `Unusable`,
strictly JSON-safe, and contains the explicit reason code
`orientation_input_nonfinite`.

## Scope and invariants

- Valid finite inputs use the existing azimuthal, Herman, peak, pattern, and
  automatic-axis calculations unchanged.
- The input objects are converted to detached numeric arrays without mutation.
- No non-finite value is removed, replaced, interpolated, extrapolated, or
  used to infer detector geometry or orientation.
- Existing shape and conversion failure reason codes remain unchanged.
- Detector evidence remains evidence about the supplied sector map, not a
  claim about raw detector saturation, masks, or geometry.
- Existing physical thresholds, quality levels, rescue behavior, and downstream
  Figure/Workbench/Export contracts are unchanged.

## Acceptance criteria

1. Each of the five required inputs can independently contain `NaN` or `Inf`
   without raising from `analyze_anisotropy()`.
2. Every such case returns no orientation metrics, `Unusable` orientation
   evidence, and the `orientation_input_nonfinite` reason code.
3. Detector and orientation evidence serialize with
   `json.dumps(..., allow_nan=False)`.
4. Existing empty, shape-invalid, configured-axis, auto-axis, and isotropic
   paths remain covered and passing.

## Verification boundary

The implementation is verified with a focused TDD regression, the SAXS 2D /
strain consumer matrix, the structured task verifier, `git diff --check`, and
the repository test-storage dry-run. A bounded full/boundary run is reported
only if it produces a fresh pytest summary; timeout or no-summary is recorded
as a limitation.
