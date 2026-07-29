# Native SAXS Strain Editor Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep an assetless diagnostic manifest entry visible while selecting a usable figure for the initial native Gallery-to-Editor route.

**Architecture:** Keep the behavior in the pure `select_plot_gallery_entry` service. Add one small helper that resolves a non-empty selection path from the entry, and use it only for the initial fallback selection; preferred-path matching and Manifest publication semantics remain untouched.

**Tech Stack:** Python, dataclasses, PySide6, pytest, native Windows Qt route acceptance.

---

### Task 1: Guard initial Gallery selection against empty assets

**Files:**
- Modify: `polynexus/gui/plot_gallery_service.py:382-407`
- Test: `tests/test_plot_gallery_service.py:287-326`

- [x] **Step 1: Write the failing test**

  Add `test_select_plot_gallery_entry_skips_assetless_diagnostic_for_initial_selection` with one assetless diagnostic entry followed by one ready entry with a real preview path. Assert that the ready entry ID and path are selected.

- [x] **Step 2: Run the focused test to verify the original failure**

  Run:

  ```powershell
  python -m pytest -q tests/test_plot_gallery_service.py -k assetless -vv
  ```

  Expected on the pre-fix implementation: the selection returns the first
  assetless entry and the assertion fails.

- [x] **Step 3: Write the minimal implementation**

  Add `_entry_selection_path(entry)` that returns the first non-empty value in
  `preview_path`, `primary_path`, `editable_path`, and `asset_paths`. Change
  only the no-preferred-path fallback to choose the first entry for which that
  helper is non-empty, while retaining the existing final fallback for an
  entirely assetless list.

- [x] **Step 4: Run the regression test to verify the fix**

  Run:

  ```powershell
  python -m pytest -q tests/test_plot_gallery_service.py -k assetless -vv
  ```

  Expected: `1 passed`.

### Task 2: Verify the native SAXS strain route and checkpoint the atomic change

**Files:**
- Verify: `tests/test_native_gui_real_route_capture.py`
- Verify: `scripts/verify.py`
- Checkpoint allowlist: `polynexus/gui/plot_gallery_service.py`, `tests/test_plot_gallery_service.py`, this task card, the matching spec, and this plan

- [x] **Step 1: Run the native focused route**

  Run with `QT_QPA_PLATFORM=windows` and an external basetemp. Expected:
  `1 passed, 16 deselected`, plus a generated
  `saxs_strain_editor.png` capture.

- [x] **Step 2: Run the focused Gallery/editor matrix and changed-file verifier**

  Run:

  ```powershell
  python -m pytest -q tests/test_plot_gallery_service.py tests/test_figure_window_service.py tests/test_main_window_persistence.py
  python scripts/verify.py --task docs/agent/tasks/2026-07-29-native-saxs-strain-editor-selection.md --changed --types
  git diff --check
  ```

  The split focused matrix passed (`29` Gallery/FigureWindow tests and `7`
  targeted MainWindow persistence tests). The combined three-file command
  exceeded the bounded tool timeout without a pytest summary and is not
  counted as a pass. The structured verifier passed with quality `290` and
  preprocessing `106`.

- [x] **Step 3: Create an explicit allowlist checkpoint**

  Use `scripts/auto_commit.py` with only the files listed in the task card.
  Do not include parallel memory edits, the full native visual acceptance
  card, capture directories, or test-storage directories. Code/doc checkpoint
  `941917e` was created; the subsequent doc-only status update is allowlisted
  separately.
