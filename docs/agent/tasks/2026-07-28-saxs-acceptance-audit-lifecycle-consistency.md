---
kind: task
status: completed
date: 2026-07-28
title: Refresh SAXS scientific acceptance audit after final validation
---

# SAXS scientific acceptance audit lifecycle consistency

## Goal

Ensure an already-attached SAXS `scientific_acceptance_audit` reflects the
final SAXS validation state after the existing validation/contract publication
hook completes.

## Evidence baseline

The temperature acceptance checkpoint `02cbc42` exposed that the shared
pipeline stores `get_parameters()` before post-analysis validation. On the real
PA6 temperature run, final `result.validation_passed` is `False`, while the
cached audit can retain the earlier validation snapshot. The audit status still
degrades from existing evidence, but the validation field is internally stale.

## Non-goals

- Do not change `BaseEngine` ordering or any non-SAXS technique.
- Do not change Guinier fitting, q windows, Q*, masks, physical metrics,
  thresholds, quality levels, rescue, AI, publication roles, or export policy.
- Do not create an audit for static SAXS results that do not already carry one.
- Do not edit real data, generated outputs, `current-state.md`, or scratch.

## Affected boundaries

- `polynexus/core/saxs.py`: existing SAXS validation hook only;
- `tests/test_saxs_acceptance_audit_lifecycle.py`: regression for cached
  temperature audit refresh and optional real PA6 evidence;
- task/spec/plan/acceptance/memory records: durable evidence only.

## Implementation plan

1. Add a RED regression that builds a pre-validation temperature parameter
   payload, raises an existing SAXS validation error, and proves the cached
   audit is refreshed to the final `False` state.
2. In `SAXSEngine._validate_results()`, after the existing
   `publish_saxs_result_contract()` call, refresh only when the current
   parameters already contain `scientific_acceptance_audit`.
3. Run focused synthetic/real tests, the exact SAXS matrix, structured verifier,
   diff check, and an explicit allowlist checkpoint.

## Acceptance criteria

- [x] An existing temperature audit's `automated_validation_passed` equals the
  final `result.validation_passed` after `_validate_results()`.
- [x] A final validation failure remains `diagnostic_only` and retains existing
  evidence/reason codes; no new scientific gate is added.
- [x] Existing strain audit refreshes through the same SAXS hook, while static
  payloads without an audit remain unchanged.
- [x] The audit remains detached and strict-JSON serializable.
- [x] TDD RED/GREEN, exact SAXS matrix, structured verifier, diff check, and
  explicit allowlist checkpoint are recorded.

## Verification evidence

- TDD RED: `2 failed`; both failures showed final validation `False` while the
  cached audit still reported `automated_validation_passed=True`.
- Focused GREEN: `2 passed in 14.97s`, including the real five-frame PA6
  temperature run.
- Exact SAXS matrix: `439 passed, 6 warnings in 83.10s`. Warnings are the
  existing Arial CJK glyph warnings and existing EDF geometry-default warnings.
- Real PA6 evidence: final `result.validation_passed=False` and audit
  `automated_validation_passed=False`, status `diagnostic_only`, with existing
  `guinier_sequence_no_valid_frames` retained.
- Structured verifier and `git diff --check` are recorded in the acceptance
  record before the explicit checkpoint.

## Verification

```powershell
python -m pytest -q tests/test_saxs_acceptance_audit_lifecycle.py -vv --basetemp C:\Temp\PolyNexus_saxs_audit_lifecycle_redgreen
python -m pytest -q (Get-ChildItem -Path tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName) --basetemp C:\Temp\PolyNexus_saxs_audit_lifecycle_matrix
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-acceptance-audit-lifecycle-consistency.md --changed --types
git diff --check
```

Pytest storage is external. A timeout or historical no-output process is not a
pass.

## Explicit changed-file allowlist

- `polynexus/core/saxs.py`
- `tests/test_saxs_acceptance_audit_lifecycle.py`
- this task card
- `docs/superpowers/specs/2026-07-28-saxs-acceptance-audit-lifecycle-consistency-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-acceptance-audit-lifecycle-consistency.md`
- `docs/acceptance/2026-07-28-saxs-acceptance-audit-lifecycle-consistency.md`
- `docs/agent/memory/active-work.md`

## Checkpoint

The checkpoint is created after the verification record is finalized.
No push, merge, publication approval, or real-data write is authorized.
