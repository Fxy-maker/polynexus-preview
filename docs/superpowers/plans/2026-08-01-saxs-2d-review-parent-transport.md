# SAXS 2D Parent Review Transport Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve an existing outer-engine SAXS 2D scientific review record when building temperature/strain summary-only AI context.

**Architecture:** Add one private read-only helper in `saxs_ai_rescue.py` that
reads the outer result's existing review payload, then pass it as the explicit
`scientific_review` argument to `build_saxs_2d_review_context`. Child-series
evidence remains the source for detector/orientation data. No new contract or
scientific decision is introduced.

**Tech Stack:** Python, pytest, existing SAXS review and AI summary contracts.

---

### Task 1: Add the parent-review regression

**Files:**
- Modify: `tests/test_saxs_2d_ai_context_bridge.py`

- [x] **Step 1: Write the failing test**

Add a reviewer payload helper and parameterized temperature/strain cases whose
outer `result.parameters` contains `scientific_review_record`, while the mode
series contains detector/orientation evidence. Assert the projected review is
accepted and the child evidence remains present. Add a wrong-scope case that
asserts `scope_mismatch` and a false promotion decision.

- [x] **Step 2: Run RED**

Run:

```powershell
python -m pytest -q tests/test_saxs_2d_ai_context_bridge.py -o addopts=
```

Expected result before production code: the new accepted-review assertions
fail with `review_missing`.

Observed: `3 failed, 7 passed in 0.65s`; all three failures were the expected
outer-review `review_missing` transport gap.

### Task 2: Project the existing outer review

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_ai_rescue.py`

- [x] **Step 1: Add the minimal helper**

Read `result.result.parameters` through the existing `_object_value` boundary,
accept only `scientific_review_record` and then `scientific_review`, and return
`None` when the payload is absent. Do not copy or mutate either result.

- [x] **Step 2: Pass the explicit payload**

Call:

```python
two_d_context = build_saxs_2d_review_context(
    _mode_result(result, normalized_mode),
    scientific_review=_existing_scientific_review(result),
)
```

Keep the existing `status != "unavailable"` projection boundary.

- [x] **Step 3: Run GREEN**

Run the focused bridge test again and expect all bridge tests to pass with no
new warning or raw-field leakage.

Observed: `10 passed in 0.15s`; the broader AI/Advisor/prompt/live regression
returned `35 passed in 1.87s`.

### Task 3: Regression and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-08-01-saxs-2d-review-parent-transport.md`
- Modify: `docs/superpowers/plans/2026-08-01-saxs-2d-review-parent-transport.md`
- Modify: `docs/superpowers/specs/2026-08-01-saxs-2d-review-parent-transport-design.md`

- [x] **Step 1: Run focused AI/Advisor/prompt regression**

Run the task card focused command and record the complete pytest summary and
exit code.

Observed: `35 passed in 1.87s`, exit `0`.

- [x] **Step 2: Run SAXS and structured checks**

Run the complete SAXS matrix, task-scoped structured verifier, storage report
and dry-run clean. Only complete summaries with exit `0` count as pass; never
run `test_storage.py --apply` in this task.

Observed: SAXS `710 passed, 6 warnings in 485.73s`, exit `0`; structured
verifier exit `0` with quality `297` and preprocessing `106`; storage dry-runs
reported `145` artifacts, `15,743,185,346` eligible bytes, and `removed=0`.

- [x] **Step 3: Create one explicit allowlist checkpoint**

Use `scripts/auto_commit.py` with only the production file, focused test, and
the three task artifacts listed in the task card.

The resulting local commit is the sole checkpoint for this atomic task; no
push, merge, or cleanup is part of this step.
