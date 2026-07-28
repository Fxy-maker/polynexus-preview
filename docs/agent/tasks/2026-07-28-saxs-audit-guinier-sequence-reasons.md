---
kind: task
status: completed
date: 2026-07-28
title: Include existing Guinier sequence reasons in SAXS acceptance audit
---

# SAXS acceptance audit Guinier sequence evidence

## Goal

Make the existing temperature Guinier sequence level and reason codes visible
inside the read-only `scientific_acceptance_audit` summary.

## Evidence baseline

The real PA6 temperature run already emits
`guinier_sequence_evidence.level="Unusable"` and
`guinier_sequence_no_valid_frames`. The current audit builder collects other
existing quality reports and metrics but omits this sequence mapping, forcing a
consumer to join two separate parameter fields to understand the boundary.

## Non-goals

- Do not change Guinier fitting, q-window selection, qRg rules, continuity
  logic, or any physical threshold.
- Do not interpolate, repair, reorder, fabricate, or rescue frames.
- Do not change audit status semantics, publication roles, AI behavior, or
  quality-level classification.
- Do not edit `current-state.md`, real data, generated outputs, or scratch.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`: read-only audit
  traversal of existing sequence evidence;
- `tests/test_saxs_audit_guinier_sequence_reasons.py`: pure and real-data
  regressions;
- task/spec/plan/acceptance and `docs/agent/memory/active-work.md` records.

## Implementation plan

1. Add RED tests asserting the audit exposes the existing sequence level and
   `guinier_sequence_no_valid_frames` reason.
2. Extend the existing recursive audit traversal with one allowlisted
   `guinier_sequence_evidence` mapping reader; preserve all existing outputs.
3. Run focused/real tests, exact SAXS matrix, structured verifier, diff check,
   and create one explicit allowlist checkpoint.

## Acceptance criteria

- [x] Audit `evidence_levels` includes the existing
  `guinier_sequence_evidence` level when present.
- [x] Existing sequence `reason_codes` are retained in audit `reason_codes`.
- [x] No sequence array, frame ordering, metric, status, threshold, or
  publication decision changes.
- [x] Pure and real PA6 audits remain strict-JSON serializable.
- [x] TDD RED/GREEN, SAXS matrix, verifier, diff, and checkpoint evidence are
  recorded.

## Verification evidence

- TDD RED: `2 failed` with the expected missing
  `evidence_levels["guinier_sequence_evidence"]` key.
- Focused GREEN: `2 passed in 15.35s`, including the real five-frame PA6 run.
- Exact SAXS matrix: `441 passed, 6 warnings in 88.00s`. Warnings remain the
  existing Arial CJK glyph and EDF geometry-default warnings.
- Real PA6 audit now reports the existing sequence level `Unusable` and reason
  `guinier_sequence_no_valid_frames`; no source frame or sequence field was
  modified.
- Structured verifier and `git diff --check` are recorded in the acceptance
  record before checkpoint creation.

## Verification

```powershell
python -m pytest -q tests/test_saxs_audit_guinier_sequence_reasons.py -vv --basetemp C:\Temp\PolyNexus_saxs_audit_guinier_redgreen
python -m pytest -q (Get-ChildItem -Path tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName) --basetemp C:\Temp\PolyNexus_saxs_audit_guinier_matrix
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-audit-guinier-sequence-reasons.md --changed --types
git diff --check
```

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `tests/test_saxs_audit_guinier_sequence_reasons.py`
- this task card
- `docs/superpowers/specs/2026-07-28-saxs-audit-guinier-sequence-reasons-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-audit-guinier-sequence-reasons.md`
- `docs/acceptance/2026-07-28-saxs-audit-guinier-sequence-reasons.md`
- `docs/agent/memory/active-work.md`

## Checkpoint

Create the checkpoint after current verification is recorded. No push,
merge, scientific approval, or real-data write is part of this task.
