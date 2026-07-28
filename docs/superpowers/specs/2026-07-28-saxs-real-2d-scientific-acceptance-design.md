# SAXS Real 2D Scientific Acceptance Audit Design

**Date:** 2026-07-28
**Status:** Approved working design for the current SAXS quality goal

## Problem

The real PAD8 in-situ strain run can complete the software pipeline and set
`validation_passed=True` while existing SAXS evidence still says that the
detector/orientation and publication conclusions are not ready. The current
fields already contain the necessary facts, but there is no one structured,
read-only audit that makes this distinction explicit.

## Goal

Add a strict JSON-safe, audit-only summary that reads the existing validation,
quality-level, provenance, reliability, and publication-gate fields. The audit
must make the current scientific boundary visible without changing any physical
calculation, threshold, quality level, Figure role, rescue decision, or
publication authorization.

## Non-goals

- No numeric detector, geometry, mask, saturation, orientation, or material
  threshold is introduced.
- No geometry calibration, mask validation, beam-center interpretation, or
  scientific sign-off is inferred from provenance.
- No existing `validation_passed`, physical metric, `paper_*` flag, or Figure /
  Manifest / Export role is changed.
- No interpolation, frame fabrication, rescue, AI action, or source guessing is
  performed.

## Contract

`build_saxs_scientific_acceptance_audit(validation_passed, parameters)` returns
a detached JSON-safe mapping with:

- `status`: `not_assessed`, `diagnostic_only`, or `review_required`; it never
  means publication approval.
- `automated_validation_passed`: the existing pipeline flag, unchanged.
- `existing_publication_gate`: the existing `paper_figure_candidate`,
  `paper_conclusion_candidate`, and `paper_conclusion_ready` values.
- `evidence_levels`: existing `QualityLevel` values found in raw detector,
  sector/orientation, and metric evidence.
- `provenance_validity`: existing geometry/mask `validity` values, including
  `not_assessed` when present.
- `reliability`: existing strain reliability status and reason.
- `reason_codes`: existing evidence reasons plus deterministic audit labels such
  as `existing_publication_gate_not_ready`.
- `audit_scope="existing_gates_only"` and
  `publication_decision_changed=False`.

The function scans only detached mappings supplied by the caller. A
`diagnostic_only` result is derived from existing false publication flags,
Diagnostic/Unusable evidence, not-assessed provenance, failed validation, or a
non-usable existing strain reliability status. It does not promote any result;
an otherwise unblocked result remains `review_required` for human scientific
review.

## Integration boundary

The SAXS strain-series parameter payload will include the audit under
`scientific_acceptance_audit`. The existing parameters and frame records remain
unchanged; downstream consumers may display or export the detached audit later.
Temperature/static behavior is not changed by this task.

## Verification

Tests will cover pure mapping behavior, input immutability, strict JSON
serialization, missing evidence, and a real PAD8 strain run. The exact SAXS
matrix, structured verifier, diff check, and an explicit allowlist checkpoint
are required. The real-run assertions will prove only the current diagnostic
boundary, not instrument-level scientific validity.
