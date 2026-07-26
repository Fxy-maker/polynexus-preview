# Joint lifecycle closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lock the complete Joint publication-to-restore lifecycle with one
run-relative regression and durable acceptance evidence.

**Architecture:** Reuse the existing Joint figure provider, shared manifest,
project service, export-context service, and MainWindow restore boundary. Add
only an integration regression; no scientific calculation or GUI production
code is required because the audited contracts already exist.

**Tech Stack:** Python, PySide6 offscreen Qt, pytest, JSON export manifests.

---

### Task 1: Add the unified Joint lifecycle regression

**Files:**
- Create: `tests/test_joint_lifecycle_closure.py`
- Read: `polynexus/core/joint/coordinator.py`
- Read: `polynexus/core/figures/project_service.py`
- Read: `polynexus/gui/export_context_service.py`
- Read: `polynexus/gui/main_window_history_mixin.py`

- [x] Build a deterministic `JointBatchRow` fixture with DSC, WAXS, and SAXS
  source run IDs.
- [x] Publish with a fixed run ID and assert all three role-specific Gallery
  entries share it.
- [x] Save and publish the main document through `FigureProjectService` and
  assert revision two for both working and published state.
- [x] Copy the output into an export bundle and assert `metadata/runs/` plus
  `metadata/active_run.json` preserve the run.
- [x] Restore the same history record and assert the custom Joint Workbench,
  report, figure IDs, roles, and run ID survive.

Run:

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_joint_lifecycle'
python -m pytest tests/test_joint_lifecycle_closure.py -q
```

Expected: `1 passed`.

### Task 2: Record and verify the closure

**Files:**
- Create: `docs/acceptance/2026-07-25-joint-lifecycle-closure.md`
- Create: `docs/agent/tasks/2026-07-25-joint-lifecycle-closure.md`
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/memory/current-state.md`

- [x] Record exact focused, matrix, and verifier commands and outcomes.
- [x] Keep real-data, restarted-GUI, human scientific review, and AI/fallback
  release gates explicitly separate from this automated closure.
- [x] Checkpoint only the test and documentation allowlist.
