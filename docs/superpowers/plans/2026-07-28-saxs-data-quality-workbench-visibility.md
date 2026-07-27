# SAXS Data-Quality Workbench Visibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show existing q/I data-quality reports as deterministic Workbench review context.

**Architecture:** A presentation-only formatter reads top-level or per-row report mappings and returns the existing risk/next text pair. The Results Workbench composes this text with existing evidence channels; no GUI algorithm state is added.

**Tech Stack:** Python, immutable copied payloads, pytest, Ruff, repository verifier.

---

### Task 1: Add failing Workbench review tests

**Files:**
- Modify: `tests/test_saxs_results_table_service.py`

- [x] **Step 1: Test a top-level report.**

Build a static payload with `data_quality_report` containing level, source/ref,
counts, reasons, and actions. Assert the English presentation includes those
emitted values and an advisory next-step message.

- [x] **Step 2: Test batch alignment and missing rows.**

Build `_batch_data` with one report and one missing report. Assert the text
reports `1/2` coverage, retains the emitted level/reason, and does not mention
invented values for the missing row.

- [x] **Step 3: Test localization and immutability.**

Build a report with reasons/actions, run English and Chinese presentations,
and assert the source payload is byte-equivalent/deep-equal before and after;
Chinese output must not expose English level labels as the primary label.

- [x] **Step 4: Run RED.**

```powershell
python -m pytest -q tests/test_saxs_results_table_service.py::test_data_quality_review_shows_top_level_report tests/test_saxs_results_table_service.py::test_data_quality_review_shows_batch_coverage_and_missing_rows --basetemp C:\Temp\PolyNexus_saxs_data_quality_workbench_red
```

Expected: the new tests fail because the existing presentation has no
data-quality review channel.

### Task 2: Implement the presentation-only formatter

**Files:**
- Modify: `polynexus/gui/saxs_results_table_service.py`

- [x] **Step 1: Add `_data_quality_review_text`.**

Read only report mappings. Keep a list of `(row_index, report)` for reports
actually present, format source order, count levels with `Counter`, and join
unique reason/action values without sorting away their first-seen order. Return
`("", "")` if no report is present.

```python
reports = []
top_report = payload.get("data_quality_report")
if isinstance(top_report, Mapping):
    reports.append((None, top_report))
for index, row in enumerate(payload.get("_batch_data", ())):
    if isinstance(row, Mapping) and isinstance(row.get("data_quality_report"), Mapping):
        reports.append((index, row["data_quality_report"]))
```

The formatter must use only emitted values and existing `tr_for_language`
wrappers; it must not compute a new level or alter the payload.

- [x] **Step 2: Compose with the existing review channels.**

Call the helper in `build_saxs_results_presentation()` and append its risk and
next text after detector text, preserving existing order for all other channels.

### Task 3: Verify and checkpoint

**Files:** task/spec/plan, service/test, and durable memory files above.

- [x] **Step 1: Run focused Workbench tests, the exact SAXS matrix, task verifier,
  Ruff/compile, and `git diff --check`; record actual outcomes.**
- [x] **Step 2: Confirm only the seven-file allowlist is staged.**
- [x] **Step 3: The explicit allowlist was checkpointed in `fb76039`; no push
  was performed.**
