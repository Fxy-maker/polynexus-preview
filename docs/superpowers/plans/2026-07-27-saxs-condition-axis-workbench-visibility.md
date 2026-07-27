# SAXS Condition-Axis Workbench Visibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface existing condition-axis defects as advisory SAXS Workbench review evidence.

**Architecture:** Add one presentation-only formatter beside the existing
`_series_metric_review_text()` helper. It reads only nested
`metric_evidence[*].condition_axis`, composes its result with existing review
channels, and leaves the Diagnostics serializer and source payload untouched.

**Tech Stack:** Python mappings, existing `ResultsTablePresentation`, pytest, SAXS verifier.

---

### Task 1: Add failing Workbench tests

**Files:**
- Modify: `tests/test_saxs_workbench_series_evidence.py`

- [x] **Step 1: Add a defective-axis fixture and assertions**

Add `condition_axis` to one metric with `status="diagnostic"`, invalid,
duplicate, and non-monotonic positions. Assert the combined review text names
the metric and axis, reports each defect count/position, and contains advisory
wording rather than a physical-pass claim.

- [x] **Step 2: Add clean-axis and localization assertions**

Assert an `ordered` axis does not add risk text, Chinese diagnostic text keeps
the axis name and “诊断”, and the Diagnostics row still contains the complete
`condition_values` and position arrays.

- [x] **Step 3: Run RED**

Run:

```powershell
python -m pytest tests/test_saxs_workbench_series_evidence.py -q
```

Expected: the new axis assertions fail because no formatter consumes
`condition_axis` yet.

### Task 2: Implement the presentation-only formatter

**Files:**
- Modify: `polynexus/gui/saxs_results_table_service.py`

- [x] **Step 1: Read only existing nested evidence**

Implement `_condition_axis_review_text(payload, language)` that iterates
`metric_evidence`, skips absent or `ordered` mappings, and safely converts
defect arrays to integer-position text. It must not touch `condition_values`.

- [x] **Step 2: Bound the review hint without truncating evidence**

Show defect counts and at most eight representative positions followed by an
ellipsis when more exist. Leave the full arrays in the existing diagnostics
row and emit a next-step instruction to inspect them.

- [x] **Step 3: Compose existing review channels**

Call the helper from `build_saxs_results_presentation()` and concatenate its
risk/next text with the existing metric and sequence text. Do not change any
DTO, persistence, export, or analysis code.

### Task 3: Verify and checkpoint

**Files:**
- Modify: task card, plan, and durable memory after verification.

- [x] **Step 1: Run focused and full SAXS matrices**

Run the focused Workbench test, then the PowerShell-expanded `test_saxs_*.py`
matrix with an external basetemp. Record exact counts and existing warnings.

- [x] **Step 2: Run structured checks**

Run the task-scoped verifier with an external basetemp, plus `git diff --check`.
Record the default `.pytest_tmp` permission limitation if it recurs; do not
claim it as a code failure.

- [x] **Step 3: Create one allowlist checkpoint**

Run `scripts/auto_commit.py` with exactly the seven task-card paths. Do not
include parallel GUI/editor files or temporary directories.

## Plan self-review

- The spec is covered by the three tasks above.
- No production code is written before the RED test run.
- The formatter consumes only an existing public evidence mapping and uses no
  new scientific threshold or strain ordering assumption.
