# Agent Task

## Goal

Deliver the confirmed canvas-first Origin editor improvement: a persistent canvas area with a collapsible Inspector drawer, practical text/line/arrow/rectangle/Bézier-curve tools, and reliable Origin data-source export diagnostics.

## Non-goals

- Do not modify scientific analysis algorithms, sample-database schema, gallery discovery, or project result data.
- Do not add a freehand drawing tool, a generic plotting workbench, or arbitrary Origin/LabTalk execution.
- Do not replace the current figure-document or edit-session contracts.

## Affected boundaries

- [x] GUI layout and editor interaction
- [x] Figure-document object normalization and rendering adapters
- [x] Origin export source preparation and user-facing diagnostics
- [ ] Scientific analysis semantics
- [ ] Database schema

## Acceptance criteria

- [ ] Style and figure-size changes do not shrink the visible canvas or leave a fixed-size plot in the upper-left corner.
- [ ] Inspector opens and closes as a drawer, preserves a user-requested close state, and restores canvas width when closed.
- [ ] Users can create, select, style, save, reload, undo/redo, and export text, line, arrow, rectangle, and Bézier curve annotations.
- [ ] Origin export resolves run-relative paths, materializes valid inline data when a file path is unavailable, and reports an actionable error when neither is available.
- [ ] Focused regression suites and `python scripts/verify.py --changed --types` pass.

## Verification

```powershell
python -m pytest tests/test_chart_editor_layout.py tests/test_chart_editor.py tests/test_annotation_canvas.py tests/test_chart_editor_generated_interaction_mixin.py tests/test_chart_editor_generated_document_mixin.py tests/test_origin_mapping.py tests/test_origin_package_exporter.py tests/test_originpro_adapter.py tests/test_origin_com_adapter.py tests/test_chart_editor_origin_export.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-18-origin-editor-usability.md --changed --types
python scripts/verify.py --changed --types --full --boundary
```

## Review checkpoint

- Reviewer focus: canvas/physical-figure separation, one canonical curve object across static and generated rendering, and safe data-source materialization.
- Human review required: yes; this task crosses GUI, document, and export boundaries.
- Design: `docs/superpowers/specs/2026-07-18-origin-editor-usability-design.md`.
- Implementation plan: `docs/superpowers/plans/2026-07-18-origin-editor-usability.md`.
- Status: planned.
