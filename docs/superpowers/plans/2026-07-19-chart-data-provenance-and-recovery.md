# Chart Data Provenance and Historical Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make chart viewers provenance-correct and make historical recovery use the correct gallery widget contract.

**Architecture:** Keep resolution in the existing GUI service boundary, using the persisted figure document and gallery entry as the source of truth. Keep `ChartViewer` presentation-only: it receives normalized table data and source status, while `ChartGallery` owns entry discovery and selection.

**Tech Stack:** Python 3.12, PySide6, pytest, existing figure-document and gallery services.

---

### Task 1: Add failing provenance resolver tests

**Files:**
- Create: `tests/test_figure_data_provenance.py`
- Test existing: `polynexus/gui/figure_window_service.py`

- [x] **Step 1: Write tests for absolute, run-relative, inline, and missing sources.**

  Use temporary files and a minimal normalized figure document. Assert the
  resolver returns the selected source rows and reports a structured missing
  source error instead of raising or using unrelated fallback data.

- [x] **Step 2: Run the focused tests and verify the expected failure.**

  Run:

  ```bash
  pytest -q tests/test_figure_data_provenance.py
  ```

  Expected: collection or attribute failure because the resolver API does not
  yet exist.

### Task 2: Implement the pure resolver

**Files:**
- Create or modify: `polynexus/gui/figure_window_service.py`
- Test: `tests/test_figure_data_provenance.py`

- [x] **Step 1: Implement one resolver entry point.**

  Add a function returning a small dataclass such as
  `FigureDataResolution(headers, rows, source_label, error)`. Resolve a plot's
  `data_ref` against `document["data_sources"]`, then resolve paths through
  `entry.run_root` for `run_relative` sources. Support CSV/TSV rows and explicit
  inline data without importing Qt widgets.

- [x] **Step 2: Run the resolver tests.**

  Run:

  ```bash
  pytest -q tests/test_figure_data_provenance.py
  ```

  Expected: all resolver tests pass.

### Task 3: Route viewer calls through provenance context

**Files:**
- Modify: `polynexus/gui/widgets/chart_viewer.py`
- Modify: `polynexus/gui/main_window_figure_mixin.py`
- Modify: `polynexus/gui/figure_window_service.py`
- Test: `tests/test_chart_viewer.py`
- Test: `tests/test_main_window_figure_mixin.py`

- [x] **Step 1: Add failing tests for entry-specific data and missing sources.**

  Assert that a viewer opened for entry A does not display fallback data from
  the current technique's result, and that missing data leaves the preview
  loaded while showing an explicit status.

- [x] **Step 2: Run the tests and confirm they fail for the current call path.**

  Run:

  ```bash
  pytest -q tests/test_chart_viewer.py tests/test_main_window_figure_mixin.py
  ```

- [x] **Step 3: Add optional entry/document context to `ChartViewer`.**

  Preserve the existing `raw_data` parameter for compatibility. Prefer the
  provenance resolver whenever an entry or document has source metadata, and
  populate the data table only from that resolution.

- [x] **Step 4: Pass the selected gallery entry from every open path.**

  Update `_open_current_figure_viewer()` and `ChartGallery._open_viewer()` so
  the selected entry travels with the figure path. Do not substitute the
  current result's raw data when the selected entry has its own document.

- [x] **Step 5: Run the focused viewer tests.**

  Expected: all modified viewer and main-window tests pass.

### Task 4: Fix historical recovery widget contract

**Files:**
- Modify: `polynexus/gui/main_window_figure_mixin.py`
- Test: `tests/test_main_window_figure_mixin.py`

- [x] **Step 1: Add a regression test that uses the real `ChartGallery` API.**

  Assert the recovery path constructs a gallery-capable widget, loads entries,
  keeps the active gallery object unchanged, and connects editor/status signals.

- [x] **Step 2: Run the regression test and observe the current mismatch.**

  Expected: failure because the current implementation instantiates
  `ChartViewer` and calls `load_entries()` on it.

- [x] **Step 3: Use `ChartGallery` for recovery entry browsing.**

  Preserve the existing isolated recovery window behavior. Connect its
  `edit_requested` and `summary_changed` signals as needed, and keep the active
  manifest gallery untouched.

- [x] **Step 4: Run the recovery tests.**

  Run:

  ```bash
  pytest -q tests/test_main_window_figure_mixin.py
  ```

### Task 5: Verify, document, and checkpoint

**Files:**
- Modify: `docs/agent/memory/active-work.md`
- Modify if needed: `docs/agent/memory/decisions/`

- [x] **Step 1: Run the task-scoped verifier.**

  ```bash
  python scripts/verify.py --task docs/agent/tasks/2026-07-19-chart-data-provenance-and-recovery.md --changed --types
  ```

- [x] **Step 2: Review the cumulative diff and update evidence.**

  Record the exact focused test counts, source-resolution behavior, and any
  unsupported legacy data formats in `active-work.md`.

- [x] **Step 3: Create the atomic checkpoint.**

  ```bash
  python scripts/auto_commit.py --message "fix(gui): bind chart viewers to figure data" --files polynexus/gui/figure_window_service.py polynexus/gui/widgets/chart_viewer.py polynexus/gui/main_window_figure_mixin.py tests/test_figure_data_provenance.py tests/test_chart_viewer.py tests/test_main_window_figure_mixin.py docs/agent/memory/active-work.md
  ```
