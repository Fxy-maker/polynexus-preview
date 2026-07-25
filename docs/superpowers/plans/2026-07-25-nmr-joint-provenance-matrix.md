# NMR and Joint provenance matrix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Verify that NMR and Joint published runs remain recoverable through the active Manifest Gallery with explicit provenance and publication roles.

**Architecture:** Reuse the existing NMR engine, Joint Coordinator, FigurePipeline, and manifest-only Gallery service. Tests inspect persisted documents rather than GUI internals.

**Tech Stack:** Python, NumPy, pytest, shared FigureDefinition/FigurePipeline/Manifest contracts.

---

### Task 1: Write failing published-run lifecycle tests

**Files:**
- Create: `tests/test_nmr_joint_provenance_matrix.py`

- [ ] **Step 1:** Build minimal NMR and Joint DTO fixtures and assert Manifest/Gallery/document provenance and roles.
- [ ] **Step 2:** Run the focused test and confirm the first missing lifecycle behavior fails.

### Task 2: Implement the smallest lifecycle fix

**Files:**
- Modify only the production lifecycle module exposed by the failing test.
- Modify: `tests/test_nmr_joint_provenance_matrix.py`

- [ ] **Step 1:** Preserve run-relative paths and role/status values through the existing entrypoint.
- [ ] **Step 2:** Re-run the focused test and the existing NMR/Joint provider suites.

### Task 3: Verify and checkpoint

**Files:**
- Create: `docs/acceptance/2026-07-25-nmr-joint-provenance-matrix.md`
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/memory/current-state.md`

- [ ] **Step 1:** Run the task-scoped verifier with external basetemp.
- [ ] **Step 2:** Record exact evidence and known real-data/GUI limits.
- [ ] **Step 3:** Create one allowlisted auto-commit.
