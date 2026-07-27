# SAXS Workbench review evidence readability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separate existing SAXS Workbench review sections into ordered lines
while preserving the string presentation contract and all evidence content.

**Architecture:** Keep the existing presentation-only section builders and
their order. Replace the final space joins with newline joins, omitting empty
sections. The SAXS engine, evidence DTOs, and persistence boundaries remain
untouched.

**Tech Stack:** Python, Pytest, Qt QLabel word wrapping, Ruff, and the project
structured verifier.

---

### Task 1: Lock the presentation contract with RED

**Files:**
- Create: `tests/test_saxs_workbench_review_readability.py`

- [x] **Step 1: Write the failing regression**

Build a payload containing metric, Guinier sequence, detector, and data-quality
review sections. Assert each source remains ordered, each section is on its own
line, and the original payload is unchanged.

- [x] **Step 2: Run RED**

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_workbench_review_red'
python -m pytest -q tests/test_saxs_workbench_review_readability.py
```

Expected: failure because the current presentation uses spaces between review
sections.

### Task 2: Change only the final presentation separators

**Files:**
- Modify: `polynexus/gui/saxs_results_table_service.py` in
  `build_saxs_results_presentation()`.

- [x] **Step 1: Apply the minimal implementation**

Collect the existing risk and next strings in local tuples and use:

```python
risk_text = "\n".join(text for text in risk_sections if text)
next_text = "\n".join(text for text in next_sections if text)
```

- [x] **Step 2: Run focused GREEN**

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_workbench_review_focus'
python -m pytest -q tests/test_saxs_workbench_review_readability.py tests/test_saxs_workbench_series_evidence.py tests/test_saxs_results_table_service.py tests/test_saxs_workbench_figure_contracts.py tests/test_results_workbench_profiles.py
```

Evidence: `104 passed`.

### Task 3: Verify and checkpoint

- [x] **Step 1: Run the exact SAXS matrix and task verifier**

Exact SAXS matrix evidence: `419 passed, 6 warnings` in 37.27s. The task
verifier passed with quality `283`, preprocessing `106`, Ruff, compile,
memory/task, and whitespace checks. `git diff --check` passed.

- [x] **Step 2: Update task/spec/plan and durable memory with actual evidence**

Post-change full/boundary verification passed: `2851 passed, 17 skipped, 12
warnings` in 1567.25s; quality `283`, preprocessing `106`, compile,
whitespace, and boundary audit passed.

- [x] **Step 3: Create one explicit allowlist checkpoint**

```powershell
python scripts/auto_commit.py --message "fix(saxs): separate workbench review evidence" --files polynexus/gui/saxs_results_table_service.py tests/test_saxs_workbench_review_readability.py docs/agent/tasks/2026-07-28-saxs-workbench-review-readability.md docs/superpowers/specs/2026-07-28-saxs-workbench-review-readability-design.md docs/superpowers/plans/2026-07-28-saxs-workbench-review-readability.md docs/agent/memory/current-state.md docs/agent/memory/active-work.md
```

Do not include the pre-existing native GUI harness modification, release docs,
scratch directories, or `.superpowers/`.
