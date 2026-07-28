# Real published-run reacceptance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended). Steps use checkbox syntax for tracking.

**Goal:** Refresh real backend lifecycle evidence for all available published-run modes.

**Architecture:** Reuse the existing real fixture walkthrough and shared FigureProductionPublisher, Manifest/Gallery, Editor/export, and History contracts. Keep all temporary outputs outside the repository on D:.

**Tech Stack:** Python, pytest, real technique fixtures, existing shared figure and GUI persistence services.

---

### Task 1: Execute the real walkthrough

**Files:**
- Read: `tests/test_real_published_run_walkthrough.py`
- Create externally: `D:\PolyNexus_real_walkthrough_current_20260730`

- [x] Run all 15 cases.
- [x] Record exit code, warnings, duration, and mode coverage.

### Task 2: Verify and checkpoint evidence

**Files:**
- Create: `docs/agent/tasks/2026-07-29-real-published-run-reacceptance.md`
- Create: `docs/acceptance/2026-07-29-real-published-run-reacceptance.md`

- [x] Run the task-scoped verifier and diff check; record the unrelated
      changed-file Ruff blocker without modifying SAXS files.
- [ ] Create an explicit allowlisted documentation checkpoint.
- [x] Preserve open scientific, visual, and full/boundary limitations.
