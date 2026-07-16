# SAXS Output/Input Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent SAXS directory analysis from treating generated output TIFFs as raw detector frames.

**Architecture:** Replace the unprunable `Path.rglob()` walk in `scan_experiment_dir()` with a sorted `os.walk()` traversal. Prune `polynexus_output` and `results*` directories before descending, preserving the existing supported-extension and condition-recovery behavior. Add a focused regression test and a real-data discovery check.

**Tech Stack:** Python 3.10+, pathlib, os.walk, pytest, bundled PolyNexus Python runtime.

---

### Task 1: Regression test for generated-output exclusion

**Files:**
- Modify: `tests/test_saxs_condition_recovery.py`

- [x] Add a test with one raw EDF and one nested generated TIFF and assert only the raw EDF is discovered.
- [x] Run the focused test before the production change and confirm it fails because the TIFF is currently discovered.

### Task 2: Prune generated directories during SAXS discovery

**Files:**
- Modify: `polynexus/core/saxs_engine/io.py:200-230`

- [x] Replace the `root.rglob("*")` enumeration with a sorted `os.walk()` traversal.
- [x] Prune `polynexus_output` and names beginning with `results` in `dirnames` before recursion.
- [x] Preserve hidden-entry skipping, supported extensions, EDF header recovery, and condition ordering.
- [x] Re-run the focused regression test.

### Task 3: Validate the fix against the supplied PA6 directory

**Files:**
- Modify: `docs/agent/tasks/2026-07-16-saxs-output-input-boundary.md`

- [x] Run the SAXS condition-recovery test file.
- [x] Run the bundled runtime against the real directory in discovery-only mode and confirm five discovered EDF files, zero generated TIFF files, and no changes to existing output artifacts.
- [x] Mark the task card complete with evidence and note any remaining geometry-header warning separately.
