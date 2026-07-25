# NMR Lifecycle Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close automated real-data lifecycle evidence for all four NMR H/C partitions.

**Architecture:** Use `NMREngine.run_pipeline` as the input/preprocessing/analysis boundary, then reuse manifest Gallery, `FigureProjectService`, export-context, and MainWindow History contracts.

**Tech Stack:** Python, pytest, PySide6 offscreen tests, existing NMR reader/engine and figure services.

---

### Task 1: Add the failing real-data lifecycle regression

**Files:**
- Create: `tests/test_nmr_lifecycle_closure.py`
- Modify: `docs/agent/tasks/2026-07-25-nmr-lifecycle-closure.md`

- [ ] **Step 1: Parameterize the four repository NMR fixture paths.**
- [ ] **Step 2: Run the new regression before changing production code.**

### Task 2: Preserve assignment and fallback semantics

**Files:**
- Modify only a production file if a lifecycle assertion proves a shared connection missing.

- [ ] **Step 1: Keep assignment-limited solid 13C evidence provisional.**
- [ ] **Step 2: Re-run the real-data lifecycle regression after the smallest fix.**

### Task 3: Verify and checkpoint

**Files:**
- Create: `docs/acceptance/2026-07-25-nmr-lifecycle-closure.md`
- Modify: `docs/agent/memory/current-state.md`
- Modify: `docs/agent/memory/active-work.md`

- [ ] **Step 1: Run the four-partition lifecycle/provider/provenance/history matrix.**
- [ ] **Step 2: Run `python scripts/verify.py --task docs/agent/tasks/2026-07-25-nmr-lifecycle-closure.md --changed --types`.**
- [ ] **Step 3: Create one allowlisted checkpoint without pushing.**
