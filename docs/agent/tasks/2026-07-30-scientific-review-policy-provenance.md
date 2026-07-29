---
task_id: 2026-07-30-scientific-review-policy-provenance
kind: cross-module
status: completed
date: 2026-07-30
title: Preserve scientific review policy provenance
---

# Scientific review policy provenance

## Goal

Carry the existing reviewer `policy_version` from `ScientificReviewRecord`
through the shared decision snapshot and GUI presentation so Results, History,
and Export evidence can be audited against the policy that produced it.

## Non-goals

- Do not choose IR coordinate/ROI semantics, NMR assignment/Xc policy, Joint
  conflict precedence, or final release values.
- Do not change promotion rules, publication roles, numeric analysis, real data,
  generated outputs, or test-storage directories.
- Do not claim that a policy version is scientific approval by itself.

## Affected boundaries

- `polynexus/core/scientific_review.py` decision snapshot.
- `polynexus/gui/scientific_review_presentation.py` shared display adapter.
- Existing Results/History/Export consumers and their focused regressions.

## Implementation plan

1. Add RED assertions for snapshot and GUI preservation of `policy_version`.
2. Extend the shared snapshot and display adapter without changing promotion
   decisions or technique-specific semantics.
3. Run focused consumers, the structured verifier, and the diff check; record
   the exact evidence and create an explicit allowlist checkpoint.

## Acceptance criteria

- [x] A valid review snapshot preserves the source record's exact
      `policy_version`.
- [x] GUI review text exposes the same version when it is present.
- [x] Missing, invalid, stale, rejected, conditional, scope-mismatched, and
      source-mismatched decisions retain their existing fail-closed reasons.
- [x] No scientific result or publication role changes.
- [x] The checkpoint contains only the explicit changed-file allowlist.

## Design and plan

- Design boundary:
  `docs/superpowers/specs/2026-07-29-scientific-release-confirmation-boundaries-design.md`
- Implementation plan:
  `docs/superpowers/plans/2026-07-30-scientific-review-policy-provenance.md`

## Verification

```powershell
python -m pytest -q tests/test_scientific_review.py tests/test_scientific_review_presentation.py tests/test_results_table_service.py tests/test_export_context_service.py tests/test_history_table_service.py
python scripts/verify.py --task docs/agent/tasks/2026-07-30-scientific-review-policy-provenance.md --changed --types
git diff --check
```

## Explicit changed-file allowlist

- `polynexus/core/scientific_review.py`
- `polynexus/gui/scientific_review_presentation.py`
- `tests/test_scientific_review.py`
- `tests/test_scientific_review_presentation.py`
- `docs/agent/tasks/2026-07-30-scientific-review-policy-provenance.md`
- `docs/acceptance/2026-07-30-scientific-review-policy-provenance.md`
- `docs/superpowers/plans/2026-07-30-scientific-review-policy-provenance.md`
- `docs/agent/memory/active-work.md`
