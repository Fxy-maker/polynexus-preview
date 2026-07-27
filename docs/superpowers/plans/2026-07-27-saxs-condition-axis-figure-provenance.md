# SAXS Condition-Axis Figure Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve existing condition-axis evidence through SAXS Figure and Manifest provenance.

**Architecture:** Extend the existing explicit `_COMMON_EVIDENCE_FIELDS`
allowlist by one public key. Reuse `_project_mapping()` and `_json_safe()` so
the projection remains detached and strict JSON-safe; no new DTO or consumer
logic is introduced.

**Tech Stack:** Python allowlist projection, NumPy JSON normalization, pytest, FigurePipeline.

---

### Task 1: Write the failing provenance tests

**Files:**
- Modify: `tests/test_saxs_figure_evidence_binding.py`

- [x] **Step 1: Add frame-level condition-axis evidence**

Put a defective axis under a frame metric and assert the projected record
contains the condition name, `null` non-finite value, and all defect-position
arrays after `json.dumps(..., allow_nan=False)`.

- [x] **Step 2: Add series-level and detached-value assertions**

Put the same axis under a temperature series metric, assert it reaches
`series_record`, and mutate the source mapping after projection to prove the
projected nested arrays are detached.

- [x] **Step 3: Run RED**

Run the focused Figure evidence tests. Expected failure: `condition_axis` is
absent from frame and series projected metric records because it is not in the
current common-field allowlist.

### Task 2: Implement the allowlist extension

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_evidence.py`

- [x] **Step 1: Add the existing public key**

Insert `condition_axis` into `_COMMON_EVIDENCE_FIELDS` and do not change the
projection loop or JSON sanitizer.

- [x] **Step 2: Run GREEN**

Run the focused Figure evidence/document tests and confirm existing role,
orientation, missing-evidence, and serialization assertions remain green.

### Task 3: Verify and checkpoint

**Files:**
- Modify: task card, plan, and durable memory after verification.

- [x] **Step 1: Run focused and complete SAXS matrices**

Use an isolated basetemp and record exact counts plus existing warnings.

- [x] **Step 2: Run task-scoped verification and diff checks**

Run the task verifier with the same isolated basetemp, then `git diff --check`.

- [x] **Step 3: Create one explicit allowlist checkpoint**

Use `scripts/auto_commit.py` with exactly the seven task-card paths; do not
include GUI, editor, or temporary workspace files.

## Plan self-review

- Every spec requirement maps to a task above.
- The only production change is one explicit projection allowlist entry.
- The RED test proves the existing projection really drops the new evidence.
