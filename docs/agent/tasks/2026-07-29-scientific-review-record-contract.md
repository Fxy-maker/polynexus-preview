---
task_id: 2026-07-29-scientific-review-record-contract
kind: schema
status: planned
date: 2026-07-29
title: Add shared scientific review record contract
---

# Shared scientific review record contract

## Goal

Implement the technique-neutral JSON-safe review record and fail-closed
promotion gate described by the approved scientific-release design.

## Non-goals

- Do not choose IR vendor semantics, NMR assignment truth, Joint precedence, or
  final release approval.
- Do not attach an unapproved record to production runs or promote existing
  diagnostic/assignment-limited figures.
- Do not modify real data, generated outputs, scratch directories, or unrelated
  SAXS worktree changes.

## Affected boundaries

- New core review record and promotion gate.
- Public `polynexus.core` exports.
- Focused regression and structured verification evidence.
- Durable acceptance and memory records.

## Design and plan

- Design: `docs/superpowers/specs/2026-07-29-scientific-release-confirmation-boundaries-design.md`
- Plan: `docs/superpowers/plans/2026-07-29-scientific-review-record-contract.md`
- Parent scientific task: `docs/agent/tasks/2026-07-29-scientific-release-confirmation-boundaries.md`

## Implementation plan

1. Write RED tests for immutable records, JSON-safe serialization, required
   scope fields, and fail-closed promotion reasons.
2. Implement the shared record, validator, promotion decision, and public core
   exports without changing technique engines.
3. Run the focused test, structured verifier, boundary audit, and diff check.
4. Update acceptance/memory evidence and create one explicit allowlist
   checkpoint.

## Acceptance criteria

- [ ] Valid pending and accepted records round-trip through JSON with no NaN or
      infinity values.
- [ ] Unknown scopes/statuses and incomplete non-pending records are rejected.
- [ ] Missing, pending, conditional, rejected, stale, wrong-scope, and
      source-mismatched records all fail closed with stable reasons.
- [ ] Only an accepted, complete, scope-matching, source-matching record can
      return an allowed promotion decision.
- [ ] No technique-specific scientific result or publication role changes in
      this slice.
- [ ] The atomic checkpoint contains only the explicit changed-file allowlist.

## Verification

```powershell
python -m pytest -q tests/test_scientific_review.py
python scripts/verify.py --task docs/agent/tasks/2026-07-29-scientific-review-record-contract.md --changed --types
python scripts/boundary_audit.py --root D:\PolyNexus --json
git diff --check
```

## Explicit changed-file allowlist

- `polynexus/core/scientific_review.py`
- `polynexus/core/__init__.py`
- `tests/test_scientific_review.py`
- `docs/agent/tasks/2026-07-29-scientific-review-record-contract.md`
- `docs/acceptance/2026-07-29-scientific-review-record-contract.md`
- `docs/agent/memory/active-work.md`
