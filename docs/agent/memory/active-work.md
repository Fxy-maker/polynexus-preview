# Active Work

## Unified LegendLayout refactor - completed 2026-07-24

- Generated legends now resolve legacy `loc`, two/four-value
  `bbox_to_anchor`, and `box_size` through the pure
  `polynexus/core/figures/legend_layout.py` model. Auto layouts retain legacy
  anchors for inspector compatibility; fixed layouts canonicalize to a
  lower-left axes anchor and positive width/height.
- Formal and legacy renderers, selection frames/handles, hit testing, drag
  previews, inspector geometry, undo transactions, and persistence consume the
  same resolved geometry. Disjoint persisted boxes no longer trigger a hidden
  rendered-bounds fallback, so the visible legend and edit frame cannot belong
  to different layout interpretations.
- Origin-like corner resize now treats the box as a true content scale: the
  drag transaction captures the starting geometry/font, derives a continuous
  area-based font scale, applies it during preview, and persists it with the
  box dimensions. Undo restores both geometry and typography, eliminating the
  former "frame grows, text snaps back" behavior.
- First fixed-box edit normalizes the style to `loc="lower left"`; preview and
  commit share the same style update. Generated export clears selection before
  rendering, so transient frames/handles remain non-exported. Invalid legacy
  dimensions surface a concise status diagnostic.
- Evidence: focused legend/editor matrix `292 passed`; task verifier passed
  with quality gate `282` and preprocessing gate `103`. Task card:
  `docs/agent/tasks/2026-07-24-legend-layout-refactor.md`.
- Known follow-up: restart the GUI for manual visual review of static images,
  log axes, and multi-series legends; the optional Chromium visual companion
  could not launch because the local executable is unavailable.

## Editor legend viewport and typography - completed 2026-07-23

- Formal manifest previews pass the actual live canvas width to the shared
  Matplotlib renderer.  Long automatic sample-name legends choose a safe
  single-column presentation before constrained layout can collapse the plot;
  publication exports retain their independent planned width and can remain
  two-column.
- The same responsive label-aware rule now also applies to legacy generated
  previews.  An explicit legend font size is a normal editable style property:
  it is persisted, rendered in preview/export, and restored through undo.
  Selecting a legend exposes only the font-size control; unrelated color,
  line-width, and alpha controls remain disabled.
- Evidence: focused matrix `291 passed`; structured and default verifier runs
  passed, including quality-gate `282` and preprocessing `103`.  Task card:
  `docs/agent/tasks/2026-07-23-editor-legend-viewport.md`.  The verifier used
  an isolated pytest base directory because the pre-existing repository
  `.pytest_tmp` has a Windows access restriction; no existing scratch artifact
  was changed. Restart the GUI before visual confirmation.

## Editor legend interaction polish - completed 2026-07-23

- Automatic multi-series legends now share one responsive presentation policy
  across formal `MatplotlibFigureRenderer` output and the ChartEditor's legacy
  generated preview: wide canvases retain two columns, while narrow canvases
  use one compact in-plot column and a smaller readable font. This policy is
  transient and never changes saved legend position or style merely because a
  user selects it.
- Double-clicking a generated legend now opens a compact localized dialog with
  one curve-name input per visible legend series. Confirming applies all
  nonblank names through one undoable document replacement, persists once,
  redraws once, and keeps the legend selected; Escape/Cancel leaves the
  document untouched.
- A final review hardening pass ensures a double-click must land on the legend
  itself and filters multi-panel dialog rows to the legend's own panel, so text
  and blank-canvas double-clicks remain available for their existing actions.
- Evidence: focused object-store/render/editor matrix passed `274`; the task
  verifier and default changed/type verifier both passed, including the quality
  gate (`282`) and preprocessing optimization gate (`103`). Task card:
  `docs/agent/tasks/2026-07-23-editor-legend-interaction.md`. Restart the GUI
  before live visual confirmation.

## Multi-series chart legend defaults - completed 2026-07-23

- Object-mode figures now materialize a persisted legend only when at least two
  named plot series are visible. The legend uses sample names verbatim,
  defaults to upper-right placement, and switches to two columns when more
  than three series are present.
- Renaming a series refreshes its legend entry through the existing editor
  name control. Existing legend visibility and dragged position remain
  authoritative; a single-series chart remains legend-free.
- The legacy and formal renderer paths now use the same persisted legend
  object. Multi-panel documents intentionally retain their pre-existing legend
  state rather than receiving an unassigned automatic object. This also fixed
  selected-line endpoint switching, where the second endpoint click had
  previously cleared selection instead of moving the active handle emphasis.
- TDD evidence: object-store, renderer, and offscreen ChartEditor regressions
  first failed for one-series suppression, formal `show_legend: false` output,
  compact columns, multi-panel safety, and endpoint selection; the final
  focused matrix passed `266` tests. Task card:
  `docs/agent/tasks/2026-07-23-editor-multiseries-legend.md`. Running GUI
  instances must be restarted before manual inspection.

## Responsive editor inspector sidebar - completed 2026-07-23

