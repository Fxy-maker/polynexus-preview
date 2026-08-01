# SAXS real boundary after AI transport design

## Purpose

This verification slice refreshes current-head evidence for real SAXS data
after the AI summary-context parent-review transport. It consumes existing
analysis outputs and existing acceptance gates; it does not add scientific
interpretation.

## Evidence contract

The method-evidence replay is authoritative for whether the existing
`metric_evidence` mapping survives the real Static, Temperature, and Strain
paths into final parameters, Figure/Manifest provenance, and
`quality_evidence.json`. The replay must remain strict JSON and detached.

The PAD8 boundary is authoritative only for the existing software-side
classification. `validation_passed=True` may coexist with
`scientific_acceptance_audit.status=diagnostic_only`, unavailable geometry or
mask validity, and false publication flags. No test result may upgrade those
fields.

The lifecycle selector is authoritative for current shared software plumbing
through Static, Temperature, and Strain. It is not a substitute for an
instrument-aware review of calibration, masking, beam center, orientation, or
physical meaning.

## Failure classification

- Complete pytest summary plus exit code `0`: automated evidence pass.
- Complete summary with failures: automated evidence failure, recorded as-is.
- Timeout, setup error, crash, permission error, disk error, or no final
  summary: incomplete evidence, never a pass.
- Storage report/clean: dry-run inventory only; `removed=0` is required because
  this task does not authorize apply.

## Scope and isolation

The only changed files are the task's spec, plan, task card, and acceptance
record. Existing real fixtures are read-only. Test output uses external D:
basetemps selected per command. Parallel memory, scratch, and GUI/release
changes are intentionally excluded.
