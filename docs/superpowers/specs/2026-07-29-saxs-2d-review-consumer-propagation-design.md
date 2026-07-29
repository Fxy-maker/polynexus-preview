# SAXS 2D Reviewer Evidence Consumer Propagation Design

## Context

The `saxs.2d` reviewer scope is now validated and attached to SAXS Figure
recipes. The remaining boundary is consumer consistency: the same reviewer-owned
decision must be visible in the result contract, the authoritative
`quality_evidence.json` bundle, and the persisted Figure document/V2 sidecar so
Workbench, History, and Export can reuse one detached snapshot.

## Goal

Propagate the existing configured SAXS reviewer decision through those
consumers without recalculating SAXS metrics or changing any scientific gate.

## Non-goals

- No new reviewer fields, thresholds, quality levels, physical gates, or
  publication-role rules.
- No interpolation, frame fabrication, automatic rescue, AI call, or confirmed
  rerun.
- No raw detector arrays or raw q/I payloads in the review snapshot.
- No GUI-specific SAXS branch when the existing generic scientific-review
  presentation can consume the snapshot.
- No changes to real datasets, generated outputs, or unrelated parallel files.

## Design

Add one core projection helper that reads the existing
`SAXSConfig.scientific_review`, validates it through the shared review contract,
matches it against the existing `SAXSFrameView` source references, and returns
the existing fail-closed decision shape. The helper is a detached JSON-safe
projection; it never mutates the config, frames, or analysis result.

The result-contract publisher and SAXS bundle exporter call this helper with
the engine's existing frame views. The result parameters expose the snapshot as
`scientific_review`, and `quality_evidence.json` exposes the same snapshot.
Figure providers already attach the same projection to Figure recipes; the
pipeline's document and V2 sidecar therefore persist it without a new manifest
schema. The generic Workbench/History/Export adapter consumes the result
snapshot through its existing recursive lookup.

When no configured review exists, the projection remains explicitly
`review_missing`; malformed records, scope mismatch, and source mismatch stay
disallowed. An accepted record is only evidence that the reviewer-owned scope
and source matched; it does not change `QualityLevel`, physical validity,
publication role, or rescue status.

## Data flow

```text
SAXSConfig.scientific_review
        + existing frame source refs
                  |
                  v
  detached fail-closed reviewer evidence
       /             |              \
result.parameters  quality_evidence  Figure recipe
       |             |                |
Workbench/History/Export   bundle manifest   document + V2 sidecar
```

## Acceptance criteria

1. A valid `saxs.2d` record matching all supplied detector frame sources is
   present, unchanged in meaning, in result parameters and
   `quality_evidence.json`.
2. The persisted Figure document and `reactive_figure_v2.json` retain the same
   `saxs.2d` reviewer evidence, while the manifest remains ready and its
   publication role is unchanged.
3. Existing generic Workbench, History, and Export presentation tests can read
   the result snapshot and display its record ID, scope, and status.
4. Missing, malformed, wrong-scope, partial-source, and source-mismatched
   records are fail-closed in every persisted consumer.
5. Existing 1D evidence, quality levels, physical gates, AI/rescue behavior,
   and publication roles remain unchanged.

## Verification strategy

- TDD RED: consumer test fails because result/export snapshots are absent.
- GREEN: focused 2D consumer and persistence matrix.
- Structured verifier: task-scoped `scripts/verify.py` gates.
- Exact SAXS matrix and diff/allowlist audit.
- Test-storage report and non-destructive clean dry-run only.
