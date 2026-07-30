---
task_id: 2026-07-30-joint-conclusion-policy
kind: scientific-semantics
status: completed
date: 2026-07-30
title: Project a reviewer-owned Joint conclusion class
---

# Joint conclusion policy

## Goal

Expose an auditable Joint conclusion class from existing review status and
validation severity without deciding scientific conflict precedence in code.

## Non-goals

- Do not change Joint formulas, tolerances, evidence weights, or severity rules.
- Do not interpret reviewer policy text or choose DSC/SAXS/WAXS precedence.
- Do not change Figure/Manifest roles or the existing scientific-review gate.
- Do not touch SAXS code, tests, real datasets, or temporary artifacts.

## Affected boundaries

- `polynexus/core/joint/conclusion.py`: pure JSON-safe conclusion classifier.
- `polynexus/core/joint/dataset.py`: report and AI-context projection.
- `polynexus/core/joint/__init__.py`: public package export.
- Joint dataset tests and this task's durable design/acceptance/memory records.

## Implementation plan

1. Add RED tests for missing, rejected, conditional, blocked, and accepted
   Joint conclusion states.
2. Implement status/severity classification while preserving reviewer policy
   text and existing validation behavior.
3. Attach the projection to the Joint report and run the non-SAXS regression
   matrix.
4. Run structured verification, boundary audit, diff checks, and create one
   explicit allowlist checkpoint.

## Acceptance criteria

- [x] Missing/invalid/source-mismatched Joint review is `review_required` and
      `allowed=false`.
- [x] Rejected review is `rejected`; accepted review with existing ERROR is
      `blocked`; accepted review with existing WARN is `conditional`.
- [x] Accepted review with no existing issues is `accepted` and only this
      class has `allowed=true`.
- [x] Reviewer policy strings and record metadata are preserved exactly as
      JSON-safe provenance and are not evaluated by the classifier.
- [x] Existing Joint report, figure, lifecycle, and provenance behavior stays
      green.
- [x] Task verifier, boundary audit, diff check, and explicit allowlist
      checkpoint are recorded below.

## Verification

```powershell
$env:POLYNEXUS_TEST_ROOT='C:\PolyNexus-test-runs'; $env:POLYNEXUS_TEST_RETENTION='review'; python -m pytest -p no:cacheprovider -q tests/test_joint_hub_dataset.py tests/test_joint_real_data_lifecycle.py tests/test_joint_figure_provider.py tests/test_joint_lifecycle_closure.py tests/test_nmr_joint_provenance_matrix.py
python scripts/boundary_audit.py --root D:\PolyNexus --json
python scripts/verify.py --task docs/agent/tasks/2026-07-30-joint-conclusion-policy.md --changed --types
git diff --check
```

## Known boundary

The projection makes the reviewer-owned policy consumable but cannot supply
the scientific values, assign NMR peaks, resolve a real conflict, or perform
human release approval. Missing reviewer input remains fail-closed.

## Explicit changed-file allowlist

- `polynexus/core/joint/conclusion.py`
- `polynexus/core/joint/__init__.py`
- `polynexus/core/joint/dataset.py`
- `tests/test_joint_hub_dataset.py`
- this task's design, plan, acceptance, and memory entry

## Final evidence (2026-07-30)

- TDD RED: collection failed with `ModuleNotFoundError` for the intentionally
  absent `polynexus.core.joint.conclusion` module.
- Focused RED/GREEN matrix: `6 passed, 7 deselected in 0.38s`, exit 0.
- Joint/NMR provenance/figure/lifecycle matrix: `24 passed in 44.79s`, exit 0.
- Boundary audit: `python scripts/boundary_audit.py --root D:\PolyNexus
  --json` emitted its inventory and exited 0.
- Structured verifier: exit 0; quality gate `291 passed in 8.96s`,
  preprocessing gate `106 passed in 2.71s`; task/memory, Ruff, compile,
  type-baseline, and whitespace checks passed.
- `git diff --check`: exit 0 before checkpoint creation.
- Tests used `C:\PolyNexus-test-runs` with review retention and disabled cache
  provider. SAXS, real datasets, and temporary test paths are outside scope.