- The ChartEditor inspector can now shrink to 280 logical pixels without
  horizontal scrolling or clipped controls. Inspector forms wrap labels above
  controls, object labels elide instead of forcing width, and the object tree
  has a bounded height so its property fields remain reachable below.
- Batch actions use a three-column grid rather than one long horizontal strip;
  object action controls can shrink with the sidebar without changing commands.
- The focused compact-width Qt regression and editor matrix passed (`78 passed`,
  four known Matplotlib tight-layout warnings). Restart the GUI before visual
  inspection.

## Inline text editor visual polish - completed 2026-07-23

- Direct canvas text entry no longer displays the native blue `QLineEdit`
  focus frame or the `标注文字` / `Annotation text` placeholder over the
  figure. It now uses a transparent input layer, a subtle dashed edit range,
  and Qt's existing blinking caret.
- Enter-to-commit, Escape-to-cancel, focus, text geometry, and double-click
  editing remain on the same shared inline-editor path.
- TDD evidence: the focused visual contract first failed because the input
  retained its native frame, then passed after the minimal chrome change. The
  direct-text workflow matrix passed (`77 passed`, four known Matplotlib
  tight-layout warnings). Restart the GUI before visual inspection.

## Generated undo/redo visual synchronization - completed 2026-07-23

- Fixed generated-object undo and redo so session history now immediately
  rebuilds the canvas, refreshes selection controls, and persists the restored
  document. Previously the document changed first, while the canvas continued
  showing the old artist until a later canvas interaction caused a redraw.
- History navigation now clears the UI selection when an undone add no longer
  exists, then restores the object(s), layer-tree selection, and inspector when
  redo recreates them. Repeated history navigation of an unchanged selection
  source also redraws explicitly rather than relying on a selection signal.
- Regression coverage verifies an inspector geometry edit, immediate undo
  redraw, immediate redo redraw, added-object selection/inspector recovery,
  and batch-selection recovery without an intervening canvas click.

## Editor history shortcuts in numeric controls - completed 2026-07-23

- Fixed the ChartEditor's Ctrl+Z routing when focus is inside a numeric style
  or geometry control. Those controls previously consumed the key before the
  window-level history shortcut could run, making a just-completed font-size
  edit appear non-undoable.
- Ctrl+Z now undoes from canvas or numeric-control focus; Ctrl+Shift+Z and
  Ctrl+Y redo. Plain text inputs retain their local text-editing behavior.
- Qt workflow coverage exercises static canvas focus, generated canvas focus,
  and the generated context font-size spin control, including redo.

## Generated text font-size commit fix - completed 2026-07-23

- Fixed the formal manifest-render styling pass so it no longer overwrites a
  generated text object's persisted `style.font_size`. This keeps a corner-drag
  font-size preview visually identical after mouse release and the resulting
  document rebuild.
- TDD evidence: the focused regression initially failed because a `72 pt`
  object label was reset to `12 pt`; it passes after the object-level style
  boundary is preserved. The ChartEditor workflow suite passes (`48 passed`,
  four known Matplotlib tight-layout warnings).
- The isolated generated-document mixin suite retains one pre-existing,
  unrelated harness failure in
  `test_manifest_editor_registers_native_image_grid_artists_for_object_editing`:
  it instantiates an incomplete mixin without `_generated_figure_object_by_id`.

## Editor workflow convergence - implementation complete 2026-07-23

- Task card: `docs/agent/tasks/2026-07-22-editor-workflow-convergence.md`.
- M1 context identity and stale-result gating are committed; M2 capability
  header, M3 lifecycle controls, M4 export/gallery scope, and M5 shell
  diagnostics are implemented in local checkpoints.
- The 2026-07-23 hardening checkpoint aligns actionable selection feedback,
  defers visibility-tree refresh until the active Qt `itemChanged` call
  returns, adds copyable error diagnostics, and formalizes the GUI `RunState`
  contract so cancelled work cannot publish a late result.
- Evidence: `tests/test_chart_editor.py` passes (`238`); the focused workflow
  matrix passes (`118`, four known Matplotlib tight-layout warnings); the
  structured verifier passes with quality gate `282` and preprocessing
  optimization `103`; `scripts/launch_gui.py --diagnose` resolves the active
  `D:\PolyNexus\polynexus\__init__.py` on
  `codex/origin-editor-usable-controls` at `9fc109c6`.
- M6 decision: no broad `main_window.py` split in this task because the new
  service boundaries cover the accepted behavior. A human visual walkthrough
  remains the only planned follow-up; existing untracked drafts and diagnostics
  remain untouched.

## Origin-style generated text labels - completed 2026-07-22

- Task card: `docs/agent/tasks/2026-07-22-origin-label-text.md`. Generated
  labels are unwrapped, use tight rendered selection overlays, resize by font
  size, and now open a compact one-line editor at the rendered label top edge.
- TDD evidence: the new tall-rectangle Qt regression failed first (`240 !=
  24`), then the focused creation/double-click Enter/Escape workflow passed
  (`3 passed`). The required full label matrix passed (`87 passed`, four known
  Matplotlib tight-layout warnings).
- Verifier commands: `python scripts/verify.py --task
  docs/agent/tasks/2026-07-22-origin-label-text.md --changed --types` and
  `python scripts/verify.py --changed --types` both passed, including Ruff,
  compile, quality gate (`282 passed`), preprocessing gate (`103 passed`), and
  whitespace checks.
