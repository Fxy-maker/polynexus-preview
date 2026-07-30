---
task_id: 2026-07-30-project-release-decision
kind: release-readiness
status: completed
date: 2026-07-30
title: Add project-level release decision provenance
---

# Project-level release decision

## Goal

Persist reviewer-owned final release decisions at the SampleDB batch/project
boundary and expose them through the existing non-SAXS Results Workbench,
History, and Export provenance paths.

## Non-goals

- Do not fill IR, NMR, or Joint scientific values.
- Do not change analysis formulas, thresholds, figure roles, or promotion
  behavior.
- Do not touch SAXS code, tests, evidence, or temporary artifacts.
- Do not delete data, push, merge, or deploy.

## Affected boundaries

- `ScientificReviewRecord` release/status validation.
- Batch-scoped SampleDB persistence and latest-run hydration.
- Non-SAXS Results Workbench release action.
- History and Export release provenance presentation.
- Test-storage paths used by this task; SAXS and real datasets remain outside
  the changed-file and test allowlist.

## Implementation plan

1. Add release/status consistency validation and focused contract tests.
2. Add append-only batch release persistence and latest snapshot hydration.
3. Add the Results Workbench release dialog action and provenance projection.
4. Add shared History/Export display adapters and missing-state coverage.
5. Run focused non-SAXS tests, boundary audit, structured verification, and
   diff checks before creating the explicit checkpoint.

## Acceptance criteria

- [x] `ScientificReviewRecord(scope="release")` rejects a status/decision
      mismatch and accepts all three explicit decisions.
- [x] SampleDB stores validated release records append-only per `batch_id` and
      returns the newest snapshot without mutating older records.
- [x] Results Workbench opens a release-scoped dialog only for a persisted run
      with a valid batch target and saves the record transactionally.
- [x] Current Results, History restore, and Export context expose the same
      JSON-safe release snapshot and preserve `release_missing` when absent.
- [x] Focused non-SAXS tests, boundary audit, task verifier, and diff checks
      pass with exact command output recorded below.
- [x] A checkpoint is created with the explicit changed-file allowlist.

## Files in scope

- `polynexus/core/scientific_review.py`
- `polynexus/data/sample_db.py`
- `polynexus/gui/scientific_review_presentation.py`
- `polynexus/gui/scientific_review_dialog.py`
- `polynexus/gui/main_window_results_mixin.py`
- `polynexus/gui/main_window_history_mixin.py`
- `polynexus/gui/export_context_service.py`
- `polynexus/gui/i18n.py`
- focused tests for the files above
- this task's design, plan, acceptance, and memory entry

## Verification

```powershell
python -m pytest -q tests/test_scientific_review.py tests/test_scientific_review_workbench.py tests/test_sample_db.py
python -m pytest -q tests/test_export_context_service.py tests/test_main_window_history_mixin.py
python scripts/boundary_audit.py --root D:\PolyNexus --json
python scripts/verify.py --task docs/agent/tasks/2026-07-30-project-release-decision.md --changed --types
git diff --check
```

The verifier command above is the authoritative structured check for this
task. Test output must include exit code and exact pass/fail counts; a storage
or process cleanup error is recorded as a tool-level failure, not as a pass.

## Final evidence (2026-07-30)

- Focused matrix: `python -m pytest -p no:cacheprovider -q
  tests/test_scientific_review.py tests/test_scientific_review_workbench.py
  tests/test_sample_db.py tests/test_export_context_service.py
  tests/test_main_window_history_mixin.py` -> `61 passed in 1.53s`, exit 0.
- Boundary audit: `python scripts/boundary_audit.py --root D:\PolyNexus
  --json` -> JSON inventory emitted, exit 0; no boundary-audit failure was
  reported.
- Structured verifier: `python scripts/verify.py --task
  docs/agent/tasks/2026-07-30-project-release-decision.md --changed --types`
  -> task/memory checks passed; Ruff and compile passed; quality gate `291
  passed in 8.91s`; preprocessing gate `106 passed in 2.70s`; type baseline
  had no changed targets; whitespace passed; exit 0.
- Diff check: `git diff --check` over the explicit source/test allowlist ->
  exit 0.
- Storage: verification used `C:\PolyNexus-test-runs` with cache provider
  disabled. No SAXS test or real dataset was included in this task.

## Known boundary

The software can capture and audit a reviewer decision, but it cannot supply
the missing IR vendor payload, NMR assignment truth set, Joint conflict policy,
or the human decision itself. Until a reviewer enters those values, release
promotion remains fail-closed.
