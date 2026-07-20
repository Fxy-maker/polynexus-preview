# Chart Editor Workflow Completion Design

> **Status:** approved direction; implementation is split into independently
> verifiable reliability, editor-productivity, and research-workflow slices.

## Goal

Finish the remaining chart-editor workflow gaps identified after the existing
reliability and high-frequency editing work: explicit damaged-document
handling, distribution and layer-oriented editing, contextual commands, and
professional template, batch, comparison, version, and export workflows.

## Scope and non-goals

This design changes the figure-document/editor/gallery boundaries only. It does
not change scientific analysis algorithms, generated real-data outputs, Origin
adapter semantics, or the manifest-only gallery discovery rule.

The implementation must preserve the existing `EditSession` command boundary,
the first-selected-object compatibility route, run-relative data-source
resolution, and atomic project-package export.

## Design

### 1. Document reliability

`load_figure_document` remains a compatibility wrapper returning a normalized
document. A new report-oriented loader will classify the load as `missing`,
`valid`, `corrupt`, or `unsupported`, and will retain the document path and a
user-safe diagnostic. JSON/schema failures must never be silently converted to
an empty document.

ChartViewer, ChartEditor, and figure-window routing will consume the report
when opening persisted documents. A corrupt document keeps its original file
untouched and presents three safe actions: open the rendered/static preview,
open the explicit historical-recovery view, or export the original document
as a backup for inspection. A missing document continues to allow an image
preview when one exists.

### 2. Editing commands and visible surface

The core receives undoable `DistributeObjectsCommand` operations for horizontal
and vertical equal-spacing distribution. They operate on the selected object
bounding boxes, preserve object dimensions, reject locked/unsupported objects,
and produce one `EditSession` history entry.

Visibility becomes an explicit undoable object state operation while retaining
the existing object-list checkbox behavior. Group nodes are represented as
parents in a layer-oriented tree; object ids and the existing first-selected
route remain stable. The tree exposes visibility and lock indicators and
supports filtering without flattening group ownership in the model.

The editor adds a context menu backed by the same public callbacks as the
toolbar: select, hide/show, lock/unlock, delete, bring front/back, align,
distribute, group, ungroup, copy style, and paste style. Keyboard shortcuts
are scoped so text fields remain usable. All mutating actions route through
core commands or the existing annotation transaction boundary.

### 3. Professional research workflow

Chart templates store document-level structure, object layout, and style, but
never embed or duplicate source data. Applying a template creates an undoable
document edit and keeps the current chart's data-source bindings unless the
user explicitly chooses a compatible source mapping.

Format painter serializes a validated style bundle for titles, axes, lines,
markers, annotations, and generated plot objects. It applies only compatible
fields and reports skipped fields instead of silently changing semantics.

Selected gallery entries can be loaded into a batch-edit preview. A batch plan
contains immutable target ids, the requested style/template operation, and a
per-entry validation result. Confirmation applies each document through its
normal persistence path and leaves no partial temporary files on validation or
write failure.

Chart comparison opens two selected entries in a synchronized side-by-side
view with source identity, revision, zoom, and axis-scale context visible.
Working/published comparison uses normalized document, asset-manifest, and
rendered-preview differences; revision badges remain a summary, not a
substitute for the diff.

Export presets store named output formats and options separately from chart
style presets. The preset is validated before export and never overwrites an
existing destination without an explicit user choice.

## Implementation boundaries

- Core contracts: `polynexus/core/figure_document.py`,
  `polynexus/core/figure_edit_commands.py`, `polynexus/core/figure_edit_session.py`,
  and new focused services under `polynexus/core/figures/`.
- Editor surface: `polynexus/gui/widgets/chart_editor*.py`, using view models
  or command results rather than technique-specific branches.
- Gallery and comparison: `polynexus/gui/widgets/chart_viewer.py` and focused
  gallery/comparison services.
- Persistence: existing figure-document, gallery-manifest, and project-bundle
  services; no generated outputs or real regression datasets are edited.

## Acceptance criteria

- Corrupt and unsupported figure documents produce a visible, actionable
  diagnostic and preserve the original file.
- Horizontal and vertical distribution are undoable, selection-aware, and
  covered by core and GUI regression tests.
- The layer tree, context menu, visibility, lock state, and shortcuts expose
  the same command semantics and remain compatible with existing selection.
- Templates, format painter, batch editing, comparison, revision diff, and
  export presets are usable from the GUI and have focused persistence and
  failure-path tests.
- Existing reliability, editor, gallery, and Origin regression suites remain
  green.
- Verification uses the structured task command and the repository default:

  ```bash
  python scripts/verify.py --task docs/agent/tasks/2026-07-20-editor-workflow-completion.md --changed --types
  python scripts/verify.py --changed --types
  ```

## Deliberate limitations

- No automatic migration of arbitrary legacy/corrupt JSON will overwrite the
  source file; recovery remains explicit.
- Template application will not infer scientifically unsafe data mappings.
- Batch editing will not silently apply to entries that fail validation.
- Full pixel-level image diff is not required; the comparison view reports
  normalized document/manifest differences and shows both rendered previews.
