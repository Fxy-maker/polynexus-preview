---
kind: task
status: completed
date: 2026-07-19
title: Icon toolbar and one-command drag transactions
---

# Icon toolbar and one-command drag transactions

## Goal

Make editor tools visually scannable and ensure a completed generated-object
drag produces one undoable command rather than a history entry per mouse move.

## Non-goals

- Do not redesign the renderer or introduce a second canvas state model.
- Do not change existing tool meanings or scientific data.

## Acceptance criteria

- [x] Toolbar actions have deterministic non-empty icons and translated
      tooltips while remaining keyboard accessible.
- [x] Drag motion updates only the transient preview document when a session is
      active; release commits one replace command.
- [x] Escape restores the original drag snapshot without adding history.
- [x] Focused toolbar, transaction, and existing drag regression tests pass.

## Affected boundaries

- [x] ChartEditor toolbar presentation
- [x] Generated drag/session boundary
- [x] Automated tests

## Implementation plan

1. Add failing icon and transaction tests.
2. Add vector icons and transactional drag commit.
3. Verify and checkpoint.

## Verification

```bash
python scripts/verify.py --task docs/agent/tasks/2026-07-19-editor-toolbar-and-drag-transactions.md --changed --types
```

## Evidence

- Full toolbar/transaction/drag/editor regression slice: `252 passed`.
