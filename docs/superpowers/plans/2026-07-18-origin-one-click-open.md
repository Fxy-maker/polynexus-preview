# Origin One-Click Open Implementation Plan

> **For agentic workers:** Execute task-by-task with TDD and verification checkpoints.

**Goal:** Make ChartEditor send the current figure to a visible OriginPro window instead of only producing an `Origin_Export` folder.

**Architecture:** Keep ChartEditor as an `ExportResult` consumer. Extend the native Origin facade with explicit application visibility/activation, while the existing adapter chain continues to decide native versus package fallback. Keep output staging inside the adapter boundary and use the configured `ORIGIN_EXE` only for Origin startup.

**Tech Stack:** Python 3, PySide6, `originpro`, optional COM/LabTalk, Pytest.

---

### Task 1: Add the failing native activation contract test

**Files:**
- Modify: `tests/test_originpro_adapter.py`
- Modify: `tests/test_chart_editor_origin_export.py`

- [x] Write a fake Origin facade test asserting that a successful native export calls `show`, `activate`, creates a plot, and saves a native project.
- [x] Write a ChartEditor test asserting the native action invokes the service without opening the directory chooser first.
- [x] Run the focused tests and confirm they fail because the facade has no explicit activation contract and ChartEditor always chooses an output directory.

### Task 2: Implement visible native Origin export

**Files:**
- Modify: `polynexus/origin/originpro_adapter.py`
- Modify: `polynexus/gui/widgets/chart_editor_origin_mixin.py`
- Modify: `polynexus/gui/i18n.py` only if fallback messaging needs a new translation key

- [x] Add `show()` and `activate()` methods to the facade, using the configured Origin installation without bypassing the adapter boundary.
- [x] Call those methods before/after native graph creation so the Origin window is visible with the graph.
- [x] Let the native request use its output root without forcing a GUI directory dialog; retain a safe default output root for native project saves.
- [x] Preserve the package fallback and make its status explicit when no native adapter can handle the request.

### Task 3: Verify the complete affected slice

**Files:**
- Modify: `docs/agent/memory/active-work.md` if durable state changes

- [x] Run the focused Origin suite: 37 passed.
- [x] Run `pytest tests/test_chart_editor.py -q`: 238 passed.
- [x] Run Ruff and capability probing; both passed for the changed slice.
- [x] Run a live smoke export with the configured OriginPro installation; it returned `success/originpro` and left an `Origin64` window visible. The smoke `.opju` is locked until Origin closes, so its temporary-directory cleanup reports the expected Windows file-lock warning.
