# IR mapping/ROI contract design

## Decision

IR mapping provider consumes a typed, already-interpreted mapping payload. The
payload contains a scalar map, explicit row/column coordinates, invalid-pixel
mask, map metric label, and ROI spectra. This separates scientific instrument
adaptation from figure lifecycle and prevents the GUI or provider from guessing
what a pixel value or band means.

## Shape rules

- `map_values` is a finite or NaN `rows x columns` array.
- `invalid_pixel_mask` is boolean and exactly `rows x columns`; invalid pixels
  are preserved in the diagnostic figure and are not silently imputed.
- row and column coordinate arrays have lengths `rows` and `columns`.
- each ROI spectrum has finite, equal-length wavenumber/intensity arrays and a
  non-empty stable ROI id; optional assignment rows remain provenance metadata.
- a map may be published with zero valid pixels, but its readiness is diagnostic
  rather than publication-ready.

## Figure pack

1. `ir.mapping.roi`: Main scalar map with explicit metric label.
2. `ir.mapping.spectra`: SI ROI spectra, one series per validated ROI.
3. `ir.mapping.invalid-pixels`: diagnostic mask with invalid-pixel count/ratio.

The provider emits no figure if the core geometry cannot be validated. It keeps
validity and provenance in the recipe so Gallery/Editor/export can trace the
source contract.

## Deferred boundary

No default reader is added until the actual instrument file format or the
pixel-matrix-plus-ROI configuration contract is confirmed. A future adapter may
construct this DTO without changing the shared Figure/Manifest lifecycle.
