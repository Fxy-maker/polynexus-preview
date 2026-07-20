# Active Work

> Last updated: 2026-07-20

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

1. Add incremental Ruff checks for changed files, then ratchet toward full-repo
   cleanliness.
2. Add a small index or search adapter for memory entries only after the Markdown
   source of truth is being maintained consistently.
3. If the startup target must improve beyond the current approximately 2.7-second fresh-process probe, separately evaluate scientific-stack packaging and lazy technique-registry loading.

## Update protocol

Every active task should record its status, blocker, next action, and evidence
link here when that information will matter to a later agent.
