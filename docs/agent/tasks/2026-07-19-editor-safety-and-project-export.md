---
kind: task
status: completed
date: 2026-07-19
title: Editor unsaved protection and self-contained project export
---

# Editor unsaved protection and self-contained project export

## Goal

Prevent accidental loss of chart edits when closing `ChartEditor`, and provide
an atomic self-contained project package that can be moved or archived without
depending on the original source paths.

## Non-goals

- Do not change scientific analysis results or figure-generation semantics.
- Do not alter Origin adapter behavior or its existing compatibility package.
- Do not silently overwrite an existing package selected by the user.
- Do not edit generated outputs, real datasets, secrets, or runtime directories.

## Acceptance criteria

- [x] Closing a dirty editor offers Save, Discard, and Cancel; Cancel keeps the
      editor open and a successful Save permits closing.
- [x] Closing a clean editor is not blocked.
- [x] Project export writes one self-contained package with document, figure
      assets, data sources, and a checksum manifest.
- [x] Relative and run-relative sources are resolved safely; missing sources or
      unsafe paths fail without leaving a partial output.
- [x] Existing files are never overwritten implicitly.
- [x] Focused regression tests cover close decisions, save failure, package
      contents, relocation, and atomic failure cleanup.

## Affected boundaries

- [x] ChartEditor window lifecycle
- [x] Core figure project persistence
- [x] Export dialog integration
- [x] Automated tests

## Implementation plan

1. Add failing close-protection and project-package regression tests.
2. Implement the core atomic package service with safe source resolution and
   checksums.
3. Add `ChartEditor` close decisions and the project-package export menu
   action while preserving existing save and Origin routes.
4. Run focused tests, the task-scoped verifier, and create an atomic
   checkpoint.

## Verification

```bash
python scripts/verify.py --task docs/agent/tasks/2026-07-19-editor-safety-and-project-export.md --changed --types
```

## Memory impact

Update `docs/agent/memory/active-work.md` with exact focused and verifier
results after the checkpoint. Record any unsupported source formats as known
limitations rather than silently falling back.

## Evidence

- Close-protection, package, and GUI integration suite: `28 passed`.
- The package service writes `figure_document.json`, `manifest.json`, figure
  assets, and bundle-relative sources into an atomic `.pnproject.zip`.
- Task-scoped verifier passed after the checkpoint was created.
