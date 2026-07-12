# GUI Streamlining Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved GUI streamlining interaction contract without removing scientific capability, evidence, history, sample workflows, figure recovery, or export contracts.

**Architecture:** Introduce one explicit `WorkspaceMode` contract for analysis,
joint analysis, and samples; keep the existing service/mixin boundaries; then
move duplicated actions to their contextual owners. Work in ordered slices so
navigation, result identity, plot entry, and responsive cleanup can each be
verified independently before any duplicate route is removed.

**Tech Stack:** Python 3.10+, PySide6, pytest, SQLite, existing PolyNexus GUI
mixins/services, Ruff, and the current bilingual translation system.

---

## Scope and execution rules

- Do not touch the dirty `D:\PolyNexus` worktree; all implementation stays in
  `codex/gui-streamlining-interaction-plan`.
- Do not change scientific algorithms, analysis result schemas, SQLite schemas,
  manifest contracts, or historical output data.
- Preserve `recent_projects` as the QSettings key; only visible labels may change.
- Keep manifest-only active gallery behavior and the separate legacy recovery view.
- Run the focused tests after each task and commit each coherent slice.
- Do not delete a duplicate route until the contextual replacement has a focused
  test, bilingual label coverage, disabled/error-state coverage, and minimum-size
  layout coverage.

## File responsibility map

### Create

- `polynexus/gui/workspace_mode.py`: canonical workspace enum and legacy alias normalization.
- `tests/test_workspace_mode.py`: pure normalization contract tests.
- `tests/test_ui_function_streamlining.py`: GUI ownership, labels, and minimum-size regression tests.

### Modify

- `polynexus/gui/main_window.py`: workspace initialization, single joint route,
  top-bar ownership, and tab/sidebar integration.
- `polynexus/gui/main_window_navigation_mixin.py`: normalize technique, joint,
  and sample navigation into `WorkspaceMode`.
- `polynexus/gui/main_window_workspace_mixin.py`: derive titles/tasks from mode,
  not pseudo-technique IDs.
- `polynexus/gui/main_window_sample_hub_mixin.py`: centralize workspace switching
  and contextual sample-to-joint routing.
- `polynexus/gui/main_window_run_mixin.py`: keep top-bar execution analysis-only
  and delegate joint busy state to `JointAnalysisHub`.
- `polynexus/gui/widgets/joint_analysis_hub.py`: selection/busy enablement and
  one run request contract.
- `polynexus/gui/analysis_history_service.py`: persist current-run identity and
  exclude the current run from comparison candidates.
- `polynexus/gui/main_window_history_mixin.py`: synchronize confirmation and
  keep optimization review in history/review context.
- `polynexus/gui/main_window_results_mixin.py`: one Results surface for summary,
  tables, comparison, confirmation, and result export.
- `polynexus/gui/main_window_guidance_panels_mixin.py`: remove only the visible
  duplicate work-memory card while keeping reusable summary services.
- `polynexus/gui/convergence_viewer.py`: keep AI-only review and active sample DB
  resolution.
- `polynexus/gui/widgets/chart_viewer.py`: contextual preview/view/edit actions
  and responsive gallery layout.
- `polynexus/gui/main_window_figure_mixin.py`: remove dependencies on deleted
  top-level plot actions; keep explicit legacy recovery.
- `polynexus/gui/figure_window_service.py`: make preview actions self-contained.
- `polynexus/gui/main_window_shell_mixin.py`: remove only duplicate View-menu
  review action and retain report-package export.
- `polynexus/gui/main_window_retranslate_mixin.py`: retranslate surviving controls,
  history headers, and new workspace labels.
- `polynexus/gui/i18n.py`: Chinese/English labels, empty states, and errors.
- `polynexus/gui/shortcuts.py`: bind shortcuts to canonical contextual actions.
- `polynexus/gui/widgets/sample_browser.py`: preserve sample operations while
  naming batch manifest export by its actual scope.
