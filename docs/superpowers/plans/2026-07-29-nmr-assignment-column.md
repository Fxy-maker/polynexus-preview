# NMR solid-C assignment column Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended). Steps use checkbox syntax for tracking.

**Goal:** Separate readable ppm peak markers from a complete solid-C assignment column.

**Architecture:** The NMR FigureDefinition provider emits both objects through the existing portable contract. The shared renderer already handles axes-coordinate text; no GUI or scientific algorithm fork is added.

**Tech Stack:** Python, Matplotlib, pytest, PySide6 native Windows acceptance harness.

---

### Task 1: Establish the failing provider regression

**Files:**
- Modify: `tests/test_nmr_figure_provider.py`

- [x] Add a seven-peak regression proving assignments are complete and ordered.
- [x] Assert plot text contains ppm only and assignment rows use axes coordinates.
- [x] Assert the spectrum layout reserves the wider side-column canvas.
- [x] Run the new test and record the expected RED failure.

### Task 2: Implement the provider layout

**Files:**
- Modify: `polynexus/core/nmr_engine/figure_provider.py`

- [x] Add deterministic assignment-row objects without changing peak ranking.
- [x] Keep existing line and ppm marker objects for each retained peak.
- [x] Widen only the spectrum layout used by the assignment-column route.
- [x] Run the focused NMR/provider/document matrix and confirm GREEN.

### Task 3: Verify real native route and checkpoint

**Files:**
- Create: `docs/acceptance/2026-07-29-nmr-assignment-column.md`
- Modify: `docs/agent/tasks/2026-07-29-nmr-assignment-column.md`

- [x] Render and inspect a fresh native solid-C Results/Gallery/History/Editor
      route with package export fallback.
- [x] Run the task-scoped verifier and diff checks.
- [x] Record exact evidence and create one explicit allowlisted checkpoint.
- [x] Preserve remaining scientific/release limitations.
