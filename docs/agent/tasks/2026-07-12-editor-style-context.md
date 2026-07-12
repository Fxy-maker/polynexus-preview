# Agent Task

## Goal

Fix ChartEditor style-context leakage during consecutive manifest/generated figure switches. The current document style must hydrate the controls, and missing fields must fall back to editor defaults.

## Non-goals

- Do not change the generated document schema.
- Do not change style preset storage or UI layout.
- Do not change static image annotation export semantics.
- Do not migrate the legacy editor architecture.

## Acceptance criteria

- [x] Generated/object document style fields hydrate from the current document.
- [x] Switching documents resets missing fields instead of inheriting the previous figure's state.
- [x] Generated document initialization is not driven by legacy `load_figure_edit()` state.
- [x] Static files retain the existing edit-overlay behavior.
- [x] Source-switch, generated-document, and save-mixin focused tests pass.

## Affected boundaries

- [x] GUI
- [x] Persistence/document loading
- [x] Export/editor state

## Implementation plan

1. Add focused RED tests for generated-document style hydration, stale-state reset, and the `set_output_target()` overlay boundary.
2. Implement centralized style-context reset/hydration and wire generated documents to current document style while keeping static edit overlays on the static path.
3. Run focused and editor regression matrices, validate changed Python files, update task evidence and active memory, then request human review.

## Verification

```powershell
python -m pytest tests/test_chart_editor_style_context.py tests/test_chart_editor_generated_document_mixin.py tests/test_chart_editor_save_mixin.py tests/test_chart_editor_style_preset_mixin.py -q
python -m pytest tests/test_chart_editor.py tests/test_chart_editor_panel_mixin.py tests/test_chart_editor_render_mixin.py tests/test_chart_editor_generated_selection_mixin.py tests/test_chart_editor_generated_geometry_mixin.py tests/test_chart_editor_save_mixin.py -q
python scripts/verify.py --changed --types
```

## Review checkpoint

- Reviewer focus: editor state boundary, generated-document style precedence, and static compatibility.
- Human review required: yes.
- Implementation branch: `codex/editor-style-context`
- Design commit: `b8e1787`
- RED test commit: `ce2a304`
- Implementation commit: `247edda`
- Regression test commit: `221dce4`
- Focused style-context tests: 5 passed.
- Focused generated/save/preset set: 12 passed.
- Editor regression matrix: 267 passed.
- Task-card validation passed using `D:\PolyNexus\scripts\task_check.py`.
- Changed-file Ruff, compileall, and `git diff --check` passed.
- Status: implementation complete; human review required before integration.
