---
task_id: 2026-09-02-results-candidate-promotion-semantics
kind: scientific
status: implementation_complete_review_required
date: 2026-09-02
title: Separate computed metrics from publication promotion
---

# Results-candidate promotion semantics

Date: 2026-09-02
Status: implementation complete, review required

## Goal

Allow successfully computed scalar metrics from a valid shared `ComputeRun` to
be exposed to ARS as provisional Results candidates while preserving the
separate human/scientific review gate. Only unavailable, structurally invalid,
or explicitly diagnostic observations remain Discussion/Diagnostic-only.

## Non-goals

- Do not change provider algorithms, raw data, units, or numerical values.
- Do not turn `ComputationState.promotion` into an automatic scientific
  approval; the shared platform may remain `diagnostic_only` until review.
- Do not remove the review ledger or allow ARS to claim publication readiness.
- Do not touch pre-existing runtime artifacts or historical full-suite failures.

## Affected boundaries

- `polynexus/core/project_workflow/writing_metrics.py`
- `polynexus/core/project_workflow/ars_handoff.py` (consumer contract only)
- Project evidence package and manuscript planning consumers

## Shared objects and entry points

- Objects: run, evidence package, export.
- AI/Codex/CLI: reads the shared metric projection and ARS handoff.
- GUI: reads the same evidence/package DTOs; no GUI-specific eligibility logic
  changes.
- Cross-entry rule: the producer is the shared writing-metric projection; all
  project, ARS, CLI, and GUI consumers must see the same candidate IDs.

## Implementation plan

1. Add a regression test for a computed run whose promotion remains pending.
2. Stop applying run-level diagnostic promotion as a blanket metric downgrade.
3. Keep unavailable, malformed, method-sensitivity, and explicit provider
   diagnostic observations out of Results candidates.
4. Verify package and ARS projections, update durable acceptance evidence, and
   create an allowlisted checkpoint.

## Acceptance criteria

- [x] A computed, numeric metric from a valid canonical `ComputeRun` is a
  `results_candidate` even when run-level promotion is `diagnostic_only`.
- [x] Metric warnings and provenance remain attached as reason codes; they do
  not silently erase a computed observation.
- [x] Explicitly unavailable, non-computed, malformed, method-sensitivity, and
  provider-diagnostic observations remain outside Results candidates.
- [x] `ars-writing-input.json` exposes provisional candidates while retaining
  `review_status: pending` and human-review entries.
- [x] Existing fail-closed parsing and cross-entry provenance checks remain
  green.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_project_writing_metrics.py tests/test_project_ars_writing_handoff.py tests/test_project_workflow_package.py tests/test_capability_evidence_projection.py
python scripts/verify.py --task docs/agent/tasks/2026-09-02-results-candidate-promotion-semantics.md --changed --types
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "fix(ars): separate computed metrics from review promotion" `
  --files polynexus/core/project_workflow/writing_metrics.py tests/test_project_writing_metrics.py tests/test_project_workflow_package.py docs/agent/tasks/2026-09-02-results-candidate-promotion-semantics.md docs/acceptance/2026-09-02-results-candidate-promotion-semantics.md
```

## Completion evidence

- Focused tests: 55 passed.
- Task verifier: selected checks passed (quality 313, preprocessing 157).
- Real PA6 v002 replay: completed; 380 Results candidates, 158 Discussion/
  Diagnostic observations, 4 pending evidence reviews.
- Known limitations: publication promotion and historical full-suite failures
  remain outside this task.
