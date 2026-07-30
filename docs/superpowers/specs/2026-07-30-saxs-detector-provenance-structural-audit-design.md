---
title: SAXS detector provenance structural audit
date: 2026-07-30
status: implemented
---

# SAXS Detector Provenance Structural Audit

## Goal

Expose a deterministic, read-only audit of the geometry and mask provenance
already attached to raw 2D detector evidence. The audit makes structural
contradictions and unassessed provenance visible without claiming that a
detector is calibrated or scientifically acceptable.

## Non-goals

- Do not add a detector reader, pyFAI calibration, beam-center inference, mask
  inference, or instrument-specific semantics.
- Do not add or change q windows, detector thresholds, saturation thresholds,
  orientation thresholds, or publication gates.
- Do not recalculate intensity, anisotropy, or any 1D physical metric.
- Do not rescue, interpolate, repair, or discard source data.
- Do not change Figure roles or promote `Diagnostic`/`Unusable` evidence.

## Design

`build_saxs_scientific_acceptance_audit()` will inspect each existing
`raw_detector_quality_report` and add a strict-JSON-safe
`detector_provenance_audit` mapping. Each label contains a list because a
temperature or strain result can carry more than one raw detector report.

Each audit record contains:

- `status`: `structurally_consistent`, `review_required`, or `unusable`;
- `level`: an existing `QualityLevel` value, never `Quantitative`;
- `source_kind`, `reason_codes`, and detached geometry/mask summaries;
- `geometry.field_sources`, required-field gaps, and the supplied validity;
- `mask.configured`, shape, shape-alignment status, and supplied validity.

The audit recognizes only explicit provenance validity values. `validated` can
support `structurally_consistent` when the report structure is coherent;
`not_assessed`, missing, or unknown validity remains `review_required` and
`Diagnostic`. An explicit `invalid` validity or a structural contradiction is
`unusable` and `Unusable`. The audit never treats a header or configuration
source by itself as calibrated.

Structural checks are limited to relationships already represented in the
report: raw-detector source kind, a non-empty two-dimensional shape, coherent
pixel count, required geometry field-source names, mask shape equality when a
mask is configured, and explicit validity values. No numeric quality cutoff is
introduced.

The existing acceptance status, provenance validity, physical gate evidence,
publication fields, and `publication_decision_changed=False` remain
authoritative and unchanged. The new projection is diagnostic evidence only.

## Data flow

```text
existing raw_detector_quality_report
    -> scientific_acceptance_audit
    -> quality_evidence.json / existing consumer projections
```

The source mapping is not mutated. The returned audit is detached and must
remain serializable with `json.dumps(..., allow_nan=False)`.

## Testing

Focused tests cover a coherent validated report, unassessed provenance,
invalid/mismatched provenance, sector-map non-fabrication, detached output,
and strict JSON serialization. Existing SAXS acceptance-audit, 2D, consumer,
and structured verifier checks remain required.
