# SAXS Workbench Geometry and Mask Provenance Visibility Design

**Date:** 2026-07-28
**Status:** Approved for implementation in the current SAXS quality goal
**Related task:** `docs/agent/tasks/2026-07-28-saxs-workbench-geometry-mask-provenance.md`

## Goal

Make the newly transported raw-detector provenance discoverable in the Results
Workbench without making the Workbench an analysis engine.

## Design

Extend the existing `_detector_evidence_review_text` presentation formatter with
a read-only raw-detector provenance fragment. It reads only the existing
`geometry_provenance` and `mask_provenance` mappings. Geometry output contains
the aggregate source (`header`, `config_default`, `mixed`, or
`invalid_header`) and deterministic counts of `field_sources`; mask output
contains its source, configured flag, and shape. If present, the literal
`validity=not_assessed` is surfaced as a reminder that transport evidence is
not scientific approval.

The fragment is emitted only for `raw_detector_quality_report`. The existing
sector-map report stays a separate detail and does not inherit raw geometry or
mask fields. Existing level, frame coverage, percentage, and reason-code
formatting is preserved and the input mapping is never mutated.

English and Chinese labels are localized in the same function. Unknown nested
values are ignored or rendered through existing safe scalar conversion; no new
threshold or status is inferred from them.

## Verification and boundaries

Tests cover complete geometry/mask payloads, mixed field source counts,
unconfigured masks, absent provenance, raw/sector separation, bilingual output,
and input immutability. The consumer matrix and task-scoped verifier are
required. This slice does not alter Figure, Export, History, Manifest, or any
scientific result contract.
