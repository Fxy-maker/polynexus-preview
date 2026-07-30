# SAXS Manual Mask Confirmed Rerun Design

## Goal

Add a fail-closed core boundary for user-edited detector masks so a manual
mask can be previewed as a candidate and applied to preprocessing only after
explicit confirmation. The original detector image and the existing SAXS
quality, physical, and publication gates remain authoritative.

## Scope

This slice covers the strict candidate data contract and the 2D preprocessing
boundary. It does not build a GUI drawing tool, infer a mask, call an AI model,
or change any SAXS threshold. A later GUI task can serialize mouse gestures
into this contract; a later AI task can propose the same candidate shape.

## Contract

`build_mask_edit_candidate(base_mask, edited_mask, source_path, frame_index)`
returns a detached JSON-safe mapping containing the image shape, a digest of
the base and edited boolean masks, changed pixel operations, and
`confirmed=False`. The operations use explicit row/column coordinates and a
boolean target state; no interpolation, morphology, or automatic threshold is
introduced.

`confirm_mask_edit_candidate(candidate, base_mask)` verifies the base shape,
base digest, operation coordinates, and edited digest before returning a copy
with `confirmed=True`. Any mismatch raises a typed validation error and cannot
mutate the base mask. `apply_confirmed_mask_edit(base_mask, candidate)` applies
only a validated confirmed candidate to a new boolean array.

## Preprocessing Boundary

`preprocess_pipeline` accepts an optional candidate mapping. A pending,
malformed, or unconfirmed candidate is ignored for numerical integration and
is recorded as `candidate_only` or `invalid` in mask provenance. A confirmed
candidate is validated against the configured mask and passed through every
existing full, sector, and azimuthal integration path. The selected mask is
reported through the existing detector quality report; raw image and q/I
arrays are never overwritten.

## Acceptance

- Candidate serialization is strict JSON-safe and contains no raw image data.
- Base masks remain unchanged after confirmation and application.
- Digest, shape, coordinate, and confirmation mismatches fail closed.
- Pending candidates cannot change numerical preprocessing or quality status.
- Confirmed candidates affect all existing integration paths and expose the
  changed mask through existing provenance fields.
- Existing analysis and physical gates remain the only promotion authority.

## Verification

Focused candidate/preprocessing tests must show RED before implementation and
GREEN after implementation. Then run the task verifier, the exact SAXS matrix,
storage report/dry-run, and diff checks. No storage apply is part of this
task.