- Commit evidence: prerequisite label slices are `63acd9a5`, `ef2d297f`,
  `9de895c8`, `13ab1961`, and `e1dc44a`; the completion checkpoint is
  `bfa6f2ed`, created after verification. None of these commits were pushed.
- A running GUI must be restarted before manual inspection.

## Generated text double-click editing - verification-ready 2026-07-22

- Existing generated text now opens the shared inline editor on a canvas
  double-click, prefilled with the displayed `text` value rather than the
  object-list name.
- Submission uses `UpdateTextCommand`, persists the object document, refreshes
  the rendered figure, and remains undoable.
- Focused ChartEditor workflow/curve matrix passes (`62 passed`); the four
  tight-layout warnings are pre-existing log-axis warnings.
- A running GUI must be restarted from `D:\PolyNexus\scripts\launch_gui.py`
  before visual acceptance.

## Viewport-anchored generated text boxes - verification-ready 2026-07-22

- Implemented the approved Axes-relative text-box slice from task card
  `docs/agent/tasks/2026-07-22-viewport-text-box-refactor.md`. New generated
  text creation stores normalized `x/y/width/height` with
  `coordinate_space: "axes"`; rendering, preview, hit testing, selection
  frames/handles, body movement, corner resizing, and Inspector edits consume
  the same Axes transform.
- Legacy data-coordinate text remains readable and is converted to a persisted
  Axes-relative box when the generated document is saved. Core renderer export
  uses the same transform for marked boxes.
- Fresh expanded focused matrix passes (`106 passed`), structured and default verifiers
  pass with quality gate `282 passed` and preprocessing gate `103 passed`.
- The live GUI acceptance pass remains pending; restart the canonical launcher
  from `D:\PolyNexus` before manual visual verification. The pre-existing
  `.pytest_tmp` ownership issue is avoided with `D:\PolyNexus\.pytest_tmp_alt`.

## Generated text drag anchor follow-up - completed 2026-07-22

- Reproduced the screenshot issue with a regression test: the generated text
  preview moved its Matplotlib `Text` artist to the persisted box origin
  `(x, y)` while the box renderer uses the left/top anchor `(x, y + height)`.
  This made the text visibly fall to the box's lower-left corner during drag.
- Added the shared `polynexus/core/figure_text_geometry.py` anchor contract and
  routed formal rendering, legacy generated preview rendering, and live drag
  preview through it. The focused editor/render matrix now passes (`103`),
  including log-axis text-box movement.
- The final structured/default verifiers pass; live GUI acceptance still
  requires restarting the canonical launcher from
  `D:\PolyNexus\scripts\launch_gui.py`.

## Generated text placement and font sizing - completed 2026-07-22

- Generated text boxes now use their stored box origin as the visual left-top
  anchor, while unboxed text keeps its legacy anchor behavior. The renderer and
  generated-document preview use the same alignment calculation, so selection
  and final rendering no longer disagree about where text begins.
- The generated-object Inspector and context style bar now expose and hydrate
  text font size. Changes are routed through the shared undoable style command,
  persisted to the document, and immediately rebuild the visible artist.
- Generated style submission now only sends line width to object types whose
  core edit capabilities support it; text font-size changes are no longer
  rejected by an unrelated line-width field.
- Focused text/renderer regression checks pass. The broader batch retains the
  pre-existing `test_manifest_editor_registers_native_image_grid_artists_for_object_editing`
  fixture failure because it directly instantiates an incomplete mixin without
  `_generated_figure_object_by_id`; it is outside this fix and remains untouched.
- The canonical launcher diagnostic resolves `D:\PolyNexus\polynexus\__init__.py`.

## High-DPI live canvas fit - completed 2026-07-22

- Fixed generated/editor figure fitting on Windows display scaling: Qt widget
  dimensions are logical pixels, while Matplotlib's Agg buffer uses device
  pixels. The live figure now scales both dimensions by
  `devicePixelRatioF()`, preventing interaction rebuilds from rendering at
  2/3 or 1/2 of the available canvas width/height.
- Figure replacement now assigns the new figure, restores only its viewport
  state, and performs the device-pixel fit last; both the Qt backend assignment
  and viewport-size restoration previously overwrote the corrected size.
- Added a regression test that reproduces a 150% display and asserts the
  figure buffer matches the device-pixel canvas size. Focused render/workflow
  tests pass (`40 passed`); the default changed/type verifier passes with
  quality gate `282 passed` and preprocessing gate `103 passed`.

## Unified canvas interaction - completed 2026-07-21

- Added immutable `Box`, `Segment`, and `Curve` geometry records with legacy
  payload adapters. Generated text and rectangle previews now retain full box
  geometry while moving on linear and logarithmic axes; selection frames and
  handles update from that same geometry.
- Generated text now uses the dragged box's left-bottom anchor, supports body
  movement and four-corner resizing, and commits width/height in one undoable
  edit. Static text and rectangle creation normalizes reversed drags through
  the same box contract.
