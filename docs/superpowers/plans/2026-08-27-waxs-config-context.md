# WAXS Configuration and Context Implementation Plan

> For agentic workers: use subagent-driven-development or executing-plans to implement this plan task-by-task.

Goal: Preserve explicit WAXS configuration and project context through the shared compute route.

Architecture: Keep numerical WAXS algorithms unchanged. Fix the engine constructor to retain a WAXSConfig or mapping, add a validated optional context property, and project only an explicit crystal-form hint at the ComputeRun boundary.

Tech Stack: Python, dataclasses, pytest.

---

### Task 1: Regression tests

Files:
- Create: tests/test_waxs_config_context.py

- [ ] Test WAXSEngine preserves a supplied WAXSConfig value.
- [ ] Test ComputeRun applies a valid WAXS context hint to an empty provider config.
- [ ] Test invalid WAXS context hints fail closed before provider execution.
- [ ] Run the focused tests and observe failures.

### Task 2: Minimal implementation

Files:
- Modify: polynexus/core/waxs.py
- Modify: polynexus/core/project_context.py
- Modify: polynexus/core/compute/service.py

- [ ] Preserve WAXSConfig instances and load mappings with WAXSConfig.from_dict.
- [ ] Add validated waxs_polymer_type to ProjectContext.
- [ ] Project the hint only if the provider config has no explicit polymer_type.
- [ ] Run WAXS and ComputeRun focused tests.

### Task 3: Verification and checkpoint

Files:
- Modify: docs/agent/memory/active-work.md

- [ ] Run the task verifier and whitespace check.
- [ ] Create the allowlisted local checkpoint.
