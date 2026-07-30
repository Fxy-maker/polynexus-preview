---
kind: task
status: completed
date: 2026-07-30
title: Project existing SAXS physical gate evidence into scientific acceptance audit
---

# SAXS scientific acceptance physical gate projection

## Goal

Make the existing `scientific_acceptance_audit` directly traceable to the
physical checks already attached to SAXS metric evidence, without changing any
scientific calculation or acceptance threshold.

## Non-goals

- Do not add or change q windows, Q*, Guinier, Porod, Kratky, invariant,
  lamellar, detector, mask, or geometry thresholds.
- Do not recalculate a metric, infer a missing physical check, interpolate a
  frame, rescue data, call an AI model, or change publication roles.
- Do not alter `MetricEvidence`, `MetricEvidenceSummary`, metric levels, or
  existing validation behavior.
- Do not modify GUI consumers, exports, real datasets, generated outputs,
  `docs/agent/memory/current-state.md`, or scratch directories.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`: read-only audit
  projection of existing metric evidence.
- `tests/test_saxs_audit_physical_gate_projection.py`: focused contract and
  fail-closed regression coverage.
- This task card, its design spec, and implementation plan.

## Implementation plan

1. Add focused RED tests for passing, failed, and unknown existing method-gate
   evidence, including detached input and strict JSON serialization.
2. Extend the existing recursive audit inspection to copy `physical_checks`
   and expose explicit or unknown `method_gate_passed` states.
3. Run the focused suite, the complete SAXS matrix, the structured verifier,
   and `git diff --check` before recording the acceptance evidence.
4. Create one local checkpoint using only the explicit changed-file allowlist.

## Contract

The audit adds `physical_gate_evidence`, keyed by the existing audit labels
such as `metric:guinier`. Each value is a list of strict-JSON-safe copies of
the supplied `physical_checks` mapping. When a supplied mapping contains
`method_gate_passed`, the audit also records that exact value in a
`method_gate_status` list for the same label. Values are copied and never
used to recompute a metric.

For an evidence node with `applicable=True` and no explicit
`method_gate_passed`, the audit records `method_gate_not_assessed`. A false
method gate records `method_gate_failed`. The existing audit status logic
remains authoritative: an unknown gate is at least `review_required` when no
stronger existing blocker applies. These reasons never alter the source
evidence level or any publication decision. Nodes without metric evidence keep
the existing audit behavior.

## Acceptance criteria

- [x] A passing existing method gate is visible in the audit with its physical
  checks and `method_gate_status=True`.
- [x] A false existing method gate is visible and contributes
  `method_gate_failed` without changing the input metric payload.
- [x] An applicable metric without an explicit method gate is visible as
  `method_gate_not_assessed`, is not treated as passed, and remains at least
  `review_required` when no stronger existing blocker applies.
- [x] Existing level, reason, provenance, validation, publication, and
  `publication_decision_changed=False` fields retain their current semantics.
- [x] Audit output remains detached and strict-JSON serializable with
  `json.dumps(..., allow_nan=False)`.
- [x] TDD RED/GREEN, focused tests, exact SAXS matrix, structured verifier,
  `git diff --check`, and an explicit changed-file checkpoint are recorded.

## Verification

```powershell
python -m pytest -q tests/test_saxs_audit_physical_gate_projection.py -vv --basetemp D:\PolyNexus_saxs_physical_gate_projection
python -m pytest -q (Get-ChildItem -Path tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName) --basetemp D:\PolyNexus_saxs_physical_gate_projection_saxs_matrix
python scripts/verify.py --task docs/agent/tasks/2026-07-30-saxs-scientific-acceptance-physical-gate-projection.md --changed --types
git diff --check
```

Test storage remains external. A timeout, process exit without a pytest
summary, or a historical run is not a pass. `test_storage.py --apply` is not
part of this task.

## Verification evidence

- TDD RED: `3 failed, 1 passed`; failures were the expected missing audit
  projection keys.
- Focused final audit/acceptance batch: `41 passed, 2 warnings` in `334.82s`.
- Fresh complete SAXS matrix: `621 passed, 8 warnings` in `567.71s`.
- `git diff --check`: passed.
- Structured verifier task check, memory check, Ruff, compile, and type
  baseline passed. Its shared quality gate reported `288 passed, 2 failed,
  3 warnings`; both failures are pre-existing parallel NMR history-table
  expectations for English scientific-review labels while the parallel NMR
  implementation emits Chinese labels. No NMR file is in this task allowlist.
- Test-storage report and dry-run clean were non-destructive: `80` artifacts,
  `6` eligible, `removed=0`; no `--apply` was run.

The verifier limitation is recorded rather than treated as a full repository
pass. Full/boundary release acceptance and human scientific review remain
outside this atomic task.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `tests/test_saxs_audit_physical_gate_projection.py`
- `docs/agent/tasks/2026-07-30-saxs-scientific-acceptance-physical-gate-projection.md`
- `docs/superpowers/specs/2026-07-30-saxs-scientific-acceptance-physical-gate-projection-design.md`
- `docs/superpowers/plans/2026-07-30-saxs-scientific-acceptance-physical-gate-projection.md`
- `docs/acceptance/2026-07-30-saxs-scientific-acceptance-physical-gate-projection.md`

## Checkpoint

The checkpoint is created only after the verification evidence and acceptance
record are finalized. It is local-only: no push, merge, publication approval,
or data deletion is authorized.
