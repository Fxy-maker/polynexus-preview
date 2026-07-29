# SAXS Static and Temperature Detector Figure Design

**Date:** 2026-07-29
**Status:** Approved working design for the current SAXS quality goal

## Goal

Close the Figure-layer gap for static and temperature SAXS runs by exposing a
diagnostic 2D detector projection whenever an existing source path is a
supported detector image. The projection is a detached view of the sampled
pixels and carries the same finite/partial provenance already used by the
strain Figure provider.

## Non-goals

- Do not re-run SAXS analysis, sector integration, orientation analysis, or
  detector quality assessment.
- Do not infer geometry, beam center, mask, saturation, calibration, or
  material structure.
- Do not interpolate, replace, pad, reshape, or fabricate pixels or frames.
- Do not add thresholds, quality levels, physical gates, AI calls, rescue
  actions, publication roles, or publication authorization changes.
- Do not edit real datasets, generated outputs, scratch directories, or the
  parallel `current-state.md` change.

## Existing evidence boundary

`SAXSFrameView.source_path` already preserves the source path for static and
temperature frames. `read_image()` and `SUPPORTED_2D_EXTENSIONS` already
define the accepted detector-image input boundary. The strain Figure provider
already defines the deterministic 256-by-256 maximum sampled grid and finite
pixel retention contract. This task reuses those facts through a small shared
projection module rather than introducing a second numeric policy.

## Contract

The new private projection service returns zero or more detached
`DetectorFrameEvidence` records and a frame-indexed failure mapping. A record
contains:

- a memory `FigureDataSourceDefinition` with `pixel_x`, `pixel_y`, and
  `log_intensity` columns;
- `sampled_pixel_count`, `retained_pixel_count`, and
  `nonfinite_pixel_count`;
- a `projection_quality` mapping with `complete` or `partial_nonfinite`
  status.

Only finite sampled pixels are placed in a Figure source. An unsupported,
unreadable, malformed, empty, or all-nonfinite source produces a failure and
no fabricated source. The failure is retained in the Figure recipe when a
diagnostic definition has at least one usable source.

## Mode behavior

- Static uses deterministic representative selection of at most three frames
  for the diagnostic detector Figure. The existing static profile and
  diagnostic definitions remain unchanged.
- Temperature uses the already selected representative frame indices from
  its existing condition-axis selection. The detector Figure is diagnostic
  and retains condition labels only as panel text; it does not make a
  temperature claim.
- Both modes create a definition only when at least one selected detector
  source yields a usable finite projection. All-invalid input remains absent
  and does not create an empty Figure.
- The recipe records source paths, selected/included frame indices, selection
  reasons where available, failures, and per-frame projection quality. The
  existing Figure evidence attachment remains the authoritative quality
  reference.

## Error handling and compatibility

The source reader is called only by the Figure projection boundary and all
reader/projection failures are converted to detached reason strings. Existing
1D providers, analysis DTOs, quality reports, orientation evidence, rescue
  evidence, manifests, and exports are not recalculated or rewritten. Detector
  axis labels use the existing shared scientific label vocabulary.

## Verification and acceptance

- Static and temperature focused tests prove usable finite pixels, mixed
  non-finite pixels, strict JSON-safe recipe provenance, and all-invalid
  fail-closed omission.
- The focused Figure/2D/publication matrix, structured task verifier, exact
  SAXS matrix, `git diff --check`, storage report, and dry-run storage clean
  must run with fresh output and explicit exit codes.
- The checkpoint uses only the explicit allowlist in the task card. Existing
  scientific and human review gates remain open.
