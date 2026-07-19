---
kind: task
status: completed
date: 2026-07-19
title: Object tree search, multi-selection state, and locking
---

# Object tree search, multi-selection state, and locking

## Goal

Make the editor object tree practical for figures with many objects: users can
filter by name/type, select several objects without losing the canonical
selection, and lock/unlock an object through the same undoable edit session.

## Non-goals

- Do not change scientific object semantics or renderer geometry.
- Do not implement alignment/group transforms in this slice; they consume the
  multi-selection contract in a later task.
- Do not bypass `EditSession` or mutate the document from Qt-only handlers.

## Acceptance criteria

- [x] Object tree search filters labels by object id, name, or type and keeps
      the background row available.
- [x] Object tree supports extended selection and exposes selected ids without
      breaking the existing canonical single selection route.
- [x] Lock/unlock is an undoable core command and locked objects reject normal
      edits while the object tree shows the state.
- [x] Focused regression tests cover search, multi-selection, lock command,
      undo/redo, and GUI state synchronization.

## Affected boundaries

- [x] Figure edit command/session core
- [x] ChartEditor object tree
- [x] Selection model
- [x] Automated tests

## Implementation plan

1. Add failing core, selection-model, and object-tree regression tests.
2. Add `SetLockCommand` and a multi-id selection model contract.
3. Add object-tree search, extended selection, lock action, and state labels.
4. Run the focused verifier and create one atomic checkpoint.

## Verification

```bash
python scripts/verify.py --task docs/agent/tasks/2026-07-19-object-tree-selection-and-locking.md --changed --types
```

## Memory impact

Update `docs/agent/memory/active-work.md` with the exact focused test count and
known limitations before checkpointing.

## Evidence

- Object-tree/core selection suite: `27 passed`.
- The existing canonical first-selected-object route remains compatible while
  `FigureSelectionModel.selected_ids` preserves ordered extended selection.
