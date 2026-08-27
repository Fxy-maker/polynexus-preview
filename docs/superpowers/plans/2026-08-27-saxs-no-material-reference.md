# SAXS No-Material Reference Implementation Plan

> For agentic workers: use subagent-driven-development or executing-plans to implement this plan task-by-task.

Goal: Remove the PA6 filename special case from static SAXS reference selection.

Architecture: Keep SAXS calculations unchanged and isolate the change to reference-index selection after per-frame analysis.

Tech Stack: Python, NumPy, pytest.

---

### Task 1: Regression tests

Files:
- Create: tests/test_saxs_no_material_reference.py

- [ ] Build a minimal fake SAXS engine state with two analyzed frames and filenames where only the later frame contains PA6.
- [ ] Assert the selected reference is the first finite-invariant frame, not the PA6-named frame.
- [ ] Run the focused test and observe failure against the current filename branch.

### Task 2: Minimal implementation

Files:
- Modify: polynexus/core/saxs.py

- [ ] Replace filename scanning with finite-invariant index selection and deterministic fallback.
- [ ] Run focused SAXS tests and confirm calibration behavior is unchanged apart from reference choice.

### Task 3: Verification and checkpoint

Files:
- Modify: docs/agent/memory/active-work.md

- [ ] Run structured verification and whitespace checks.
- [ ] Create the allowlisted local checkpoint.
