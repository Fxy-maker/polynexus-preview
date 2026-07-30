# Joint AI Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the deterministic Joint AI-off and fallback boundary in the report context.

**Architecture:** Keep the existing rule-based `_build_joint_ai_context()` as the source of report summaries and add one static JSON-safe boundary object. No provider or GUI-specific branch is introduced.

**Tech Stack:** Python, pytest, existing Joint report contracts.

---

### Task 1: Add the failing report contract test

**Files:**
- Modify: `tests/test_joint_hub_dataset.py`

- [x] **Step 1: Assert the AI boundary on the existing clean and conflicted report fixtures**

```python
assert report["ai_context"]["ai_boundary"] == {
        "mode": "off",
        "provider_status": "not_configured",
        "fallback": "rule_based_report",
        "failure_policy": "preserve_source_evidence_and_diagnostic_status",
    }
```

- [x] **Step 2: Run the focused tests and confirm they fail because the payload is absent**

Run: `python -m pytest -q tests/test_joint_hub_dataset.py::test_joint_hub_dataset_collects_latest_runs_and_reports tests/test_joint_hub_dataset.py::test_joint_hub_report_builds_cross_tech_ai_context`

Observed: `2 failed`; both failed with `KeyError: 'ai_boundary'`.

### Task 2: Implement the static boundary payload

**Files:**
- Modify: `polynexus/core/joint/dataset.py`

- [x] **Step 1: Add the boundary to every returned AI context**

Add the same JSON-safe `ai_boundary` mapping to both the no-issue and issue
branches of `_build_joint_ai_context()`. Leave all counts, issue families,
weights, and recommendations unchanged.

### Task 3: Verify and checkpoint

**Files:**
- Modify: `docs/acceptance/2026-07-30-joint-ai-boundary.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] **Step 1: Run focused and real Joint tests**

Run: `$env:POLYNEXUS_TEST_RETENTION='review'; python -m pytest tests/test_joint_hub_dataset.py tests/test_joint_real_data_lifecycle.py -q`

Observed: `9 passed in 17.12s`, exit code `0`.

- [x] **Step 2: Run the structured verifier and create the explicit allowlist checkpoint**

Run: `python scripts/verify.py --task docs/agent/tasks/2026-07-30-joint-ai-boundary.md --changed --types`

Observed: task/memory, Ruff, compile, type baseline, quality `290`,
preprocessing `106`, and whitespace checks passed; exit code `0`. The broader
Joint matrix passed `27` tests in `28.92s`. The explicit allowlist checkpoint
is the only commit action for this slice.