- Focused cross-mode interaction matrix passed (`141 passed`). Structured and
  default changed/type verifiers pass when `PYTEST_ADDOPTS` points to
  `D:\\PolyNexus\\.pytest_tmp_alt`: quality gate `282 passed`, preprocessing
  gate `103 passed`, compile, whitespace, and memory checks passed.
- Running the local preview server still owns repository `.pytest_tmp`, so the
  verifier without the basetemp override reports WinError 5 during pytest
  cleanup; this is an environment limitation, not a source failure.
- Implementation commits are `e34ed75`, `814d9f5`, `d0b297b`, and `d24cc8b`.


## Inline text editor layering fix - completed 2026-07-21

- Real Qt reproduction showed the generated text input was visible and focused
  but covered by the Matplotlib canvas. The shared inline text editor now raises
  itself before focusing, so the input is visible and interactive for direct
  canvas text placement.
- Focused text/inline matrix passed (`15 passed`), including the real Qt widget
  stacking regression. Structured verification passed with Ruff, compile,
  quality gate `282 passed`, preprocessing gate `103 passed`, and whitespace
  checks. The task card is
  `docs/agent/tasks/2026-07-21-inline-text-layering.md`.
- The GUI must be restarted after this checkpoint; the screenshot supplied by
  the user predates this fix.

## Empty selection visibility follow-up - completed 2026-07-21

- The editor now distinguishes an empty selection from the compatibility
  Background row with localized `未选择对象` / `No object selected` feedback.
  Clearing generated or static selection returns to this state, while explicit
  background activation still reports Background.
- Focused behavior checks pass (`4 passed`); structured and default changed/type
  verification both pass with quality gate `282 passed` and preprocessing gate
  `103 passed`. The task card is
  `docs/agent/tasks/2026-07-21-empty-selection-visibility.md`.
- A running GUI must be restarted to load the new source; the launcher probe
  confirms the canonical root is `D:\PolyNexus`.

## Strong editor feedback mode - implementation complete, checkpoint blocked 2026-07-21

- Generated chart selection now renders transient blue dashed frames for text,
  rectangle, line, arrow, curve, and rendered series bounds. Frames stay
  outside the persistent artist map and are absent during generated export.
- Static annotation selection now has a transient blue dashed scene frame below
  handles. It is hidden by `render_scene()` exports, removed on Escape/clear/
  rebuild, and does not enter annotation history. The object tree preserves the
  background row for compatibility but clears its selection state when there is
  no editable object and scrolls matching nested rows into view.
- Focused matrix passed: `127 passed` for annotation canvas, layout, and
  workflow tests; renderer/workflow selection and export checks passed with
  `20 passed`. Changed modules compile and `git diff --check` passes.
- The task card is valid after adding numbered implementation steps. `ruff
  0.15.22` and `pyright 1.1.411` are now installed in the bundled Python
  runtime and the verifier reaches the quality gate. The quality gate remains
  blocked by Windows permission errors while cleaning `.pytest_tmp`; the full
  combined editor matrix also retains the known Qt access violation in the
  legacy `LayerTreeItem.setData()` path.
- The atomic checkpoint could not be created because this sandbox identity lacks
  write permission for `.git/index` and `.git/objects`; no push, merge, or
  cleanup was performed, and pre-existing untracked drafts remain untouched.

## Unified editor interaction architecture — completed 2026-07-21

- Connected the Qt-independent `EditorInteractionController` to static
  `AnnotationCanvas` creation, body drag, handle drag, cancellation, and the
  generated ChartEditor tool/gesture lifecycle. Creation tools return to
  Select, and generated object mode continues to deactivate Matplotlib
  navigation before annotation gestures.
- Added `GeneratedInteractionAdapter` and immutable `HitTarget` records so
  generated text, line, curve, rectangle, legend, and point targets expose a
  consistent object/body/handle/cursor contract while existing edit-session
  commands remain the history authority.
- Added focused adapter/controller tests and a real Qt static creation gesture
  regression. Focused interaction/workflow matrix: `115 passed`; all
  ChartEditor/AnnotationCanvas regressions: `465 passed`.
- Structured and default verifiers passed: Ruff/compile, quality gate `282
  passed`, preprocessing gate `103 passed`, and whitespace checks. Task card:
  `docs/agent/tasks/2026-07-21-unified-editor-interaction-architecture.md`.
- Code checkpoint: `36a0cc5`; local mainline finish completed through
  `scripts/repo_maintenance.py` in `8fecc26`.

## Navigation toolbar interaction conflict — completed 2026-07-21

- Generated object-edit mode now hides Matplotlib's pan/zoom toolbar, which was
  drawing the orange zoom rubber-band and intercepting annotation drags.
- Selecting a generated text, line, arrow, curve, or rectangle tool now exits
  any active navigation mode before the gesture begins; static preview mode
  retains the navigation toolbar.
- Focused layout/workflow tests pass (`49 passed`). Task card:
  `docs/agent/tasks/2026-07-21-navigation-toolbar-interaction-conflict.md`.

## Curve body hit regression — completed 2026-07-21

- Generated curve body picking now samples the quadratic path in data space,
  transforms it through the rendered artist into pixels, and reuses the
  existing segment hit tolerance. This fixes visible-stroke misses on
  logarithmic axes while retaining the original artist fallback.
