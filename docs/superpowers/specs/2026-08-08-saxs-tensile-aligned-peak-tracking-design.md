# SAXS Tensile-Aligned Peak Tracking Design

## Goal

Expose lamellar q/L peaks aligned to an explicitly configured tensile axis and
its transverse direction, while preserving the total-profile peak as a
backwards-compatible cross-check.

## Scope and non-goals

The change applies to canonical 2D sector payloads in SAXS strain analysis.
`L_nm`/`q_peak_total_nm1` remain the full-profile tracked feature. New aligned
fields are diagnostic unless the tensile axis is explicitly configured and the
directional support/peak gates pass. No automatic promotion of a principal
scattering axis to a tensile axis, no calibration inference, and no change to
Herman reliability policy are included.

## Data flow

For each frame with a finite `tensile_axis_deg`, build two support-aware radial
profiles from `I_2d(q, chi)`: a pi-periodic sector centered on the tensile axis
and one centered 90 degrees away. Track each peak using the existing bounded
relative-step rule, anchored to the total tracked q. Publish q/L, axis
metadata, and an explicit unavailable reason when canonical 2D data or support
is missing. Fixed detector meridional/equatorial values remain available for
legacy comparison.

The canonical chi map is discretized, so boundary bins are weighted by their
angular overlap with the requested sector instead of being included as whole
bins. When the requested axis and half-width exactly match an existing fixed
meridional/equatorial sector, the already normalized and smoothed fixed profile
is reused after canonical-payload/support validation. Arbitrary-axis profiles
receive the same normalization and smoothing stages before peak tracking.
Canonical validation requires positive strictly increasing q, ordered unique
full-period chi bins, strict numeric support counts, finite intensity wherever
support is positive, and adequate support inside the configured Bragg window.

## Acceptance

- A synthetic 2D frame with distinct axial/transverse q peaks produces distinct
  tensile/transverse q and L fields.
- Missing tensile axis or non-canonical sector data leaves new fields absent or
  unavailable without changing total L or legacy fields.
- GUI/table consumers expose the new fields as diagnostics with no change to
  formal Herman gating.
