---
kind: task
status: completed
date: 2026-07-19
title: Editor tool shortcuts and complete alignment surface
---

# Editor tool shortcuts and complete alignment surface

## Goal

Expose the editor's primary tools through predictable canvas-scoped shortcuts
and make all core alignment modes reachable from the batch action surface.

## Non-goals

- Do not make single-key shortcuts intercept text-entry fields.
- Do not change command semantics or scientific rendering.

## Acceptance criteria

- [x] Select, text, line, arrow, rectangle, undo, redo, save, export, and delete
      have discoverable shortcuts with appropriate focus scope.
- [x] All six alignment modes are reachable from the editor UI.
- [x] Focused shortcut/layout tests and existing editor regressions pass.

## Affected boundaries

- [x] ChartEditor keyboard surface
- [x] Batch alignment controls
- [x] Automated tests

## Implementation plan

1. Add failing shortcut and alignment-surface tests.
2. Add canvas-scoped shortcuts and the remaining alignment actions.
3. Verify, update memory, and checkpoint.

## Verification

```bash
python scripts/verify.py --task docs/agent/tasks/2026-07-19-editor-shortcuts-and-alignment-surface.md --changed --types
```

## Evidence

- Shortcut/alignment/editor suite: `249 passed`.
