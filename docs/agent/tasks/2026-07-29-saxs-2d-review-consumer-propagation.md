---
task_id: 2026-07-29-saxs-2d-review-consumer-propagation
kind: cross-module
status: completed
---

# SAXS 2D Reviewer Evidence Consumer Propagation

## Goal

Propagate the existing reviewer-owned `saxs.2d` evidence from configured SAXS
frames into the result contract, authoritative `quality_evidence.json`, and
persisted Figure document/V2 sidecar so existing Workbench, History, and Export
consumers can display one consistent snapshot.

## Non-goals

- No new scientific fields, thresholds, quality levels, physical gates, or
  publication-role changes.
- No interpolation, frame fabrication, automatic rescue, AI call, or confirmed
  rerun.
- No raw detector arrays or raw q/I in reviewer evidence.
- No edits to real datasets, generated outputs, secrets, or parallel files.

## Affected boundaries

- `polynexus/core/saxs_engine/figure_evidence.py`: detached config-to-frame
  reviewer projection.
- `polynexus/core/saxs_result_contract.py`: result parameter snapshot.
- `polynexus/core/saxs_export_bundle.py`: authoritative bundle snapshot.
- Existing FigurePipeline/V2 serialization and generic GUI presentation
  consumers, covered by regression tests without a new GUI contract.
- Focused regression coverage in
  `tests/test_saxs_2d_review_consumer_propagation.py`.

## Acceptance criteria

- [x] Valid matching `saxs.2d` evidence reaches result parameters and
  `quality_evidence.json` as detached strict JSON.
- [x] Figure document and V2 sidecar preserve the same reviewer evidence;
  manifest readiness and publication role are unchanged.
- [x] Existing Workbench, History, and Export adapters display the snapshot's
  identity/status without recomputing SAXS state.
- [x] Configured malformed, wrong-scope, partial-source, and source-mismatch
  cases remain fail-closed in persisted consumers; an empty optional review
  stays absent from generic non-gated SAXS consumers while Figure evidence
  retains its explicit `review_missing` snapshot.
- [x] Existing 1D review behavior and all SAXS physical/quality gates remain
  unchanged.

## Implementation plan

1. Write consumer-boundary RED tests for result, bundle, Figure persistence,
   and generic presentation.
2. Add one adapter that delegates to the existing review contract and source
   matching, returning only detached evidence.
3. Publish that adapter's snapshot in result parameters and bundle quality
   evidence.
4. Verify FigurePipeline/V2 sidecar and existing GUI consumers reuse the same
   snapshot.
5. Run focused, structured, exact-SAXS, diff, and storage dry-run checks, then
   create one explicit-allowlist checkpoint.

## Verification

The task will record the actual RED/GREEN results, adjacent consumer matrix,
task-scoped verifier, exact SAXS matrix, `git diff --check`, storage report and
non-destructive clean output, and the final explicit-allowlist checkpoint.

Structured verification command:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-2d-review-consumer-propagation.md --changed --types
```

## Implementation status

- [x] TDD RED: `4 failed`; failures were the missing result, authoritative
  bundle, V2 sidecar, and partial-source reviewer snapshots.
- [x] GREEN: focused consumer/persistence tests `4 passed`.
- [x] Adjacent 2D/1D/Figure/bundle/Workbench/scientific-review matrix:
  `70 passed in 3.17s`, exit code `0`.
- [x] Independent broader adjacent consumer recheck: `160 passed in 10.00s`,
  exit code `0`.
- [x] Added only a detached projection adapter and result/bundle handoff; no
  algorithm, quality, physical, AI, rescue, or publication behavior changed.
- [x] Task-scoped verifier passed with quality `290` and preprocessing `106`;
  Ruff, compile, memory, type-baseline, and whitespace checks were green. The
  authoritative independent shared recheck of the exact SAXS matrix was
  `588 passed, 6 warnings in 594.35s`, exit code `0` (the earlier local run
  was `588 passed, 6 warnings in 591.42s`, exit code `0`). Storage
  report/clean dry-run was `46 artifacts`, `eligible_bytes=0`, `removed=0`;
  no deletion was performed. A unique explicit-allowlist reconciliation
  checkpoint is recorded after this final evidence update.

## Scientific boundary

The reviewer record is evidence only. Existing SAXS physical indicators,
quality levels, validation gates, and publication eligibility remain the final
decision authorities. An accepted reviewer record does not promote a
Diagnostic/Unusable result or enable rescue.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/figure_evidence.py`
- `polynexus/core/saxs_result_contract.py`
- `polynexus/core/saxs_export_bundle.py`
- `tests/test_saxs_2d_review_consumer_propagation.py`
- `docs/superpowers/specs/2026-07-29-saxs-2d-review-consumer-propagation-design.md`
- `docs/superpowers/plans/2026-07-29-saxs-2d-review-consumer-propagation.md`
- `docs/agent/tasks/2026-07-29-saxs-2d-review-consumer-propagation.md`
- `docs/acceptance/2026-07-29-saxs-2d-review-consumer-propagation.md`
- `docs/agent/memory/active-work.md`