- `polynexus/data/sample_db.py`: expose active database path without schema changes.
- `polynexus/app.py`: stop injecting a duplicate global review action only after
  the contextual review route is verified.
- `README.md`, `docs/maintenance-boundaries.md`, `docs/maintenance.md`: document
  stable GUI flow and 1280x820/960x600 verification expectations.

---

### Task 1: Add the workspace-mode contract

**Files:** create `polynexus/gui/workspace_mode.py` and
`tests/test_workspace_mode.py`; modify navigation/workspace mixins only after
the pure contract is green.

- [ ] Write tests for `WorkspaceMode.ANALYSIS`, `.JOINT`, and `.SAMPLES`, plus
  normalization of `joint`, `joint.quick`, `joint.compare`, `samples`, and
  unknown values.
- [ ] Run `python -m pytest tests/test_workspace_mode.py -q`; expected initial
  failure is the missing module.
- [ ] Implement `normalize_workspace_mode(value)` so canonical enum values pass
  through, all `joint.*` aliases map to `JOINT`, `samples` maps to `SAMPLES`,
  `analysis` maps to `ANALYSIS`, and unknown non-empty values raise `ValueError`.
- [ ] Run the focused test; expected result is all normalization cases passing.
- [ ] Commit `feat(gui): add explicit workspace mode contract`.

### Task 2: Centralize navigation and joint execution

**Files:** `main_window.py`, `main_window_navigation_mixin.py`,
`main_window_workspace_mixin.py`, `main_window_sample_hub_mixin.py`,
`main_window_run_mixin.py`, `widgets/joint_analysis_hub.py`, and
`tests/test_ui_function_streamlining.py`.

- [ ] Add failing tests asserting that real technique IDs select `ANALYSIS`, all
  joint aliases select one Joint workspace, samples select `SAMPLES`, and a
  sample/batch shortcut preserves selected IDs when entering Joint Analysis.
- [ ] Add `self._workspace_mode` initialization and one transition helper; route
  sidebar and sample actions through it without changing the existing widget
  signals.
- [ ] Keep the top bar Run/Replot disabled outside analysis; make Joint Analysis
  expose exactly one selection-aware run action with a busy-state guard.
- [ ] Run `python -m pytest tests/test_workspace_mode.py tests/test_ui_function_streamlining.py tests/test_main_window_navigation_mixin.py tests/test_main_window_workspace_mixin.py tests/test_main_window_sample_hub_mixin.py tests/test_main_window_run_mixin.py -q`.
- [ ] Commit `feat(gui): centralize workspace and joint navigation`.

### Task 3: Bind Results and History to current-run identity

**Files:** `analysis_history_service.py`, `main_window_history_mixin.py`,
`main_window_results_mixin.py`, `main_window_guidance_panels_mixin.py`,
`convergence_viewer.py`, and related tests.

- [ ] Add failing tests for persisted current-run ID, exclusion of current run
  from comparison candidates, and confirmation synchronization between Results
  and History.
- [ ] Implement the smallest service-level current-run field and route all
  confirmation writes through the existing persistence service.
- [ ] Consolidate visible Results content into summary, structured tables, and
  review actions; keep work-memory helpers callable but remove only their
  duplicate visible card.
- [ ] Move Optimization Review ownership to Results/History context and keep
  AI-only querying plus active sample database resolution.
- [ ] Run `python -m pytest tests/test_analysis_history_service.py tests/test_main_window_results_mixin.py tests/test_main_window_history_mixin.py tests/test_convergence_viewer.py tests/test_main_window_persistence.py -q`.
- [ ] Commit `feat(gui): consolidate result and history review ownership`.

### Task 4: Make plot actions contextual

**Files:** `widgets/chart_viewer.py`, `main_window_figure_mixin.py`,
`figure_window_service.py`, `main_window_shell_mixin.py`, `main_window.py`,
and chart/figure tests.