- The curve body can now enter the existing preview drag transaction; endpoint
  and control-point movement remain persisted through the existing geometry
  command path.
- Focused workflow, curve, and hit-testing tests pass (`47 passed`); the task
  verifier passes with Ruff, compile, quality gate (`282 passed`), preprocessing
  gate (`103 passed`), and whitespace checks.

## Generated canvas drag regression — completed 2026-07-21

- Text body hit testing now uses the rendered artist window extent, so labels
  remain selectable when logarithmic-axis data coordinates make the old fixed
  fallback bounds inaccurate.
- Generated drag viewport snapshots now retain X/Y axis scales. Non-linear
  axis body movement uses the active artist transform and pointer pixel delta;
  linear axes retain the exact data-coordinate movement contract.
- Focused generated drag/workflow tests pass (`31 passed`). The structured
  verifier passes for task card
  `docs/agent/tasks/2026-07-21-generated-canvas-drag-regression.md`, including
  Ruff, compile, quality gate (`282 passed`), preprocessing gate (`103 passed`),
  and whitespace checks.
- The pre-existing untracked drafts and diagnostics remain intentionally
  untouched; no push or mainline merge was performed for this follow-up.

> Last updated: 2026-07-20

## Editor interaction reliability — completed 2026-07-20

- Added direct body-drag transactions for static annotations and generated
  text/rectangle/curve objects. Handles now resize text boxes as well as
  rectangles, curve defaults use a distance-aware control point, line body
  movement preserves both endpoints, and generated selection redraw preserves
  manual axes limits.
- The context style bar is a fixed-height overlay surface, so tool/selection
  changes do not add or remove canvas layout height. Drag preview remains
  non-persistent until release; release creates one edit-session/canvas history
  entry and undo/redo restores the exact geometry.
- Focused interaction matrix: `109 passed`; remaining ChartEditor-related
  modules: `156 passed`; targeted legacy ChartEditor drag/undo/static checks:
  `7 passed`. Structured verifier passed for task card
  `docs/agent/tasks/2026-07-20-editor-interaction-reliability.md`.
- Known limitation remains the pre-existing Windows Qt access violation in the
  legacy `LayerTreeItem.setData()` compatibility path when the full
  `tests/test_chart_editor*.py` set is combined; stable focused batches pass.
- Local checkpoint commit: `132bf912` (`fix(editor): stabilize direct canvas
  interactions`). The explicit finish metadata is being merged to local
  `main`; no push is performed. All pre-existing untracked drafts/diagnostics
  remain intentionally untouched.

## Local finish verification — recorded 2026-07-20

- The completed editor-workflow branch and the local `main` worktree both
  resolve to `5e973d30`; the feature code is already locally integrated.
- Fresh structured verification passed with
  `python scripts/verify.py --task docs/agent/tasks/2026-07-20-editor-workflow-completion.md --changed --types`.
- Fresh default verification passed with
  `python scripts/verify.py --changed --types`; the quality gate reported
  `282 passed` and the preprocessing optimization gate reported `103 passed`.
- The focused completion matrix reported `51 passed`. Existing untracked
  design drafts, acceptance notes, temporary diagnostics, and legacy worktrees
  were intentionally left untouched; the worktree remains unregistered and is
   not eligible for automatic removal.

## Editor visual polish — completed 2026-07-20

- The editor shell now gives the canvas expanding space, uses a readable
  text-under-icon tool rail with grouped history/export actions, keeps all
  inspector tabs visible without scroll arrows, and exposes selection actions
  beside the object/layer tree.
- Focused visual/editor tests pass (`34 passed`); `tests/test_chart_editor.py`
  passes independently (`238 passed`) and the workflow suite passes
  independently (`19 passed`). Structured and default changed/type verifiers
  both pass with quality gate `282` and preprocessing gate `103`.
- A combined Qt-heavy invocation can still trigger a Windows access violation
  inside the pre-existing `LayerTreeItem.setData` compatibility path; this is
  recorded in the task card and is not claimed as resolved by this UI-only
  slice.
- Local finish sequence is ready: source branch `codex/origin-editor-usable-controls`
  is at `943411b2`, target `main` is clean at `0086ca40`, and the source-only
  untracked drafts and diagnostics remain intentionally untouched.

## Origin-like editor mainline integration — completed 2026-07-20

- Integrated the tested Origin-like annotation and generated-canvas
  interactions into `codex/origin-editor-usable-controls` without replacing
  the current object tree, batch editing, comparison, templates, export, or
  canonical GUI launcher.
- Text, line, arrow, curve, and rectangle creation now share direct-canvas
  preview/commit behavior; static and generated geometry handles remain
  undoable and export excludes editor overlays.
- Fixed the release router so generated `plot_series` point edits and legend
  drags commit through the preview transaction instead of falling back to the
  legacy document-diff path, which had discarded preview-only changes.
- Verification evidence: `238 passed` for `tests/test_chart_editor.py`,
  `120 passed` for the remaining focused Origin-like editor/layout/workflow
  matrix, `66 passed` for the generated drag/geometry/render/core matrix;
  Ruff, compileall, and `git diff --check` passed. The prescribed structured
  verifier is the final repository gate for this checkpoint.
