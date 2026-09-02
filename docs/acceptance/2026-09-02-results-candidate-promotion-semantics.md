# Results-candidate promotion semantics

Date: 2026-09-02
Status: implementation complete, review required

## Outcome

The writing-metric projection no longer treats the shared run-level
`ComputationState.promotion = diagnostic_only` as a blanket downgrade. Numeric
metrics with a valid computed manifest are now exposed as provisional
`results_candidate` records. Explicit provider-capability observations,
method-sensitivity values, unavailable values, and malformed/non-computed rows
remain outside Results candidates.

Run/evidence review is still independent: the package remains
`review_required`, ARS `review_status` remains `pending`, and no publication or
scientific conclusion is auto-approved.

## Verification

- Focused matrix: **55 passed**
  (`test_project_writing_metrics.py`, `test_project_ars_writing_handoff.py`,
  `test_project_workflow_package.py`, `test_capability_evidence_projection.py`).
- Task verifier: **selected checks passed**, including quality **313**,
  preprocessing **157**, Ruff, compile, memory, and whitespace checks.
- Real PA6 close-loop replay using the existing four selected files completed
  successfully as package `pa6-first-ai-loop-v002-v001`.
- Replay handoff counts: **380** provisional Results candidates and **158**
  Discussion/Diagnostic observations across DSC/IR/SAXS/WAXS; **4** evidence
  items remain human-review pending.

## Human-review boundary

The candidate list means “available for ARS drafting and human selection”, not
“approved for publication”. Units/method metadata, provider applicability,
figure choice, and cross-technique claims still require scientific review.

## Untouched pre-existing workspace changes

The existing modified `polynexus/core/agent_workflow/service.py`, runtime files,
reference notes, and `tests/_tmp_phase3/` were intentionally left untouched.
Historical full-suite failures remain outside this task.
