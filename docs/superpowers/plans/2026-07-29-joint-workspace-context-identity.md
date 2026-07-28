# Joint workspace context identity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the remaining `No data loaded` contradiction from the Joint
Workbench workspace context line when a report already has a sample identity.

**Architecture:** Reuse the existing display-only Joint identity resolver at
the `MainWindowWorkspaceMixin._workspace_context_summary_text()` boundary.
No data model or persistence contract changes.

**Tech Stack:** Python, PySide6 mixins, pytest, Windows Qt route harness.

---

### Task 1: Bind the workspace context identity

**Files:**
- Modify: `polynexus/gui/main_window_workspace_mixin.py`
- Modify: `tests/test_main_window_workspace_mixin.py`

- [x] **Step 1: Write and run the failing regression**

Build a Joint workspace context with a report row for `PA6-A`, render the
summary, and assert that it contains `PA6-A` and not the no-data placeholder.
The RED run failed because the summary rendered the translated no-data text.

- [x] **Step 2: Implement the minimal binding**

When `context.technique == "joint"`, resolve the source label from the active
`_joint_report` with `resolve_joint_history_project_label("", report)`.

- [x] **Step 3: Run the focused regression**

```powershell
python -m pytest -q tests/test_main_window_workspace_mixin.py::test_joint_workspace_context_uses_report_identity_instead_of_no_data -vv
```

Observed: `1 passed`.

### Task 2: Verify and checkpoint

**Files:**
- `polynexus/gui/main_window_workspace_mixin.py`
- `tests/test_main_window_workspace_mixin.py`
- this task card, spec, plan, acceptance note, and `active-work.md`

- [x] **Step 1: Run the focused Workspace/Joint matrix and structured verifier**

```powershell
python -m pytest -q tests/test_main_window_workspace_mixin.py tests/test_joint_history_project_identity.py tests/test_context_suggestion_service.py tests/test_joint_hub_dataset.py tests/test_main_window_persistence.py -k "workspace or workflow_task or joint or history_project_identity or persistence_keeps_raw_project_identity"
python scripts/verify.py --task docs/agent/tasks/2026-07-29-joint-workspace-context-identity.md --changed --types
git diff --check
```

- [x] **Step 2: Run the native Joint route and create the allowlist checkpoint**

The focused matrix returned `42 passed, 177 deselected in 38.36s`; the
structured verifier exited `0` with quality `287` and preprocessing `106`;
diff check passed. The native Joint selector returned `1 passed, 16
deselected in 9.20s`, and the fresh capture shows `PA6-A` in both header
locations. Use `scripts/auto_commit.py` with only the explicit task-card
allowlist; do not include `current-state.md`, generated outputs, or scratch.
