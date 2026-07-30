# Joint AI Context Fallback Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Preserve the deterministic Joint AI boundary in legacy GUI/history fallback contexts.

**Architecture:** Add one static JSON-safe boundary mapping to the two existing fallback return dictionaries in `joint_ai_context()`. Leave report-context priority and all diagnostic calculations unchanged.

**Tech Stack:** Python, pytest, existing Joint/History context contracts.

---

### Task 1: Add the failing fallback assertions

**Files:**
- Modify: `tests/test_analysis_history_service.py`

- [x] **Step 1: Extend clean and conflicted fallback tests**

Assert that `context["ai_boundary"]` equals the four-field boundary in both
`test_joint_ai_context_builds_no_issue_summary_with_translated_labels` and
`test_joint_ai_context_summarizes_issue_families_highlights_and_counts`.

- [x] **Step 2: Run the focused tests and confirm the missing-key failure**

Run:

```powershell
python -m pytest -q tests/test_analysis_history_service.py -k "joint_ai_context"
```

Expected: the two fallback tests fail with `KeyError: 'ai_boundary'` while
existing report/tuning/history priority tests remain otherwise unchanged.

Observed: `2 failed, 2 passed, 114 deselected`; both failures were the
expected missing-key errors.

### Task 2: Implement the minimal fallback boundary

**Files:**
- Modify: `polynexus/gui/analysis_history_service.py`

- [x] **Step 1: Add the static boundary to both fallback dictionaries**

Use the exact JSON-safe values from the design. Do not change the existing
summary, counts, issue family, highlight, sample, batch, or row fields.

### Task 3: Verify and checkpoint

**Files:**
- Modify: task card, design, plan, acceptance, and `active-work.md`.

- [x] **Step 1: Run focused tests and task verifier**

Run the commands in the task card and record complete summaries and exit codes.

Observed: fallback tests `4 passed`; the History/Export/Joint consumer and
lifecycle matrix passed `143 passed in 20.97s`, both with exit code `0`.

- [x] **Step 2: Create one explicit allowlist checkpoint**

Use `scripts/auto_commit.py` with only the listed seven files. Do not include
`current-state.md`, scratch directories, or unrelated task changes.

Task-scoped verification passed with quality `290`, preprocessing `106`,
task/memory, Ruff, compile, type baseline, and whitespace checks; exit code
`0`. The explicit allowlist checkpoint is the only commit action for this
slice.
