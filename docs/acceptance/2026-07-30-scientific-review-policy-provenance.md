# Scientific review policy provenance

Status: implementation and focused consumer verification passed; scientific
values and final release approval remain open.

## Change

`review_decision_snapshot()` now carries the existing review record's exact
`policy_version`. The shared GUI adapter exposes that value as `policy=...`
when present, while preserving status, reason, source, scope, and fail-closed
behavior. No IR/NMR/Joint semantic value, threshold, publication role, or
numeric result changed.

## Verification

Focused Results/History/Export consumer matrix:

```text
61 passed in 0.46s
```

Task-scoped verification passed with quality `290`, preprocessing `106`,
Ruff, compile, type-baseline, memory/task, and whitespace checks all green.
`git diff --check` also passed. This slice is provenance metadata only; it does
not create a reviewer decision or promote a scientific result.

## Remaining gates

Reviewer-owned IR coordinate/ROI semantics, NMR solid-C assignment/Xc policy,
Joint conflict precedence, restarted-GUI all-mode human review, and final
release authorization remain open.
