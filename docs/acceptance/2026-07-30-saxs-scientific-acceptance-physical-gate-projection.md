# SAXS scientific acceptance physical gate projection

Status: implementation complete for this scoped contract; the shared quality
gate has two unrelated parallel-NMR failures. The local allowlist checkpoint
is the final handoff action.

This slice makes `scientific_acceptance_audit` traceable to the physical checks
already present in SAXS metric evidence. It exposes detached
`physical_gate_evidence` and `method_gate_status` fields, records explicit
method-gate failures, and keeps an applicable metric with an unknown gate at
least `review_required`. It does not add thresholds, recalculate metrics,
change quality levels, rescue data, call AI, or change publication decisions.

Evidence:

- TDD RED: `3 failed, 1 passed`; the failures were the expected missing output
  fields.
- Final focused acceptance/audit batch: `41 passed, 2 warnings` in `334.82s`.
- Fresh complete SAXS matrix: `621 passed, 8 warnings` in `567.71s` with exit
  code `0`. Warnings are the existing locale deprecation, Arial CJK glyph,
  EDF geometry-default, and pytest-cache warnings.
- Task/memory checks, Ruff, compile, and type baseline completed successfully
  inside the structured verifier. The shared quality gate reported `288
  passed, 2 failed, 3 warnings`; both failures are existing NMR history-table
  locale expectations from parallel uncommitted work, and no NMR file is in
  this task's allowlist.
- `git diff --check` passed.
- Test-storage report and dry-run clean remained non-destructive: `80`
  artifacts, `6` eligible, `removed=0`; no `test_storage.py --apply` was run.

The existing audit remains read-only and strict-JSON-safe. Full software
full/boundary release acceptance, raw detector geometry/mask scientific review,
AI rescue execution, and publication authorization remain open outside this
task.

Explicit changed-file allowlist:

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `tests/test_saxs_audit_physical_gate_projection.py`
- `docs/agent/tasks/2026-07-30-saxs-scientific-acceptance-physical-gate-projection.md`
- `docs/superpowers/specs/2026-07-30-saxs-scientific-acceptance-physical-gate-projection-design.md`
- `docs/superpowers/plans/2026-07-30-saxs-scientific-acceptance-physical-gate-projection.md`
- `docs/acceptance/2026-07-30-saxs-scientific-acceptance-physical-gate-projection.md`

No push, merge, data deletion, or publication approval is included.
