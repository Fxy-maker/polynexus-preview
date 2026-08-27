---
task_id: 2026-08-28-release-failure-ledger
kind: structured
status: implementation_complete_review_required
date: 2026-08-28
title: Record full-suite release boundary and historical failures
---

# Record full-suite release boundary and historical failures

## Goal

Record a fresh full-boundary verification result and separate historical GUI,
figure, IR bridge, and SAXS failures from the newly completed shared-template
work.

## Non-goals

- Do not weaken tests, quality gates, scientific eligibility, or raw-data rules.
- Do not claim release-green while the listed failures remain unresolved.

## Affected boundaries

- `docs/acceptance/2026-08-28-full-suite-release-boundary.md`
- `docs/agent/memory/active-work.md`

## Acceptance criteria

- [x] Fresh full-suite counts and failed test names are recorded.
- [x] Passed focused gates for the current tasks are recorded separately.
- [x] Remaining human/scientific and historical release boundaries are explicit.

## Implementation plan

1. Run the full boundary verifier and capture exact counts.
2. Classify failures as historical/non-goal versus current-task regressions.
3. Update durable acceptance and memory records without changing source behavior.

## Verification

```powershell
python scripts/verify.py --changed --types --full --boundary
git diff --check
```

## Completion evidence

- Fresh full suite: **4197 passed, 39 failed, 25 skipped**.
- Current focused gates remain green; release-wide status is review-required.
