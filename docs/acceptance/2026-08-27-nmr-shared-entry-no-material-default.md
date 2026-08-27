# NMR Shared Entry Without Material Defaults — Acceptance

Date: 2026-08-27

## Result

Implementation complete, architecture/scientific review required.

NMR table inputs now use the shared material-neutral one-dimensional converter
with `nmr.spectrum.v1`. FID and vendor directories receive a source-bound NMR
envelope so the provider remains runnable without pretending opaque bytes are
decoded canonical measurements. `ComputeRunService` preserves the same
artifact/template/plan/result contract and forwards an explicit project
context material name only as a provider hint.

## Scientific boundary

Without a material hint, generic peak metrics remain available and polymer
library assignments are not fabricated. Solid-state 13C Xc remains gated by
explicit crystalline/amorphous phase support. Existing NMR provider algorithms
were not rewritten.

## Verification

- Focused NMR/converter/ComputeRun matrix: `77 passed, 3 skipped`.
- Structured verifier: passed, including existing quality gates.
- No raw data, generated evidence packages, or pre-existing runtime artifacts
  were modified.

## Follow-up

Run the six-sample replay through the unified route, then finish GUI gallery
consumption, cross-technology package handoff, ARS input consistency, and the
release-readiness ledger. Human review remains required for scientific claims.
