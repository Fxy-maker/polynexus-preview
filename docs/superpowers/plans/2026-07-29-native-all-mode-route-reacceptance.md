# Native all-mode route reacceptance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended). Steps use checkbox syntax for tracking.

**Goal:** Refresh current native route evidence after the NMR solid-C assignment-column change.

**Architecture:** Reuse the existing native Windows Qt harness and real fixture sources. Write captures, pytest basetemp, and PackageExporter output only to external D: roots; checkpoint only the task and acceptance records.

**Tech Stack:** Python, pytest, PySide6 native Windows Qt, existing Results/Gallery/History/Editor/PackageExporter harness.

---

### Task 1: Run the current native matrix

**Files:**
- Read: `tests/test_native_gui_real_route_capture.py`
- Create externally: `D:\PolyNexus_native_all_routes_reacceptance_20260729`

- [x] Run all 17 selected native cases with isolated D: basetemp.
- [x] Record exact stdout, exit code, warning count, and image count.

### Task 2: Inspect representative current evidence

**Files:**
- Read: current capture PNGs under the external D: root.

- [x] Inspect NMR solid-C Editor for the complete assignment column.
- [x] Inspect Joint Results/History and synthetic IR mapping boundaries.
- [x] Separate automated route evidence from human/scientific gates.

### Task 3: Verify and checkpoint documentation

**Files:**
- Modify: `docs/agent/tasks/2026-07-29-native-all-mode-route-reacceptance.md`
- Create: `docs/acceptance/2026-07-29-native-all-mode-route-reacceptance.md`

- [x] Run the task-scoped verifier and `git diff --check`.
- [x] Create one explicit allowlisted local checkpoint; do not push or merge.
