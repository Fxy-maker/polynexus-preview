---
kind: task
status: in_progress
date: 2026-07-20
title: Complete editor reliability, productivity, and research workflow
---

# Complete editor workflow

## Goal

Finish the remaining chart-editor workflow gaps: actionable damaged-document
handling, distribution, hierarchical layers, contextual actions, templates,
format painting, multi-chart batch editing, chart comparison, revision diff,
and export presets.

## Non-goals

- Do not change scientific analysis algorithms or generated real-data outputs.
- Do not change Origin adapter semantics.
- Do not silently overwrite source documents, export destinations, or corrupt
  files.
- Do not bypass `EditSession`, figure-document persistence, or manifest-only
  gallery discovery.

## Affected boundaries

- Figure document loading and validation
- Figure edit commands, object store, and edit session
- ChartEditor object/layer/context-action surface
- Chart gallery batch and comparison flows
- Template, style-bundle, revision-diff, and export-preset persistence

## Acceptance criteria

- Corrupt/unsupported documents show an actionable diagnostic while preserving
  the original file.
- Horizontal and vertical distribution are undoable and selection-aware.
- The object surface supports nested layer groups, visibility, lock state,
  search, context menus, and scoped shortcuts.
- Templates, format painter, batch chart editing, comparison, working-vs-
  published diff, and export presets are available from the GUI.
- Each behavior change has focused regression coverage.
- Structured and default repository verification pass, or any limitation is
  reported with exact evidence.

## Verification

```bash
python scripts/verify.py --task docs/agent/tasks/2026-07-20-editor-workflow-completion.md --changed --types
python scripts/verify.py --changed --types
```

## Checkpoints

1. Document reliability and damaged-document diagnostics.
2. Distribution, visibility command, hierarchy, context menu, and shortcuts.
3. Templates, format painter, batch editing, comparison, revision diff, and
   export presets.
