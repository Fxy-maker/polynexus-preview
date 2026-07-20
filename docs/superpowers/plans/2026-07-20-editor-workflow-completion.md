# Chart Editor Workflow Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> to implement this plan task-by-task with verification checkpoints.

**Goal:** Complete the remaining chart-editor reliability, high-frequency editing, and professional research workflows without changing scientific analysis behavior.

**Architecture:** Extend existing figure-document and `EditSession` contracts rather than adding GUI-only mutations. Add small pure core services for document reports, distribution, style/template payloads, revision diffs, and export presets; let ChartEditor and ChartGallery consume those contracts through view-model-like payloads.

**Tech Stack:** Python 3.10+, PySide6, JSON figure documents, pytest, existing PolyNexus verifier and atomic persistence helpers.

---

### Task 1: Add structured document-load diagnostics

**Files:**
- Modify: `polynexus/core/figure_document.py`
- Modify: `polynexus/gui/figure_window_service.py`
- Modify: `polynexus/gui/widgets/chart_editor.py`
- Modify: `polynexus/gui/widgets/chart_viewer.py`
- Test: `tests/test_figure_document.py`
- Test: `tests/test_figure_window_service.py`
- Test: `tests/test_chart_viewer.py`
- Create: `tests/test_figure_document_diagnostics.py`

- [ ] **Step 1: Write failing tests for load classification.**

  Add tests that write valid JSON, malformed JSON, a non-mapping JSON value,
  and an unsupported document version. Assert the report contains `status`,
  `path`, `document`, and a non-empty safe `message`, and that the malformed
  source is not rewritten.

- [ ] **Step 2: Run the focused tests and confirm the expected failure.**

  Run:

  ```bash
  python -m pytest tests/test_figure_document_diagnostics.py -q
  ```

  Expected: failure because the report loader and diagnostic status contract do
  not exist yet.

- [ ] **Step 3: Implement the report contract and compatibility wrapper.**

  Add a frozen `FigureDocumentLoadReport` with `status`, `path`, `document`,
  `message`, and `error_type`. Add `load_figure_document_report()` that
  distinguishes missing, valid, corrupt, and unsupported documents. Keep
  `load_figure_document()` returning `{}` for missing/corrupt legacy callers,
  but make GUI callers use the report so errors are visible.

- [ ] **Step 4: Route GUI open paths through the report.**

  Preserve image previews and historical recovery for missing/corrupt files;
  show a localized warning with safe actions and never call a save path during
  a failed load. Keep existing valid-document behavior unchanged.

- [ ] **Step 5: Run the focused tests and refactor only after green.**

  Run:

  ```bash
  python -m pytest tests/test_figure_document_diagnostics.py tests/test_figure_document.py tests/test_figure_window_service.py tests/test_chart_viewer.py -q
  ```

- [ ] **Step 6: Create checkpoint.**

  ```bash
  python scripts/auto_commit.py --message "fix(editor): report damaged figure documents" --files polynexus/core/figure_document.py polynexus/gui/figure_window_service.py polynexus/gui/widgets/chart_editor.py polynexus/gui/widgets/chart_viewer.py tests/test_figure_document_diagnostics.py tests/test_figure_document.py tests/test_figure_window_service.py tests/test_chart_viewer.py
  ```

### Task 2: Add undoable distribution and explicit visibility commands

**Files:**
- Modify: `polynexus/core/figure_edit_commands.py`
- Modify: `polynexus/core/figure_edit_capabilities.py`
- Modify: `polynexus/gui/widgets/chart_editor_batch_edit_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_object_list_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor.py`
- Test: `tests/test_figure_edit_batch_commands.py`
- Test: `tests/test_chart_editor_batch_edit.py`
- Test: `tests/test_chart_editor_object_list_mixin.py`

- [ ] **Step 1: Write failing core tests for horizontal/vertical distribution.**

  Build three objects with unequal widths/heights and assert distribution keeps
  outer edges and dimensions unchanged, creates equal gaps, rejects fewer than
  three objects, and rejects locked objects without mutation.

- [ ] **Step 2: Run the core tests and confirm the expected failure.**

  ```bash
  python -m pytest tests/test_figure_edit_batch_commands.py -q
  ```

- [ ] **Step 3: Implement `DistributeObjectsCommand` and `SetVisibilityCommand`.**

  Use the existing command result/error conventions. Distribution must operate
  on normalized object geometry and produce one undo/redo snapshot. Visibility
  must be persisted through the object store/session route used by the current
  object-list checkbox.

