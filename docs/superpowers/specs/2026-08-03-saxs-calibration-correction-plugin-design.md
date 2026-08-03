# SAXS Detector Calibration Correction Plugin Design

**Date:** 2026-08-03
**Status:** Approved for implementation planning with real-data validation open
**Depends on:** q-resolved reliability and stable correction ledger

## Goal

Provide an inactive-by-default, provenance-bearing two-dimensional detector
correction plugin foundation for dark, flat-field, detector background,
polarization/solid-angle, and isotropic-standard evidence. Production numerical
correction remains disabled until both the equations and reviewed calibration
inputs are approved.

## Scientific boundary

Software support can be implemented and tested with synthetic arrays now, but
real instrument correction is not scientifically validated until compatible
calibration EDFs and reviewer evidence exist. Zero-strain data is never a
calibration input.

## Correction request and provenance

Introduce immutable requests and results equivalent to:

```text
DetectorCorrectionRequest
  mode: disabled | candidate | reviewed
  sample_source_id
  dark_source
  flat_source
  background_source
  isotropic_standard_source
  transmission_sample
  transmission_background
  sample_thickness
  background_thickness
  polarization_degree
  geometry_reference
  review_record

DetectorCorrectionResult
  corrected_image
  valid_mask
  correction_ledger
  candidate_systematic_harmonic
  level
  applicable
  reason_codes
```

Detached evidence contains digests and metadata, never pixel arrays or source
paths. The in-memory result may carry arrays only inside core preprocessing.

## Plugin and future correction order

The plugin protocol fixes one owner-controlled operation order for a future
reviewed backend:

1. validate shapes, detector identity, exposure, geometry, and review scope;
2. subtract exposure-scaled dark from sample and background inputs;
3. divide by finite positive flat response and extend the invalid mask;
4. normalize sample and detector background by explicit transmission and
   thickness evidence;
5. subtract the normalized two-dimensional background;
6. apply polarization and solid-angle correction exactly once through one
   backend owner;
7. integrate corrected pixels with the resulting valid mask;
8. estimate an isotropic-standard harmonic only as separately reviewed
   evidence and subtract it only in `reviewed` mode.

Every applied, skipped, unavailable, rejected, or candidate-only operation is
recorded in the correction ledger. This task registers no production backend:
a test-only synthetic backend verifies transaction ordering, rollback,
ownership, and provenance without implementing or validating these physical
equations. Registering a production backend requires a separate scientific
review of dark treatment, flat normalization, background scaling,
polarization/solid-angle ownership, negative-intensity support, and compatible
calibration files.

## Double-correction guards

- EDF metadata that says flat-field corrected blocks another flat correction
  unless a review record explicitly identifies the header as incorrect.
- Existing backend polarization or solid-angle correction ownership blocks a
  duplicate operation.
- A one-dimensional `background_file` cannot be treated as a detector image.
- Detector model/serial, shape, geometry, and exposure mismatches fail closed.
- Missing transmission or thickness cannot silently default to one for a
  reviewed background subtraction.
- Corrected negative intensities remain measured corrected values with support;
  they are not converted into empty bins or clipped before evidence building.

## No-calibration behavior

Default mode is `disabled` and the production backend registry is empty. With
no calibration files or reviewed backend, the plugin returns the original
immutable image, the existing mask, and ledger entries marked `unavailable` or
`not_requested`. Candidate mode may compute compatibility diagnostics but
cannot supply an effective corrected image to final orientation.

## Failure behavior

Any malformed, mismatched, unreviewed, nonfinite, or double-correction input
leaves the authoritative baseline unchanged and records explicit reasons.
Partial correction is not treated as reviewed correction. Candidate output
cannot promote orientation or publication state.

## Boundaries and tests

Create one core detector-correction module, extend explicit config fields and
EDF metadata normalization, call the empty-by-default registry from
preprocessing before chi-by-q integration, and preserve the Task 1 ledger
contract. Tests use a test-only synthetic backend for order, shape/exposure
guards, mask union, negative corrected values, rollback, double correction,
strict JSON, immutability, and disabled identity behavior. Real calibration
acceptance and production numerical correction remain open gates.

## Acceptance criteria

1. Disabled mode is byte-for-byte/numerically identity-preserving.
2. Candidate and rejected corrections cannot affect final orientation.
3. A test-only backend proves one documented transaction order and owner.
4. Every operation has strict provenance and double-correction protection.
5. No real calibration-validity claim is made without reviewed calibration
   EDF evidence.
6. Production reviewed mode remains unavailable until a scientifically
   reviewed backend is explicitly registered in code.

## Non-goals

- No zero-strain subtraction.
- No automatic review approval.
- No GUI workflow beyond existing explicit config binding.
- No claim that synthetic tests validate a real detector.
