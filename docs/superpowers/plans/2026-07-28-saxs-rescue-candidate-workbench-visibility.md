# SAXS Rescue-Candidate Workbench Visibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or superpowers:subagent-driven-development) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Transport existing temperature rescue candidates and expose them as
candidate-only Workbench review evidence.

**Architecture:** Extend the existing immutable evidence-copy allowlist with
`sequence_rescue_candidates`; add one pure presentation formatter that reads
the public payload. No algorithm or AI execution path changes.

**Tech Stack:** Python, mappings, dataclasses, pytest, Ruff, repository verifier.

---

### Task 1: Write RED transport and Workbench tests

**Files:**

- Modify: `tests/test_saxs_batch_parameters.py`
- Modify: `tests/test_saxs_workbench_series_evidence.py`

- [x] Add a temperature `TempSeriesResult` with one candidate and assert
  `get_parameters()` returns an equal but detached `sequence_rescue_candidates`
  list while the source remains unchanged.
- [x] Add a Workbench payload test asserting candidate ID, frame index,
  proposed source, `candidate_only`, and validation-required wording appear;
  assert the text does not claim applied/accepted/physical validity.
- [x] Add empty/malformed and bilingual assertions, including payload
  immutability.
- [x] Run the new tests and confirm they fail because the public payload and
  review channel do not yet expose candidates.

### Task 2: Implement the smallest transport and review projection

**Files:**

- Modify: `polynexus/core/saxs_batch_helpers.py`
- Modify: `polynexus/core/saxs.py`
- Modify: `polynexus/gui/saxs_results_table_service.py`

- [x] Add `sequence_rescue_candidates` to the existing deep-copy field
  allowlist and expose the copied list from the temperature parameters branch;
  do not alter candidate generation or per-frame copying.
- [x] Add `_sequence_rescue_review_text(payload, language)` that consumes only
  valid mappings, preserves input order, bounds displayed values, and returns
  empty text when none are valid.
- [x] Compose its risk/next text with the existing review channels. The next
  text must require deterministic rerun plus existing physical, quality, and
  sequence gates and must not imply application or acceptance.

### Task 3: Verify and checkpoint

**Files:** the explicit allowlist in the task card.

- [x] Run focused tests, exact SAXS matrix, task verifier, Ruff/compile, and
  `git diff --check`; record exact results and any full/boundary limitation.
- [x] Update task/spec/plan status and durable memory with actual evidence.
- [ ] Confirm only the explicit allowlist is staged and run:

```powershell
python scripts/auto_commit.py --message "feat(saxs): expose rescue candidates in workbench" --files <explicit-allowlist>
```
