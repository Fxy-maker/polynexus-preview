# DSC Lifecycle Closure Implementation Plan

 > **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove and, if needed, minimally connect all three DSC modes to the shared figure lifecycle through history restore.

**Architecture:** Keep DSC providers as the source of publication roles and use existing manifest, gallery, editor-project, and export services as the only cross-layer contracts. Add a parameterized regression that exercises the same lifecycle for standard, isothermal, and non-isothermal DTOs, with a Qt restore check at the boundary.

**Tech Stack:** Python, pytest, PySide6 offscreen tests, existing PolyNexus figure and export services.

---

### Task 1: Add the failing DSC lifecycle regression

**Files:**
 - Create: `tests/test_dsc_lifecycle_closure.py`
 - Modify: `docs/agent/tasks/2026-07-25-dsc-lifecycle-closure.md`

 - [x] **Step 1: Write one parameterized test for provider-to-gallery/editor/export/history behavior.**

   Build one standard engine from `tests/eval/synth_data/dsc_synth_heating_standard.xy`, one isothermal `SimpleNamespace` with a qualified Avrami result, and one non-isothermal `SimpleNamespace` with two conversion curves and a qualified Kissinger result. For each mode, publish with `FigureProductionPublisher`, assert active Gallery entries, load the first document, call `FigureProjectService.save_working` and `publish`, copy the output through export-context helpers, and restore a history record through `MainWindow._restore_history_record`.

 - [x] **Step 2: Run the new test before changing production code.**

   Run:

   ```powershell
   $env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_dsc_lifecycle_red'
   python -m pytest tests/test_dsc_lifecycle_closure.py -q
   ```

   Expected: the test either passes for the already-connected path or fails at the first missing lifecycle contract; record the exact failure before any implementation change.

### Task 2: Implement only the missing product connection

**Files:**
 - Modify only the production file identified by the failing assertion.
 - Modify: `tests/test_dsc_lifecycle_closure.py` only when the failure proves the test setup is invalid.

 - [x] **Step 1: Add the smallest failing-case fix.** No production change was required; the regression passed against the existing shared contracts after correcting its fixture and Qt setup.

   Preserve the existing provider IDs, publication roles, run-relative paths,
   and history routing. Do not add a DSC-specific branch to ChartGallery or
   MainWindow when a shared service contract already exists.

 - [x] **Step 2: Re-run the lifecycle regression.**

   ```powershell
   $env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_dsc_lifecycle_green'
   python -m pytest tests/test_dsc_lifecycle_closure.py -q
   ```

### Task 3: Run the DSC regression matrix and document acceptance

**Files:**
 - Create: `docs/acceptance/2026-07-25-dsc-lifecycle-closure.md`
 - Modify: `docs/agent/memory/current-state.md`
 - Modify: `docs/agent/memory/active-work.md`

 - [x] **Step 1: Run focused verification.**

   ```powershell
   $env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_dsc_lifecycle_focus'
   python -m pytest tests/test_dsc_lifecycle_closure.py tests/test_dsc_engine.py tests/test_dsc_figure_provider.py tests/test_dsc_publication_standard_provider.py tests/test_dsc_publication_isothermal_provider.py tests/test_dsc_publication_nonisothermal_provider.py tests/test_dsc_publication_cutover.py tests/test_dsc_workbench_figure_contracts.py tests/test_results_workbench_profiles.py tests/test_results_export_contracts.py tests/test_figure_project_service.py tests/test_chart_editor_save_mixin.py tests/test_export_context_service.py tests/test_main_window_persistence.py -q
   ```

 - [x] **Step 2: Run the structured verifier and record exact results.**

   ```powershell
   python scripts/verify.py --task docs/agent/tasks/2026-07-25-dsc-lifecycle-closure.md --changed --types
   ```

 - [x] **Step 3: Create the allowlisted checkpoint.**

   ```powershell
   python scripts/auto_commit.py --message "feat(dsc): close figure lifecycle" --files tests/test_dsc_lifecycle_closure.py docs/acceptance/2026-07-25-dsc-lifecycle-closure.md docs/agent/memory/current-state.md docs/agent/memory/active-work.md docs/superpowers/specs/2026-07-25-dsc-lifecycle-closure-design.md docs/superpowers/plans/2026-07-25-dsc-lifecycle-closure.md docs/agent/tasks/2026-07-25-dsc-lifecycle-closure.md
   ```
