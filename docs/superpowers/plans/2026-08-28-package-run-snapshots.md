# Package Run Snapshots Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make packaged run-manifest references portable and package-relative.

**Architecture:** Snapshot each already validated run manifest during package
creation under `runs/`; leave raw data external and hash-bound.

**Tech Stack:** Python, pathlib, pytest.

---

### Task 1: Snapshot contract

**Files:**
- Modify: `tests/test_project_workflow_package.py`
- Modify: `polynexus/core/project_workflow/package.py`

- [x] Add a failing assertion for `runs/<run_id>.json` and relative manifest references.
- [x] Copy validated manifest payloads into the package `runs/` directory.
- [x] Run focused package/evidence tests.

### Task 2: Verification and checkpoint

**Files:**
- Modify: task card, acceptance, and memory records.

- [ ] Run the task-scoped structured verifier and diff check.
- [ ] Create the explicit allowlisted checkpoint.