- Task card: `docs/agent/tasks/2026-07-20-origin-like-editor-mainline-integration.md`.

## Chart editor workflow completion — completed 2026-07-20

- Completed the remaining editor workflow slice on
  `codex/origin-editor-usable-controls`: structured corrupt/unsupported
  document diagnostics, undoable horizontal/vertical distribution and
  visibility, a hierarchical layer tree with legacy row compatibility, context
  menus and scoped shortcuts, data-free chart templates, format painter,
  previewed atomic batch editing, side-by-side chart comparison, working-vs-
  published revision diff, and named export presets.
- Focused editor/core/gallery regression command passed with `354 passed`.
- Structured verifier passed:
  `python scripts/verify.py --task docs/agent/tasks/2026-07-20-editor-workflow-completion.md --changed --types`.
  Default verifier also passed:
  `python scripts/verify.py --changed --types`; quality-gate focused tests
  passed (`282`) and preprocessing optimization tests passed (`103`).
- Known limitation: the revision comparison UI presents normalized document
  and asset-count differences; it does not perform a pixel-level image diff.

## Current checkpoint

- Worktree lifecycle manager added on 2026-07-20. Agent-owned worktrees can be
  registered, marked pending cleanup only after a clean Git state, archived into
  replayable WIP bundles, and removed only after branch/HEAD checks and a
  one-hour cooldown. Existing unregistered worktrees are intentionally retained.

- Unified GUI worktree launcher completed on 2026-07-20. The desktop launch path
  now uses `scripts/launch_gui.py` from the canonical `D:\PolyNexus`
  worktree; the launcher validates the imported package path, exposes branch
  and commit diagnostics, and preserves explicit worktree selection without
  guessing among isolated worktrees. Task card:
  `docs/agent/tasks/2026-07-20-unified-gui-worktree-launcher.md`. Focused
  launcher tests pass (6); the task-scoped verifier passes, including Ruff,
  compile, core quality (281), preprocessing optimization (103), memory, and
  whitespace checks; both system and bundled Python diagnostics resolve to
  `D:\PolyNexus\polynexus\__init__.py`.
- Final goal audit on 2026-07-19: the prescribed default verifier
  `python scripts/verify.py --changed --types` passes after all checkpoints;
  memory, compile, core quality gate (281), preprocessing optimization gate
  (103), and whitespace checks are green. The broader
  `python scripts/verify.py --changed --types --full --boundary` was attempted
  and timed out after 244 seconds without emitting a failure diagnostic; this
  remains a verification limitation, not evidence of a pass.
- Editor tool shortcuts and complete alignment surface completed on 2026-07-19.
  Canvas-scoped V/T/L/A/R/Del shortcuts avoid intercepting text fields, while
  window-scoped save, project export, undo, and redo remain available. All six
  alignment modes are reachable from the selection-aware batch controls.
  Shortcut/layout/editor suite passes (249). Task card:
  `docs/agent/tasks/2026-07-19-editor-shortcuts-and-alignment-surface.md`.
- Editor icon toolbar and one-command drag transactions completed on
  2026-07-19. Toolbar actions now use deterministic vector icons with
  translated tooltips. Generated drag motion is preview-only while a session
  is active; release commits one `ReplaceObjectCommand`, then persists the
  result, while Escape restores the original snapshot. Full focused
  toolbar/transaction/drag/editor slice passes (252). Task card:
  `docs/agent/tasks/2026-07-19-editor-toolbar-and-drag-transactions.md`.
- Chart gallery search, sorting, batch export, and revision status completed on
  2026-07-19. Active gallery cards can be filtered by title/id/status, sorted
  by title or working/published revision, checked for selected batch export,
  and show working/published revision badges. The manifest-only boundary is
  unchanged. Focused chart gallery/viewer suite passes (26). Task card:
  `docs/agent/tasks/2026-07-19-chart-gallery-search-sort-batch.md`.
- Undoable batch alignment and grouping completed on 2026-07-19. The core now
  supports left/center/top alignment plus group/ungroup as one `EditSession`
  command each, preserving geometry dimensions and rejecting locked or
  unsupported selections before mutation. ChartEditor exposes compact actions
  only for multi-selection. Focused batch/core/layout suite passes (31); the
  task-scoped verifier passes. Task card:
  `docs/agent/tasks/2026-07-19-batch-alignment-and-grouping.md`.
- Object tree search, multi-selection state, and locking completed on
  2026-07-19. The object tree now filters by id/name/type while retaining the
  background row, uses extended selection, and exposes ordered selected ids
  with the first id preserved for existing Inspector/canvas routes. Locking is
  an undoable `SetLockCommand`; locked objects continue to be selectable but
  existing capability gates reject normal edits. Focused object-tree/core
  selection suite passes (27). Task card:
  `docs/agent/tasks/2026-07-19-object-tree-selection-and-locking.md`.
