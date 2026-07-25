# Export figure-run provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Declare and preserve manifest-backed figure runs in result exports.

**Architecture:** Extend the existing export-context service only. Figure runs
  remain under `metadata/runs`, the source active pointer is copied to
  `metadata/active_run.json`, and the export manifest records both paths.

**Tech Stack:** Python, pathlib, shutil, pytest.

---

### Task 1: Contract regression

**Files:**

- Modify: `tests/test_export_context_service.py`
- Modify: `tests/test_main_window_persistence.py`

- [x] Assert figure-run directory and active pointer entries in manifest shape.
- [x] Assert a source `runs/` tree and `active_run.json` are expected in the
  copied bundle; verify the old behavior fails.

### Task 2: Export implementation

**Files:**

- Modify: `polynexus/gui/export_context_service.py`

- [x] Append `figure_runs` when `runs/` is copied.
- [x] Copy `active_run.json` to `metadata/active_run.json` when present.
- [x] Declare both paths and list `metadata/runs/` in README.

### Task 3: Checkpoint

- [x] Run focused export/GUI matrix and task verifier.
- [ ] Commit only the explicit source, test, planning, and memory files.
