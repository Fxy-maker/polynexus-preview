# SAXS GUI Mask Editor Confirmed Rerun Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide a static 2D SAXS mask review dialog that emits a validated candidate and starts the existing single rerun path.

**Architecture:** The core preprocessing result exposes the configured base mask as a detached array. A GUI service validates whether the current result is eligible, while a dedicated Qt dialog owns only transient display/edit state. MainWindow consumes the dialog's public candidate signal and passes it to the existing worker boundary.

**Tech Stack:** Python, NumPy, PySide6, pytest, existing SAXS mask candidate contract.

---

### Task 1: Specify and test the public boundaries

**Files:**
- Create: `tests/test_saxs_gui_mask_editor_confirmed_rerun.py`

- [x] **Step 1: Write RED tests**

Cover base-mask transport from `preprocess_pipeline()` to `SAXSEngine.result.raw_data`, static-only editor eligibility, dialog confirmation/cancel behavior, and `_run_single(mask_edit_candidate=...)` forwarding.

- [x] **Step 2: Run focused RED**

```powershell
python -m pytest -q tests/test_saxs_gui_mask_editor_confirmed_rerun.py -o addopts= --basetemp=D:\PolyNexus-test-runs\pytest\saxs-gui-mask-editor-red
```

Expected: failures for the missing base-mask payload, editor dialog, and run-mixin candidate boundary.

Observed: pytest exited `1` during collection because the new GUI service was
not yet present; this was the expected missing-boundary RED.

### Task 2: Implement the static editor vertical slice

**Files:**
- Modify: `polynexus/core/saxs_engine/preprocess.py`
- Modify: `polynexus/core/saxs.py`
- Create: `polynexus/gui/saxs_mask_edit_service.py`
- Create: `polynexus/gui/widgets/saxs_mask_editor.py`
- Modify: `polynexus/gui/main_window_results_mixin.py`
- Modify: `polynexus/gui/main_window_run_mixin.py`
- Test: `tests/test_saxs_gui_mask_editor_confirmed_rerun.py`

- [x] **Step 1: Return the configured mask baseline**

Add a detached boolean `mask_edit_base_mask` to the existing single-image preprocessing payload and copy it into `result.raw_data`; sequence loading does not expose an editor context.

- [x] **Step 2: Add eligibility and dialog boundaries**

Implement a pure context builder and a Qt dialog/canvas. The dialog only emits a candidate after `confirm_mask_edit_candidate()` succeeds; cancel and zero-change paths emit nothing.

- [x] **Step 3: Connect results action to one rerun**

Add an action in the existing results review area for eligible static 2D results. Call `_run_single(mask_edit_candidate=candidate)` and append the candidate keyword only for that invocation.

- [x] **Step 4: Run focused GREEN**

```powershell
python -m pytest -q tests/test_saxs_gui_mask_editor_confirmed_rerun.py -o addopts= --basetemp=D:\PolyNexus-test-runs\pytest\saxs-gui-mask-editor-green
```

Expected: all tests pass with no candidate application outside static 2D.

Observed: `5 passed` in `0.59s`, including reset-to-no-change and cancel
no-op behavior.

### Task 3: Verify and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-30-saxs-gui-mask-editor-confirmed-rerun.md`
- Modify: `docs/acceptance/2026-07-30-saxs-gui-mask-editor-confirmed-rerun.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] **Step 1: Run structured verification**

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-30-saxs-gui-mask-editor-confirmed-rerun.md --changed --types
```

- [x] **Step 2: Run SAXS matrix, storage report/dry-run, and diff check**

Require a complete pytest summary and exit code `0`; do not execute
`test_storage.py --apply`.

- [x] **Step 3: Create the explicit allowlist checkpoint**

```powershell
python scripts/auto_commit.py --message "feat(saxs): add confirmed mask editor rerun" --files polynexus/core/saxs_engine/preprocess.py polynexus/core/saxs.py polynexus/gui/saxs_mask_edit_service.py polynexus/gui/widgets/saxs_mask_editor.py polynexus/gui/main_window_results_mixin.py polynexus/gui/main_window_run_mixin.py tests/test_saxs_gui_mask_editor_confirmed_rerun.py docs/superpowers/specs/2026-07-30-saxs-gui-mask-editor-confirmed-rerun-design.md docs/superpowers/plans/2026-07-30-saxs-gui-mask-editor-confirmed-rerun.md docs/agent/tasks/2026-07-30-saxs-gui-mask-editor-confirmed-rerun.md docs/acceptance/2026-07-30-saxs-gui-mask-editor-confirmed-rerun.md docs/agent/memory/active-work.md
```
