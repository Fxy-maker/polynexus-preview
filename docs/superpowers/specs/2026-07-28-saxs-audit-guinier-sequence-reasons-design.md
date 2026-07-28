# SAXS Acceptance Audit Guinier Sequence Reasons Design

**Date:** 2026-07-28
**Status:** Approved working design for the active SAXS quality goal

## Problem

The existing audit builder recursively summarizes SAXS quality reports,
orientation, and metric evidence, but does not inspect the already-transported
`guinier_sequence_evidence` mapping. On a failed temperature run this hides the
most direct explanation for why the sequence is unusable from the audit itself.

## Design

Within the current recursive mapping traversal, inspect only mappings under the
existing `guinier_sequence_evidence` field. Copy its existing `level` into
`evidence_levels["guinier_sequence_evidence"]` and append its existing
`reason_codes` to the audit's detached `reason_codes`. Duplicate reasons remain
deduplicated by the existing helper. No new reason or reclassification is
introduced.

## Safety boundary

The builder remains read-only and JSON-safe. It does not recalculate Guinier,
alter the sequence payload, infer missing frames, or make `Unusable` evidence
quantitative. Existing audit status logic continues to determine
`diagnostic_only`/`review_required` from existing gates.

## Verification

Pure mapping tests and an optional real PA6 temperature test prove that the
sequence level and `guinier_sequence_no_valid_frames` are surfaced while the
original parameters remain unchanged. The exact SAXS matrix and structured
verifier remain required.