- [ ] **Step 4: Expose the commands in the editor.**

  Add horizontal/vertical distribute actions, enable them only for valid
  selections, and route checkbox changes through `SetVisibilityCommand`.

- [ ] **Step 5: Run focused editor tests and checkpoint.**

  ```bash
  python -m pytest tests/test_figure_edit_batch_commands.py tests/test_chart_editor_batch_edit.py tests/test_chart_editor_object_list_mixin.py -q
  python scripts/auto_commit.py --message "feat(editor): add distribution and undoable visibility" --files polynexus/core/figure_edit_commands.py polynexus/core/figure_edit_capabilities.py polynexus/gui/widgets/chart_editor_batch_edit_mixin.py polynexus/gui/widgets/chart_editor_object_list_mixin.py polynexus/gui/widgets/chart_editor.py tests/test_figure_edit_batch_commands.py tests/test_chart_editor_batch_edit.py tests/test_chart_editor_object_list_mixin.py
  ```

### Task 3: Replace the flat object list with a layer-oriented tree

**Files:**
- Modify: `polynexus/gui/widgets/chart_editor.py`
- Modify: `polynexus/gui/widgets/chart_editor_object_list_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_selection_mixin.py`
- Create: `polynexus/gui/widgets/chart_editor_layer_model.py`
- Test: `tests/test_chart_editor_layer_model.py`
- Test: `tests/test_chart_editor_object_list_mixin.py`

- [ ] **Step 1: Write failing model tests.**

  Assert group objects become parent nodes, children retain stable ids, a
  filtered query keeps matching ancestors visible, and selection returns the
  same ordered ids used by the existing compatibility route.

- [ ] **Step 2: Run the tests and confirm failure.**

  ```bash
  python -m pytest tests/test_chart_editor_layer_model.py -q
  ```

- [ ] **Step 3: Implement a pure layer-tree model.**

  Build a tree DTO/model from the normalized document and current object store;
  keep visibility and lock state as display metadata. Do not make Qt event
  handlers responsible for grouping semantics.

- [ ] **Step 4: Integrate the tree and preserve search/multi-select behavior.**

  Replace only the presentation widget, retain `_object_list_selected_ids()`
  compatibility, and update selection synchronization for parent/child rows.

- [ ] **Step 5: Run layer/object-tree regressions and checkpoint.**

  ```bash
  python -m pytest tests/test_chart_editor_layer_model.py tests/test_chart_editor_object_list_mixin.py tests/test_chart_editor_generated_selection_mixin.py -q
  python scripts/auto_commit.py --message "feat(editor): add hierarchical layer tree" --files polynexus/gui/widgets/chart_editor.py polynexus/gui/widgets/chart_editor_object_list_mixin.py polynexus/gui/widgets/chart_editor_generated_selection_mixin.py polynexus/gui/widgets/chart_editor_layer_model.py tests/test_chart_editor_layer_model.py tests/test_chart_editor_object_list_mixin.py tests/test_chart_editor_generated_selection_mixin.py
  ```

### Task 4: Add context menus and complete editor shortcuts

**Files:**
- Modify: `polynexus/gui/widgets/chart_editor.py`
- Modify: `polynexus/gui/widgets/chart_editor_layout_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_batch_edit_mixin.py`
- Test: `tests/test_chart_editor_context_menu.py`
- Test: `tests/test_chart_editor_shortcuts.py`

- [ ] **Step 1: Write failing action-surface tests.**

  Assert the context menu contains selection, visibility, lock, delete, z-order,
  alignment, distribution, grouping, and style-copy actions; assert shortcuts
  are unavailable while a line edit owns focus and available on the canvas.

- [ ] **Step 2: Run tests and confirm failure.**

  ```bash
  python -m pytest tests/test_chart_editor_context_menu.py tests/test_chart_editor_shortcuts.py -q
  ```

- [ ] **Step 3: Add shared QAction factories.**

  Build menu actions from the same callbacks used by toolbar buttons. Add
  scoped shortcuts for hide/show, group/ungroup, align, distribute, and z-order
  while preserving text-field input behavior.

- [ ] **Step 4: Verify context-menu and shortcut behavior.**

  ```bash
  python -m pytest tests/test_chart_editor_context_menu.py tests/test_chart_editor_shortcuts.py tests/test_chart_editor_layout.py -q
  ```

