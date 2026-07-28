# Real SAXS Acceptance Audit Surface Verification Design

**Date:** 2026-07-28

## Purpose

Verify the existing audit-surface transport against the real Static,
Temperature, and Strain SAXS fixtures. This is an acceptance regression, not a
new scientific algorithm.

## Evidence contract

For each available real mode, run one engine pipeline into pytest's external
temporary root. Compare the strict-JSON audit mapping in:

1. `result.parameters["scientific_acceptance_audit"]`;
2. every generated FigureDefinition document's
   `recipe.evidence.quality_provenance.scientific_acceptance_audit`;
3. exported `quality_evidence.json` and its `bundle_manifest.json` registration.

The test asserts equality of the existing audit snapshot, not a new status or
threshold. It permits each mode's actual evidence level and validation result,
but requires the existing temperature validation state to remain visible.

## Failure boundary

If Figure documents contain the pre-validation audit while final parameters
contain a refreshed post-validation audit, the test fails so the lifecycle
ordering can be repaired explicitly. Missing fixtures skip with a clear reason;
no synthetic data is fabricated. All outputs stay outside the repository.
