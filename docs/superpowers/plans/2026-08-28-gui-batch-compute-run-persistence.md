# GUI Batch ComputeRun Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended; not used for this inline checkpoint) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist one shared ComputeRun projection for each successful GUI batch row.

**Architecture:** BatchWorker supplies explicit locators; the GUI history mixin
passes rows to a Qt-free helper that reuses the existing single-run persistence
contract with a per-row context.

**Tech Stack:** Python, PySide6, SampleDB, pytest.

---

### Task 1: Per-row persistence contract

**Files:**
- Modify: `tests/test_analysis_run_service.py`
- Modify: `polynexus/gui/analysis_run_service.py`

- [x] Add a failing test for two rows retaining two ComputeRun projections.
- [x] Implement `persist_batch_analysis_runs` with per-row contexts.
- [x] Run the helper test.

### Task 2: GUI wiring

**Files:**
- Modify: `tests/test_main_window_workers.py`
- Modify: `tests/test_main_window_run_mixin.py`
- Modify: `polynexus/gui/main_window_workers.py`
- Modify: `polynexus/gui/main_window_run_mixin.py`
- Modify: `polynexus/gui/main_window_history_mixin.py`
- Modify: `polynexus/gui/main_window.py`

- [x] Add source/output locators to successful worker rows.
- [x] Invoke persistence after a current batch completes.
- [x] Forward the shared context through the existing history service.
- [x] Run the focused GUI matrix.

### Task 3: Verification and checkpoint

**Files:**
- Modify: task card, acceptance, and memory records.

- [ ] Run the structured verifier and diff check.
- [ ] Create the explicit allowlisted checkpoint.
