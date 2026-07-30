# Scientific Review Visibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make one persisted Scientific Review decision consistently visible in Results Workbench, History, and Export.

**Architecture:** Add one pure GUI adapter that extracts and localizes the existing review decision snapshot. Thread its immutable display DTO through the existing results model, history-row builder, and export context; keep all scientific decisions in `polynexus.core.scientific_review`.

**Tech Stack:** Python dataclasses, PySide6 presentation services, pytest, existing i18n and verification scripts.

---

### Task 1: Add the shared review display contract

**Files:**
- Create: `polynexus/gui/scientific_review_presentation.py`
- Create: `tests/test_scientific_review_presentation.py`
- Modify: `polynexus/gui/i18n.py`

- [x] **Step 1: Write failing tests** for accepted, missing required, not-applicable, source mismatch, and nested evidence extraction.
- [x] **Step 2: Run `python -m pytest -q tests/test_scientific_review_presentation.py`** and verify collection or assertion failure proves the contract is absent.
- [x] **Step 3: Implement the immutable adapter and bilingual status labels.** It must inspect direct/nested `scientific_review` mappings, preserve reason/record/scope/source, and fail closed for malformed states.
- [x] **Step 4: Re-run the focused adapter tests** and verify green.

### Task 2: Surface the DTO in Results Workbench

**Files:**
- Modify: `polynexus/gui/result_table_models.py`
- Modify: `polynexus/gui/results_table_service.py`
- Modify: `polynexus/gui/main_window_output_mixin.py`
- Modify: `tests/test_results_table_service.py`

- [x] **Step 1: Add failing tests** asserting a solid-C or mapping model carries review text and a normal DSC model is not applicable.
- [x] **Step 2: Run the focused tests** and verify the new assertions fail.
- [x] **Step 3: Thread the display DTO through `ResultsTableModel`; pass the live result as a review source and append the text to the existing result summary without changing risk/next-step semantics.
- [x] **Step 4: Re-run focused Results Workbench tests** and verify green.

### Task 3: Surface the DTO in History

**Files:**
- Modify: `polynexus/gui/history_table_service.py`
- Modify: `polynexus/gui/main_window_history_mixin.py`
- Modify: `polynexus/gui/main_window_retranslate_mixin.py`
- Modify: `polynexus/gui/analysis_history_service.py`
- Modify: `tests/test_history_table_service.py`

- [x] **Step 1: Update the history-row regression test** to require the Scientific review column and its tooltip.
- [x] **Step 2: Run the test and verify it fails before implementation.
- [x] **Step 3: Add the column/header/retranslation and keep history export matrix aligned with the visible table.
- [x] **Step 4: Re-run history tests and verify green.

### Task 4: Surface the DTO in Export

**Files:**
- Modify: `polynexus/gui/export_context_service.py`
- Modify: `tests/test_export_context_service.py`

- [x] **Step 1: Add failing assertions for structured review context and README output.
- [x] **Step 2: Run focused export tests and verify they fail.
- [x] **Step 3: Add `scientific_review` and `scientific_review_text` to export context and render the same text in README.
- [x] **Step 4: Run focused tests for all three surfaces.

### Task 5: Verify and checkpoint

**Files:**
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/memory/current-state.md`

- [x] **Step 1: Run the focused matrix from the task card.
- [x] **Step 2: Run `python scripts/verify.py --task docs/agent/tasks/2026-07-29-scientific-review-visibility.md --changed --types` and record the exact outcome.
- [x] **Step 3: Review `git diff --check` and the explicit allowlist.
- [x] **Step 4: Create the implementation checkpoint and a follow-up evidence checkpoint with explicit allowlists.** The implementation is `e7209ee`; the current evidence checkpoint records the fresh focused matrix and verifier.
