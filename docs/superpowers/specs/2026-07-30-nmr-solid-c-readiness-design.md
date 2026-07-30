# NMR Solid-C Readiness Design

Date: 2026-07-30
Status: approved conservative evidence/UI boundary
Scope: non-SAXS NMR solid-C Results review only

## Decision

Expose the existing NMR solid-C assignment gate as a JSON-safe
`assignment_readiness` object in the NMR evidence and as a compact Results
review summary. Also expose the existing ppm-axis provenance in that summary.
No new assignment inference or ppm conversion is introduced.

## Classification

- `not_applicable`: non-solid-13C input.
- `supported`: existing phase assignment gate is supported.
- `assignment_limited`: Xc exists but phase assignment support is incomplete.
- `missing_assignment`: no usable phase assignment supports the Xc claim.

Only the existing `supported` state reports `allowed=true`. The object is a
read-only projection of `Xc_assignment_status`; it does not replace the
existing `nmr.solid_c` scientific review record or figure-role gate.

## Axis boundary

The summary reports the existing `axis_evidence` source, reason, units,
calibration boolean, and range. Frequency-like JEOL metadata remains raw and
unconfirmed; no values are reinterpreted as ppm.

## Non-goals

- Do not assign peaks, change assignment confidence thresholds, or calculate a
  new Xc.
- Do not promote NMR figures or alter scientific review decisions.
- Do not edit real NMR files, SAXS files, or generated artifacts.
