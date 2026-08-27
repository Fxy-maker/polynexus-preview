# Evidence Gallery Visible Filters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose technique and group filtering in the evidence package gallery.

**Architecture:** Build selector values from the technique-neutral figure index,
then forward selections through `EvidencePackageViewAdapter` to the pure
gallery service. No provider or package schema changes are needed.

**Tech Stack:** Python, PySide6, pytest.

---

### Task 1: GUI filter contract

**Files:**
- Modify: `tests/test_evidence_package_view.py`
- Modify: `polynexus/gui/evidence_package_view.py`

- [x] Write a regression test for technique/group selection and default reset.
- [x] Verify the test fails because the dialog has no selectors.
- [x] Add selectors and reload the read-only gallery through the adapter.
- [x] Run the focused GUI tests.

### Task 2: Verification and checkpoint

**Files:**
- Modify: task card and acceptance/memory records as needed.

- [x] Run the task-scoped structured verifier and `git diff --check`.
- [ ] Create an explicit allowlisted checkpoint with `scripts/auto_commit.py`.