- Editor safety and self-contained project export completed on 2026-07-19.
  `ChartEditor.closeEvent()` now offers Save/Discard/Cancel, keeps dirty state
  on failed or exceptional saves, and does not prompt for clean editors. The
  core `figure_project_bundle` service creates an atomic relocatable
  `.pnproject.zip` containing the normalized document, figure assets, resolved
  sources, and SHA-256 manifest; it refuses existing destinations and rejects
  missing or run-root-escaping sources. Focused close/package/editor-export
  suite passes (28). Task card:
  `docs/agent/tasks/2026-07-19-editor-safety-and-project-export.md`.
- Chart viewer provenance and historical recovery completed on 2026-07-19.
  `ChartViewer` now consumes selected figure entry/document context and a
  figure-specific data resolution, with raw-data compatibility only when no
  persisted source metadata exists. Run-relative CSV sources resolve through
  the entry run root; missing sources produce an explicit warning while the
  image preview remains usable. The recovery action now uses `ChartGallery`,
  preserving the active manifest gallery. Focused provenance/viewer/recovery
  suite passes (43); the task-scoped verifier passes, including quality gate
  (281) and preprocessing optimization gate (103). Task card:
  `docs/agent/tasks/2026-07-19-chart-data-provenance-and-recovery.md`.
- Chart gallery visual polish completed on 2026-07-19: the three-column layout remains, `ChartThumbnail` now has a unified card surface, and the blue border follows hover while selection uses a low-emphasis theme focus color. Task card: `docs/agent/tasks/2026-07-19-chart-gallery-visual-polish.md`; focused suite: 17 passed. The verifier tooling is restored and the prescribed changed/type command passes.
- Chart gallery header polish completed on 2026-07-19: the plots page now has a localized gallery title/count, grouped recovery action, and a theme-aware toolbar container; the focused chart/gallery/startup slice passes 21 tests. The verifier tooling is restored and the prescribed changed/type command passes.
- Follow-up fix completed on 2026-07-19: `ChartGallery.retranslate()` now updates filters, actions, badges, and card labels after language changes, removing the mixed Chinese/English gallery state. Focused chart/gallery/startup slice passes 25 tests; restart is required for an already-running GUI process.
- OriginLab integration is implemented and locally merged into `main`. The
  ChartEditor top export menu exposes Origin, and run-relative generated-figure
  CSV sources resolve through the gallery `run_root`; native export now shows
  and activates the Origin graph when available; capability probing also reads
  the Windows user environment registry when the running GUI has a stale
  `os.environ`; object documents retain the editable Origin mode while static
  documents retain visual-fidelity fallback, and native layers rescale after
  plots are added; all series now reuse one native Graph; source axis scales
  are forwarded, including logarithmic Y; see decisions `0010` and `0011`.
- The local `main` fast-forward merge is `583709ad`; the branch is not pushed.
- The focused Origin/editor verification currently passes: 44 Origin-related
  tests plus the new 16-test source/style fidelity slice, 3 GUI-startup checks,
  and 238 ChartEditor regression tests. The
  prescribed verifier command passes after restoring the workflow scripts and
  normalizing the legacy decision metadata; the evidence is recorded in the
  current verifier-restoration checkpoint.
- A live style smoke export through the configured OriginPro installation
  returned `success/originpro` for a synthetic five-plot document and was
  inspected in-process: one Graph, five plots, logarithmic Y, document colors,
  five 1.2-point display line widths, 0.8-point `x/x2/y/y2` frame axes, five
  source sheets, and five sample names. The generated native `.opju` remains
  owned by Origin until that application closes; no user-owned Origin process
  was closed.
- Native multi-series export now binds each plot through `data_ref` instead of
  reusing the last imported dataframe; axis labels fall back to the first
  object-document panel, and plot presentation uses Origin's LabTalk width
  units. The task card is
  `docs/agent/tasks/2026-07-19-origin-single-graph-fidelity.md`.
- Follow-up Origin label polish converts Matplotlib mathtext to Origin-safe
  Unicode (`q (nm⁻¹)`, `I (a.u.)`) at the native adapter boundary; the focused
  Origin suite is now 18 passed. The task card is
  `docs/agent/tasks/2026-07-19-origin-label-display-polish.md`.
- The agent memory foundation is now present: `README.md`,
  `current-state.md`, this register, decision memory, and lesson memory.
- The older entries below were last reconciled on 2026-07-11. Treat their
  branch/PR status as historical context until each item is rechecked against
  the current mainline.

## Completed

- Added the root agent contract in `AGENTS.md`.
- Added the agent workflow, definition of done, task template, and testing matrix
  under `docs/agent/`.
- Added `scripts/verify.py` as the unified verification entry point.
- Added this external memory foundation under `docs/agent/memory/`.

## In progress

- AI preprocessing mainline is active on `codex/ai-preprocess-mainline-v2` from
  `main@4437bc90`. Foundation, semantic intents, DSC/IR/WAXS, and SAXS/NMR
  adapters are present; the current safety checkpoint adds scoped experience
  retrieval, decision audit records, original-config snapshots, hash rechecks,
  runtime negative-fraction evidence, and SAXS/NMR hard guards. Focused
  preprocessing/calibration tests pass (`79`); the broader orchestration subset
  passes (`244 passed, 1 skipped`). GUI confirmation, Golden/AI-off/fault gates,
  CI, and human scientific review remain pending. Focused Golden/synthetic,
  fault-injection, AI-off, and quality-gate checks now pass; local
  `quality_gate.py --all-tests` exceeded 304 seconds without reporting a
  failing test. The task card is
  `docs/agent/tasks/2026-07-13-ai-preprocessing-mainline.md`.
