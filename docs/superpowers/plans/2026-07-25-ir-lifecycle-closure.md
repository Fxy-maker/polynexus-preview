# IR Lifecycle Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close automated lifecycle evidence for IR standard, temperature-2D, and mapping/ROI without inventing vendor semantics.

**Architecture:** Exercise existing typed DTO providers through the shared Manifest/Gallery, project, export, and History services. Keep the mapping branch explicit and provenance-preserving.

**Tech Stack:** Python, pytest, PySide6 offscreen tests, NumPy, existing PolyNexus figure services.

---

### Task 1: Add the failing IR lifecycle regression

**Files:**
- Create: `tests/test_ir_lifecycle_closure.py`
- Modify: `docs/agent/tasks/2026-07-25-ir-lifecycle-closure.md`

- [ ] **Step 1: Parameterize standard, temperature-2D, and mapping/ROI DTOs.**
- [ ] **Step 2: Run the new test before any production change.**

### Task 2: Preserve the explicit mapping boundary

**Files:**
- Modify only a production file if a lifecycle assertion proves a shared connection missing.

- [ ] **Step 1: Keep mapping provenance and invalid-pixel roles unchanged.**
- [ ] **Step 2: Re-run the lifecycle regression after the smallest fix.**

### Task 3: Verify and checkpoint

**Files:**
- Create: `docs/acceptance/2026-07-25-ir-lifecycle-closure.md`
- Modify: `docs/agent/memory/current-state.md`
- Modify: `docs/agent/memory/active-work.md`

- [ ] **Step 1: Run the focused IR lifecycle/provider/temperature/mapping/history matrix.**
- [ ] **Step 2: Run `python scripts/verify.py --task docs/agent/tasks/2026-07-25-ir-lifecycle-closure.md --changed --types`.**
- [ ] **Step 3: Create one allowlisted checkpoint without pushing.**
