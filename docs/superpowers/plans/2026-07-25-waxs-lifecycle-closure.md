# WAXS Lifecycle Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close automated lifecycle evidence for WAXS static, temperature, and strain modes while preserving the strain 2D reactive-editor route.

**Architecture:** Reuse WAXS provider definitions and the shared figure lifecycle. Route static/temperature through `FigureProjectService`; route strain image-grid definitions through `ReactiveFigureProjectService`; use one shared export and MainWindow History assertion.

**Tech Stack:** Python, pytest, PySide6 offscreen tests, NumPy, existing PolyNexus figure services.

---

### Task 1: Add the failing WAXS lifecycle regression

**Files:**
- Create: `tests/test_waxs_lifecycle_closure.py`
- Modify: `docs/agent/tasks/2026-07-25-waxs-lifecycle-closure.md`

- [ ] **Step 1: Write a parameterized test for static, temperature, and strain.**

  Build completed provider DTOs using the repository WAXS fixture and the
  existing real-data test shapes. Assert active Gallery role/run context, save
  and publish a working revision with the appropriate project service, copy
  figure runs into an export bundle, and restore each history record.

- [ ] **Step 2: Run the new test before changing production code.**

  ```powershell
  $env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_waxs_lifecycle_red'
  python -m pytest tests/test_waxs_lifecycle_closure.py -q
  ```

### Task 2: Implement only a missing shared connection

**Files:**
- Modify only the production file named by a failing lifecycle assertion.

- [ ] **Step 1: Preserve provider IDs, roles, run-relative paths, and V2 routing.**
- [ ] **Step 2: Re-run the lifecycle regression after the smallest fix.**

### Task 3: Verify and checkpoint

**Files:**
- Create: `docs/acceptance/2026-07-25-waxs-lifecycle-closure.md`
- Modify: `docs/agent/memory/current-state.md`
- Modify: `docs/agent/memory/active-work.md`

- [ ] **Step 1: Run the focused WAXS lifecycle/publication/V2/history matrix.**
- [ ] **Step 2: Run `python scripts/verify.py --task docs/agent/tasks/2026-07-25-waxs-lifecycle-closure.md --changed --types`.**
- [ ] **Step 3: Create one allowlisted `scripts/auto_commit.py` checkpoint without pushing.**
