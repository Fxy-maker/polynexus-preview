# Joint workflow task identity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep the Joint Workbench task card consistent with the existing
report identity instead of displaying `No data loaded` for a populated report.

**Architecture:** Reuse the existing display-only Joint identity resolver at
the Workbench context boundary. The task card receives the resolved identity
as its source field; the report and persistence payload remain unchanged.

**Tech Stack:** Python, PySide6 mixins, pytest, repository task verifier.

---

### Task 1: Protect the Joint task-card source contract

**Files:**
- Modify: `tests/test_main_window_workspace_mixin.py`
- Modify: `polynexus/gui/main_window_workspace_mixin.py`

- [x] **Step 1: Write the failing regression**

Create a fake Workspace window with `technique="joint"` and a report row whose
sample is `PA6-A`; call `_workflow_task_context()` and assert
`task["source"] == "PA6-A"`.

- [x] **Step 2: Run the regression and observe the expected failure**

```powershell
python -m pytest -q tests/test_main_window_workspace_mixin.py::test_joint_workflow_task_uses_report_identity_instead_of_no_data -vv
```

Observed: `1 failed`; actual source was `No data loaded`.

- [x] **Step 3: Implement the minimal display-only binding**

In `_workflow_task_context()`, when `tech == "joint"`, pass the current
`_joint_report` through `resolve_joint_history_project_label("", report)` and
use the returned value as `source_name`.

- [x] **Step 4: Run the focused matrix**

```powershell
python -m pytest -q tests/test_main_window_workspace_mixin.py tests/test_joint_history_project_identity.py tests/test_context_suggestion_service.py tests/test_joint_hub_dataset.py tests/test_main_window_persistence.py -k "workspace or workflow_task or joint or history_project_identity or persistence_keeps_raw_project_identity"
```

Observed: `41 passed, 177 deselected`.

### Task 2: Verify and checkpoint

**Files:**
- `polynexus/gui/main_window_workspace_mixin.py`
- `tests/test_main_window_workspace_mixin.py`
- this plan, task card, spec, and acceptance note

- [x] **Step 1: Run the structured verifier**

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-29-joint-workflow-task-identity.md --changed --types
```
- [x] **Step 2: Run `git diff --check` and create the explicit allowlist checkpoint**

The verifier exited `0` with quality `287` and preprocessing `106`; diff check
passed. Use `scripts/auto_commit.py` with only the files listed in the task
card. Do not include `current-state.md`, generated outputs, or scratch
directories.
