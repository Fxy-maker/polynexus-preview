# NMR Solid-C Review Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose NMR solid-C assignment and Xc promotion provenance in the Results Workbench.

**Architecture:** Preserve existing NMR evidence in the core, derive only a display gate in the review service, and render it through a shared panel DTO. Real route tests remain the authority for GUI transport; scientific approval stays separate.

**Tech Stack:** Python, PySide6, pytest, repository verifier.

---

### Task 1: Evidence and review formatter

**Files:**
- Modify: `polynexus/core/analysis_evidence_nmr.py`
- Modify: `polynexus/gui/results_review_service.py`
- Modify: `polynexus/gui/i18n.py`
- Test: `tests/test_analysis_evidence.py`
- Test: `tests/test_results_review_service.py`

- [x] **Step 1: Write failing tests** for source preservation, the blocked Xc gate, and the panel DTO field.
- [x] **Step 2: Run the tests** and observe missing source/gate/DTO behavior.
- [x] **Step 3: Implement the minimal evidence and formatter changes.**
- [x] **Step 4: Run the focused tests** and confirm `3 passed` for the new behaviors.

### Task 2: Native route

**Files:**
- Modify: `polynexus/gui/main_window_results_mixin.py`
- Modify: `tests/test_native_gui_real_route_capture.py`

- [x] **Step 1: Add the wrapped NMR evidence row and route assertions.**
- [x] **Step 2: Run the real `nmr.solid_c` Windows route and inspect the Results capture.**

### Task 3: Checkpoint

**Files:**
- Create: `docs/agent/tasks/2026-07-30-nmr-solid-c-review-provenance.md`
- Create: `docs/superpowers/specs/2026-07-30-nmr-solid-c-review-provenance-design.md`
- Create: `docs/superpowers/plans/2026-07-30-nmr-solid-c-review-provenance.md`
- Create: `docs/acceptance/2026-07-30-nmr-solid-c-review-provenance.md`

- [ ] **Step 1: Run the focused matrix and structured verifier.**
- [ ] **Step 2: Create one explicit-allowlist checkpoint.**
