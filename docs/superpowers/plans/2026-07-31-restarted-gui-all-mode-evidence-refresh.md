# Restarted GUI All-Mode Evidence Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce fresh current-checkout native GUI route and visual evidence without changing product behavior.

**Architecture:** Reuse `tests/test_native_gui_real_route_capture.py`, which restores real engine results through the existing History/Manifest path and uses the existing PackageExporter fallback. Keep all pytest basetemp and captures outside the repository source/data boundary.

**Tech Stack:** Python, pytest, PySide6 native Windows Qt, existing GUI and figure lifecycle services.

---

### Task 1: Run the native route matrix

**Files:**
- Test: `tests/test_native_gui_real_route_capture.py`
- Evidence: `D:\PolyNexus_native_restarted_gui_audit_20260731`
- Test storage: `D:\PolyNexus-test-runs-native-restarted-20260731`

- [x] **Step 1: Run all native route cases**

Run with `QT_QPA_PLATFORM=windows`, evidence retention, and `-o addopts=` so
the test process produces a complete independent pytest summary.

- [x] **Step 2: Count and inspect captures**

Confirm every mode has four PNGs and inspect representative Results, Gallery,
Joint, IR mapping, NMR solid-C, and Editor images for nonblank content and
visible conservative status.

### Task 2: Record the evidence boundary

**Files:**
- Create: `docs/acceptance/2026-07-31-restarted-gui-all-mode-evidence-refresh.md`
- Modify: `docs/agent/tasks/2026-07-31-restarted-gui-all-mode-evidence-refresh.md`

- [x] **Step 1: Record exact test and capture counts**
- [x] **Step 2: Record warnings and visual limitations without upgrading them**
- [x] **Step 3: Run boundary, task verifier, and diff checks**
- [x] **Step 4: Create one four-file explicit allowlist checkpoint**
