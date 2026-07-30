---
title: SAXS detector provenance structural audit acceptance
date: 2026-07-30
status: verified
---

# SAXS Detector Provenance Structural Audit

The existing SAXS scientific acceptance audit now exposes a detached
`detector_provenance_audit` for raw detector reports. It checks only supplied
structural relationships: detector shape and pixel count, required geometry
field-source names, configured mask shape alignment, and explicit provenance
validity values.

The projection reuses the existing quality levels conservatively:

- explicit `validated` provenance with no contradiction is `Trend` and
  `structurally_consistent`;
- missing, unknown, or `not_assessed` provenance is `Diagnostic` and
  `review_required`;
- explicit `invalid` provenance or structural contradictions are `Unusable`
  and `unusable`.

It never infers calibration, beam center, mask validity, orientation meaning,
or publication eligibility. Existing acceptance status, physical gates,
publication fields, and `publication_decision_changed=False` remain unchanged.
Sector-map evidence does not receive fabricated raw-detector provenance.

## Evidence

- RED: `4 failed, 1 passed` with the expected missing projection key.
- GREEN: focused structural-audit suite `5 passed`.
- Adjacent 2D/acceptance/transport suite `52 passed`.
- Complete SAXS matrix `626 passed, 6 warnings`.
- Task-scoped verifier: task/memory checks, Ruff, compile, type baseline,
  quality gate `290 passed`, preprocessing gate `106 passed`, and whitespace
  all passed.
- `git diff --check` passed.

## Limits

This is a provenance and structural audit, not instrument calibration or
scientific release approval. Raw detector geometry, mask correctness,
orientation interpretation, restarted-GUI review, and publication decisions
remain separate human or instrument-aware gates.