- [ ] **Step 5: Create checkpoint.**

  ```bash
  python scripts/auto_commit.py --message "feat(editor): add contextual actions and shortcuts" --files polynexus/gui/widgets/chart_editor.py polynexus/gui/widgets/chart_editor_layout_mixin.py polynexus/gui/widgets/chart_editor_batch_edit_mixin.py tests/test_chart_editor_context_menu.py tests/test_chart_editor_shortcuts.py
  ```

### Task 5: Add chart templates and format painter

**Files:**
- Create: `polynexus/core/figure_template_service.py`
- Create: `polynexus/core/figure_style_bundle.py`
- Modify: `polynexus/gui/widgets/chart_editor.py`
- Modify: `polynexus/gui/widgets/chart_editor_style_preset_mixin.py`
- Test: `tests/test_figure_template_service.py`
- Test: `tests/test_figure_style_bundle.py`
- Test: `tests/test_chart_editor_style_preset_mixin.py`

- [ ] **Step 1: Write failing persistence and compatibility tests.**

  Assert templates omit source data, round-trip canvas/style/objects, reject
  malformed payloads, and apply only compatible style fields. Assert format
  painter reports skipped incompatible fields.

- [ ] **Step 2: Run tests and confirm failure.**

  ```bash
  python -m pytest tests/test_figure_template_service.py tests/test_figure_style_bundle.py -q
  ```

- [ ] **Step 3: Implement validated template/style-bundle services.**

  Store user presets under the existing configuration directory with atomic
  JSON writes. Normalize payloads and keep data-source bindings outside the
  template.

- [ ] **Step 4: Add editor actions and undoable application.**

  Add template save/apply and format-copy/format-paste controls to the visible
  editor surface. Apply through one document edit transaction and show skipped
  field diagnostics.

- [ ] **Step 5: Run focused GUI tests and checkpoint.**

  ```bash
  python -m pytest tests/test_figure_template_service.py tests/test_figure_style_bundle.py tests/test_chart_editor_style_preset_mixin.py -q
  python scripts/auto_commit.py --message "feat(editor): add chart templates and format painter" --files polynexus/core/figure_template_service.py polynexus/core/figure_style_bundle.py polynexus/gui/widgets/chart_editor.py polynexus/gui/widgets/chart_editor_style_preset_mixin.py tests/test_figure_template_service.py tests/test_figure_style_bundle.py tests/test_chart_editor_style_preset_mixin.py
  ```

### Task 6: Add previewed batch chart editing

**Files:**
- Create: `polynexus/core/figure_batch_edit_service.py`
- Modify: `polynexus/gui/widgets/chart_viewer.py`
- Modify: `polynexus/gui/figure_window_service.py`
- Test: `tests/test_figure_batch_edit_service.py`
- Test: `tests/test_chart_gallery_management.py`

- [ ] **Step 1: Write failing batch-plan tests.**

  Assert selected entries produce immutable target ids, validation errors are
  reported per entry, valid plans preview the normalized changes, and a failed
  write leaves all original documents unchanged.

- [ ] **Step 2: Run tests and confirm failure.**

  ```bash
  python -m pytest tests/test_figure_batch_edit_service.py -q
  ```

- [ ] **Step 3: Implement plan/preview/apply services.**

  Reuse template/style-bundle normalization and existing atomic document saves.
  Validate every target before writing any target; write to temporary files and
  replace only after the complete plan validates.

- [ ] **Step 4: Integrate gallery selection and confirmation UI.**

  Add a "Batch Edit" action beside existing batch export. Show target count, changed
  fields, skipped entries, and a confirmation action before applying.

- [ ] **Step 5: Run focused tests and checkpoint.**

  ```bash
  python -m pytest tests/test_figure_batch_edit_service.py tests/test_chart_gallery_management.py -q
  python scripts/auto_commit.py --message "feat(gallery): add previewed batch chart editing" --files polynexus/core/figure_batch_edit_service.py polynexus/gui/widgets/chart_viewer.py polynexus/gui/figure_window_service.py tests/test_figure_batch_edit_service.py tests/test_chart_gallery_management.py
  ```

### Task 7: Add chart comparison and working/published revision diff

