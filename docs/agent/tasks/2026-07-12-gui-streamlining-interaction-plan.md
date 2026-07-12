# Agent Task

## Goal

Write the final GUI streamlining interaction plan and an explicit retention,
contextual-ownership, deferment, and removal checklist before any GUI code is
changed.

## Non-goals

- Do not modify GUI code or delete buttons in this task.
- Do not remove scientific modules, result evidence, history, sample workflows,
  figure recovery, or export contracts.
- Do not change schemas, persistence, manifest behavior, or scientific logic.
- Do not implement the old broad streamlining plan before this baseline is
  reviewed.

## Acceptance criteria

- [x] The five-workspace information architecture is defined.
- [x] Standard analysis, result review, plot review, history, and joint-analysis
  interaction flows are documented.
- [x] Action ownership and duplicate-entry rules are explicit.
- [x] Always-retain, contextual-retain, defer, and remove-after-verification
  items are listed.
- [x] Responsive, bilingual, keyboard, and error-state requirements are listed.
- [x] Later implementation gates and slice order are defined.
- [x] No production GUI code is changed.

## Affected boundaries

- [x] GUI navigation and workspace ownership
- [x] Results/history/sample/figure interaction contracts
- [x] Accessibility and responsive layout
- [x] Agent architecture and implementation sequencing

## Implementation plan

1. Inspect the existing GUI streamlining draft and current MainWindow workspace,
   results, plots, history, sample, and joint entry points.
2. Define the final interaction flow and canonical owner for each action.
3. Write the retention/deferment/removal checklist and implementation gates.
4. Record the decision and verify the documentation-only change.

## Verification

```powershell
git diff --check
git status --short
```

The later implementation wave must run the GUI regression matrix, changed-file
Ruff/compile checks, and manual 1280x820/960x600 checks before deleting any
duplicate route.

## Review checkpoint

- Strategy document: `docs/superpowers/specs/2026-07-12-gui-streamlining-interaction-plan.md`
- Decision memory: `docs/agent/memory/decisions/0004-gui-streamlining-last-wave.md`
- Production Python files changed: none.
- Implementation commits: `a726039`, `da87f14`, `8412ca3`, `cab2168`, `0ce603f`, `78df20d`.
- GUI focused regression matrix: 452 passed in 49.85s.
- Workspace-mode and changed-scope compile checks passed; `git diff --check` passed.
- Existing Ruff baseline findings remain in legacy GUI modules; no unrelated import cleanup was included.
- Status: implementation complete for the approved streamlining slice; PR review required before integration.
