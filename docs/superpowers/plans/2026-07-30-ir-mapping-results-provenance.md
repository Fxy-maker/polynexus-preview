# IR Mapping Results Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface canonical IR mapping coordinate and review provenance in the Results Workbench without changing scientific gating.

**Architecture:** The existing IR formatter remains the semantic boundary. A typed-like immutable review DTO carries its text to a dedicated GUI label; tests cover the formatter, DTO construction, and a native Windows route.

**Tech Stack:** Python, PySide6, pytest, repository verifier.

---

### Task 1: Prove the review DTO contract

**Files:**
- Modify: `tests/test_results_review_service.py`

- [x] **Step 1: Write the failing test** for an IR window whose evidence is nested under `feature_evidence.mapping_evidence`; assert the panel DTO contains source and physical-axis provenance.
- [x] **Step 2: Run the focused test** and observe the expected missing-DTO-field failure.
- [x] **Step 3: Implement the minimal DTO field** in `polynexus/gui/results_review_service.py` and populate it only for IR.
- [x] **Step 4: Run the focused formatter and DTO tests** and confirm both pass.

### Task 2: Render and route the evidence

**Files:**
- Modify: `polynexus/gui/main_window_results_mixin.py`
- Modify: `polynexus/gui/i18n.py`
- Modify: `tests/test_native_gui_real_route_capture.py`

- [x] **Step 1: Add a wrapped Results review evidence row** bound to `ir_support_text`.
- [x] **Step 2: Use the canonical `IRMappingResult.to_evidence()` envelope** in the native synthetic route and assert the live row contains mapping provenance.
- [x] **Step 3: Run the Windows-native route** with `QT_QPA_PLATFORM=windows` and inspect the Results capture for source, axes, origin, ROI, order, and status.

### Task 3: Checkpoint the atomic change

**Files:**
- Modify: the files listed above
- Create: `docs/agent/tasks/2026-07-30-ir-mapping-results-provenance.md`
- Create: `docs/superpowers/specs/2026-07-30-ir-mapping-results-provenance-design.md`
- Create: `docs/superpowers/plans/2026-07-30-ir-mapping-results-provenance.md`
- Create: `docs/acceptance/2026-07-30-ir-mapping-results-provenance.md`

- [ ] **Step 1: Run structured verification and `git diff --check`.**
- [ ] **Step 2: Create one explicit-allowlist local checkpoint** with `scripts/auto_commit.py`.
