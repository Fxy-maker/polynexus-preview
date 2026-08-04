# Qt lifecycle stability design

## Goal

Make the desktop test and runtime figure-preview lifecycle safe when widgets
are destroyed while deferred layout work is pending, and remove the MainWindow
workspace-summary method/label name collision that breaks AI tuning context.

## Root causes

1. `FigureFilePreview` used unowned `QTimer.singleShot` callbacks bound to the
   widget. A deleted preview could still receive `fit_to_window()` and touch a
   deleted `QGraphicsScene`.
2. `MainWindow` assigned a QLabel to `_workspace_context_summary`, shadowing
   the `MainWindowSummaryMixin._workspace_context_summary()` method.
3. ChartEditor tests left top-level editors alive until a later generic Qt
   fixture closed them, which invoked the user-facing dirty-document prompt in
   offscreen teardown.

## Design

- Replace preview single-shot callbacks with two single-shot `QTimer` children
  owned by `FigureFilePreview`; stop them when the preview is cleared.
- Rename only the MainWindow label storage to
  `_workspace_context_summary_label`; keep a legacy non-callable label fallback
  in the workspace mixin for lightweight test doubles.
- Add an autouse test isolation fixture that closes only ChartEditor instances,
  clears their test-only dirty state, and processes deferred deletion.

## Non-goals

- Do not weaken the production dirty-document close prompt.
- Do not change figure rendering, scientific calculations, or publication roles.
- Do not delete user data or alter existing scratch directories.

## Acceptance

- The preview deletion regression passes without a deleted-Qt-object error.
- AI tuning workspace-context regressions pass.
- ChartEditor plus DSC lifecycle passes as one process without Qt heap abort.
- Repository verification records any remaining unrelated full-suite limits.