**Files:**
- Create: `polynexus/core/figure_revision_diff.py`
- Create: `polynexus/gui/widgets/chart_comparison_view.py`
- Modify: `polynexus/gui/widgets/chart_viewer.py`
- Modify: `polynexus/core/figures/project_service.py`
- Test: `tests/test_figure_revision_diff.py`
- Test: `tests/test_chart_comparison_view.py`
- Test: `tests/test_chart_gallery_management.py`

- [ ] **Step 1: Write failing diff and selection tests.**

  Assert normalized documents produce stable field-level changes, asset
  manifests report added/removed/changed assets, identical revisions compare
  equal, and two selected gallery entries produce a comparison request with
  source/revision metadata.

- [ ] **Step 2: Run tests and confirm failure.**

  ```bash
  python -m pytest tests/test_figure_revision_diff.py tests/test_chart_comparison_view.py -q
  ```

- [ ] **Step 3: Implement pure revision diff and comparison request models.**

  Ignore volatile timestamps, preserve data-source identity, and return stable
  sorted changes. Use existing gallery entries and project manifests rather
  than recursive filesystem discovery.

- [ ] **Step 4: Integrate synchronized side-by-side view.**

  Add a comparison action for exactly two selected entries. Keep previews
  usable when a source is missing and display the diagnostic beside the affected
  panel instead of hiding the panel.

- [ ] **Step 5: Run focused tests and checkpoint.**

  ```bash
  python -m pytest tests/test_figure_revision_diff.py tests/test_chart_comparison_view.py tests/test_chart_gallery_management.py -q
  python scripts/auto_commit.py --message "feat(gallery): add chart comparison and revision diff" --files polynexus/core/figure_revision_diff.py polynexus/gui/widgets/chart_comparison_view.py polynexus/gui/widgets/chart_viewer.py polynexus/core/figures/project_service.py tests/test_figure_revision_diff.py tests/test_chart_comparison_view.py tests/test_chart_gallery_management.py
  ```

### Task 8: Add named export presets and finish verification

**Files:**
- Create: `polynexus/core/figure_export_preset_service.py`
- Modify: `polynexus/gui/widgets/chart_editor.py`
- Modify: `polynexus/gui/widgets/chart_viewer.py`
- Test: `tests/test_figure_export_preset_service.py`
- Test: `tests/test_chart_editor_project_export.py`
- Test: `tests/test_chart_gallery_management.py`
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/tasks/2026-07-20-editor-workflow-completion.md`

- [ ] **Step 1: Write failing preset persistence tests.**

  Assert named presets round-trip formats/options, reject unsupported formats,
  and never overwrite an existing destination without explicit confirmation.

- [ ] **Step 2: Run tests and confirm failure.**

  ```bash
  python -m pytest tests/test_figure_export_preset_service.py -q
  ```

- [ ] **Step 3: Implement preset service and editor/gallery controls.**

  Persist presets atomically in the user config directory and reuse existing
  export/project-package callbacks. Keep style presets and export presets in
  separate stores.

- [ ] **Step 4: Run all focused editor/gallery regressions.**

  ```bash
  python -m pytest tests/test_figure_document_diagnostics.py tests/test_figure_edit_batch_commands.py tests/test_chart_editor_layer_model.py tests/test_chart_editor_context_menu.py tests/test_figure_template_service.py tests/test_figure_style_bundle.py tests/test_figure_batch_edit_service.py tests/test_figure_revision_diff.py tests/test_chart_comparison_view.py tests/test_figure_export_preset_service.py tests/test_chart_editor.py tests/test_chart_viewer.py tests/test_chart_gallery_management.py -q
  ```

- [ ] **Step 5: Update durable memory and run the structured verifier.**

  Record exact test counts, known limitations, and the full-verification
  timeout if it recurs. Then run:

  ```bash
  python scripts/verify.py --task docs/agent/tasks/2026-07-20-editor-workflow-completion.md --changed --types
  python scripts/verify.py --changed --types
  ```

- [ ] **Step 6: Create the final checkpoint with an explicit allowlist.**

  ```bash
  python scripts/auto_commit.py --message "feat(editor): complete chart workflow" --files polynexus/core/figure_export_preset_service.py polynexus/gui/widgets/chart_editor.py polynexus/gui/widgets/chart_viewer.py tests/test_figure_export_preset_service.py tests/test_chart_editor_project_export.py tests/test_chart_gallery_management.py docs/agent/memory/active-work.md docs/agent/tasks/2026-07-20-editor-workflow-completion.md
  ```
