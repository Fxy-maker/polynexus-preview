---
kind: task
status: active
date: 2026-07-19
title: Undoable batch alignment and grouping
---

# Undoable batch alignment and grouping

## Goal

Provide common editor batch actions—left/center/top alignment and group/
ungroup—using one canonical command per user action and one undo step.

## Non-goals

- Do not alter scientific analysis or renderer semantics.
- Do not introduce a second document mutation path in Qt handlers.
- Do not implement arbitrary freeform group transforms in this slice.

## Acceptance criteria

- [x] Alignment preserves object sizes and commits atomically.
- [x] Group/ungroup stores explicit group membership and round-trips through
      undo/redo.
- [x] Locked or unsupported selections fail without partial changes.
- [x] The editor exposes batch actions only when at least two objects are
      selected.
- [x] Focused core and GUI regression tests pass.

## Affected boundaries

- [x] Figure edit command/session core
- [x] ChartEditor batch action surface
- [x] Automated tests

## Implementation plan

1. Add failing command and batch-mixin tests.
2. Implement atomic alignment/group commands and selection routing.
3. Expose compact editor actions with selection-aware enablement.
4. Run the task-scoped verifier and create a checkpoint.

## Verification

```bash
python scripts/verify.py --task docs/agent/tasks/2026-07-19-batch-alignment-and-grouping.md --changed --types
```

## Evidence

- Focused batch/core/layout suite: `31 passed`.
