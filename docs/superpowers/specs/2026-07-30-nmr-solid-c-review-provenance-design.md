# NMR Solid-C Review Provenance Design

## Goal

Make the existing NMR solid-C evidence boundary legible in Results without
turning a diagnostic assignment into a scientific conclusion.

## Design

The NMR evidence builder copies the already computed `assignment_source` into
`feature_evidence.assignment_evidence`. The shared review formatter then emits
assignment readiness, source, axis source/units/calibration, and an Xc gate.
The gate is `allowed` only when evidence says the assignment is supported and
the structure is paper-conclusion-ready; otherwise it is `blocked` with the
existing evidence reason. The GUI receives this as `nmr_support_text` and only
renders it.

For the supplied solid-C files the expected state is `generic_region`,
`default_range`, `ppm`, `false`, and `phase_assignment_limited`. These are
provenance values, not newly inferred assignments. No reviewer record is
created by the route test.

## Failure behavior

Absent NMR evidence leaves the panel row empty. A missing or unsupported
assignment cannot accidentally become an allowed Xc conclusion because the
gate requires both the explicit readiness permission and
`paper_conclusion_ready=true`.