- [ ] Add failing tests asserting that selected-figure preview exposes the
  canonical View/Edit actions, that missing/disabled entries remain safe, and
  that the separate legacy recovery action does not replace active gallery state.
- [ ] Make preview View/Edit self-contained and remove only the redundant global
  View Current Figure route after equivalent behavior is covered.
- [ ] Remove duplicate gallery-card Edit wiring only after preview Edit is the
  canonical route; keep secondary assets and manifest capability routing intact.
- [ ] Keep active gallery manifest-only and preserve the explicit Historical
  Figure Recovery action.
- [ ] Run `python -m pytest tests/test_chart_viewer.py tests/test_figure_window_service.py tests/test_main_window_figure_mixin.py tests/test_plot_gallery_service.py tests/test_legacy_figure_recovery_service.py -q`.
- [ ] Commit `feat(gui): consolidate figure preview actions`.

### Task 5: Apply labels, shortcuts, and responsive contracts

**Files:** `i18n.py`, `main_window_retranslate_mixin.py`, `shortcuts.py`,
`widgets/sample_browser.py`, `data/sample_db.py`, `styles.py`, docs, and
`tests/test_ui_function_streamlining.py`.

- [ ] Add tests for Chinese/English surviving labels, all seven history headers,
  canonical report-package shortcut, batch-manifest naming, and no stale labels
  for removed duplicate actions.
- [ ] Implement only scope-specific label/tooltip changes and preserve QSettings
  keys, schema names, and existing export services.
- [ ] Add minimum-size checks at 1280x820 and 960x600 for Data, Results, Plots,
  History, Joint, and Sample actions; allow wrapping but never hide primary
  actions.
- [ ] Run `python -m pytest tests/test_ui_function_streamlining.py tests/test_main_window_retranslate_mixin.py tests/test_main_window_shell_mixin.py tests/test_sample_browser.py tests/test_chart_viewer.py -q`.
- [ ] Commit `feat(gui): finalize streamlined labels and layout checks`.

### Task 6: Remove only verified duplicate routes

**Files:** surviving duplicates in `main_window.py`, `main_window_shell_mixin.py`,
`app.py`, translation entries, and focused tests.

- [ ] Compare the retention checklist against the actual diff and identify each
  candidate route by object name and signal target.
- [ ] Delete only the duplicate top-bar review route, duplicate global plot view
  route, duplicate gallery edit route, or pseudo-joint alias whose replacement
  tests passed; keep compatibility aliases in normalization code.
- [ ] Run `rg -n "action_convergence_viewer|_btn_convergence_viewer|_btn_view_current_figure|joint\."` and confirm every remaining match is either a canonical route, alias normalization, or test evidence.
- [ ] Commit `refactor(gui): remove verified duplicate entry points`.

### Task 7: Full verification and manual handoff

**Files:** final docs and task evidence only after code is stable.

- [ ] Run the complete focused GUI matrix covering workspace, navigation, run,
  results, history, sample, joint, plots, editor, translation, and persistence.
- [ ] Run changed-file Ruff, compile checks, `git diff --check`, and the quality
  gate. Record exact outputs in the task card.
- [ ] Manually inspect Chinese and English at 1280x820 and 960x600, including
  empty/loading/error/recovery states and keyboard focus.
- [ ] Update maintenance boundaries and active memory with the final ownership
  map; do not claim completion if any deletion candidate lacks a test.
- [ ] Commit `docs(gui): record streamlining verification evidence`.

## Completion checklist

- [ ] No scientific module or result contract was removed.
- [ ] No historical data or legacy recovery path was deleted.
- [ ] Each action has one canonical owner or an explicitly contextual duplicate.
- [ ] Results and History share current-run/confirmation state.
- [ ] Plots retains manifest gallery, preview/editor/view, and explicit recovery.
- [ ] Sample and Joint preserve selection context and busy safety.
- [ ] Chinese/English and minimum-size checks pass.
- [ ] Focused and full verification outputs are recorded.
