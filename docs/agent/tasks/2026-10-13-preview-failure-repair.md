---
task_id: 2026-10-13-preview-failure-repair
kind: scientific
status: implementation_complete_review_required
date: 2026-10-13
title: Repair preview integration failures and make human review actionable
---

# Preview failure repair

## Goal

Resolve the 38 remaining integration failures, verify the full cumulative PR,
and document concrete scientific/architecture decisions for human review.

## Non-goals

- Promote diagnostic models to validated capabilities or invent material references.
- Change raw datasets, infer experiment grouping, merge the PR, or modify private mainline.
- Implement the proposed reference-evidence layer or an unrelated algorithm.

## Shared objects and entry points

CanonicalExperiment admission, AnalysisResult/ComputeRun, SAXS sequence metrics,
FigureDefinition/export profiles, and history DTOs are affected. Producers are
Core converters and SAXS providers; consumers are GUI workers/history/gallery,
CLI and Agent orchestrators, and shared figure publishing. Preserve the shared
contracts and verify each affected consumer.

## Affected boundaries

GUI display/selection/logging, figure export fixtures, canonical admission
fixtures, SAXS feature tracking and signed-input regression consumers,
Python 3.11 replay DTO construction, and Qt test lifecycle cleanup. No shared
result schema changes.

## Implementation plan

1. Reproduce/group failures and compare assertions with documented contracts.
2. Repair genuine defects; update obsolete fixtures only with contract evidence.
3. Run focused tests and full structured integration verification, including CI.
4. Record actionable human review, update durable memory, checkpoint explicit paths,
   and update the existing GitHub PR without merging.

## Acceptance criteria

- [x] All formerly failing nodes and surrounding regressions pass.
- [x] Full/type/boundary gates pass against the public preview base.
- [x] Review notes state current behavior, recommendations, and consequences.
- [x] Original workspace user changes remain untouched.

## Verification

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-10-13-preview-failure-repair.md --base preview/research-preview-v0.1 --changed --types --full --boundary
```

Before changes, the previous failure replay recorded 38 failed, 7 passed, 5
skipped. Existing failing cases provide the initial regression tests. Extend
coverage when the repair exposes a missing boundary case. Record final commands
and evidence in the acceptance notes.

## Completion evidence

Original failure nodes pass 38/38. Final integration verification passes
4995 tests with 50 external/optional skips and no failures, quality 313,
preprocessing 157, cumulative Ruff/compile, whitespace and boundary checks.
Standalone Pyright reports zero errors/warnings. The earlier transient Qt
construction failure, lifecycle cleanup and verified limits remain explicit
in `docs/acceptance/2026-10-13-preview-failure-repair.md`.
Concrete human review: `docs/acceptance/2026-10-13-preview-human-review.md`.
Checkpoint only the changed repair source/tests and these documentation/memory
paths; update existing public PR #1 without merging or touching private main.