- Unified Tables results/export slice is merged in PR #12 at `3f050065`; the slice covers structured table templates/adapters, generic fallback, CSV/TSV/XLSX export, and clipboard extraction.
- Unified Tables GUI integration is active on `codex/unified-tables-gui-integration-v2` from main `3f050065`. The slice is limited to the structured result panel, MainWindow service/view-model consumption, workspace/history restore context, and persistence/retranslation regressions; editor/export reconciliation remains separate.
- DSC publication packs were reviewed and merged in PR #14 as `a5804d2a`, with the dedicated 600-DPI publication profile and standard/isothermal/non-isothermal evidence-gated providers. The dedicated main worktree is synchronized with `origin/main`.
- WAXS publication packs are in progress on `codex/waxs-publication-packs-v2` from `main@a5804d2a`. The slice is limited to static, temperature/time, and strain providers, editable 2D image-grid support, manifest-backed publication with a WAXS 600-DPI TIFF profile, and explicit legacy fallback isolation. Focused WAXS/shared regression and quality-gate evidence currently pass; scientific review, CI, push, and merge remain pending.
- Unified Tables contracts slice is implemented on `codex/unified-tables-contracts-v2`; PR #11 passed local and GitHub gates and received user data-contract review on 2026-07-13. Results service/export, GUI integration, DSC/WAXS packs, editor/export reconciliation, and AI preprocessing remain separate task cards.
- Mainline integration reconciliation completed the reviewed SAXS evidence-filtering slice in PR #10. Shared figure lifecycle compatibility, SAXS mode/evidence contract, cumulative review evidence, and temperature/strain filtering are recorded in the acceptance and memory documents; the squash merge is `70b299af`.
- GUI startup performance task completed on 2026-07-11. The application entry now uses deferred optional UI construction; focused startup and MainWindow persistence evidence is recorded in `docs/acceptance/2026-07-11-gui-startup-performance.md`.
- SAXS temperature/strain production cutover was rebased onto `origin/main` after PR conflict investigation. The current mainline already contains the strict shared-publisher route; the rebased PR adds entry-level regression coverage and keeps the design/task evidence without replacing newer provider code. Focused rebased tests pass; full repository pytest exceeded the five-minute runtime limit without a reported failing test. Human architecture/science review is pending before integration.
- Editor style-context hydration implementation completed on isolated branch `codex/editor-style-context`. Generated/document source switching now resets editor style controls, hydrates from the current document, and keeps static edit overlays on the static path. Focused style-context tests pass (5), focused generated/save/preset tests pass (12), and the editor regression matrix passes (267); task evidence is recorded in `docs/agent/tasks/2026-07-12-editor-style-context.md`, and human editor review is pending.
- Legacy gallery fallback strategy evaluation completed on isolated branch `codex/legacy-gallery-fallback-strategy`. The normal gallery remains manifest-only; historical recursive discovery stays behind the explicit recovery view and never silently changes the active run. Strategy evidence is recorded in `docs/superpowers/specs/2026-07-12-legacy-gallery-fallback-strategy.md` and decision memory `docs/agent/memory/decisions/0003-manifest-only-gallery-discovery.md`; no production code changed.
- GUI streamlining implementation completed on isolated branch `codex/gui-streamlining-interaction-plan`. The implementation adds explicit workspace modes, binds current results to persisted run IDs, makes the figure preview the canonical View route, fixes primary shortcuts and batch-manifest naming, removes verified duplicate top-bar routes, and preserves manifest-only gallery plus explicit legacy recovery. GUI focused regression matrix passes (452); evidence is recorded in `docs/superpowers/specs/2026-07-12-gui-streamlining-interaction-plan.md`, the implementation plan, and decision memory `docs/agent/memory/decisions/0004-gui-streamlining-last-wave.md`. Existing Ruff baseline findings remain in legacy GUI modules.

## Suggested next candidates

- Editor legend-box task completed on 2026-07-24 at `10d4c61`: generated
  legends now retain their rendered layout on selection, expose a transient
  non-exported Origin-style box with four handles, persist corner-resize W/H
  through one undoable style transaction, and surface the same geometry in the
  inspector. Evidence: task card
  `docs/agent/tasks/2026-07-24-editor-legend-box.md`; focused matrix `272
  passed`, changed-file verifier plus quality gates `282 passed` and `103
  passed` using a dedicated pytest base temp directory.

1. Add incremental Ruff checks for changed files, then ratchet toward full-repo
   cleanliness.
2. Add a small index or search adapter for memory entries only after the Markdown
   source of truth is being maintained consistently.
3. If the startup target must improve beyond the current approximately 2.7-second fresh-process probe, separately evaluate scientific-stack packaging and lazy technique-registry loading.

## Update protocol

Every active task should record its status, blocker, next action, and evidence
link here when that information will matter to a later agent.
