# IR No-Implicit-PA6 Default Implementation Plan

> For agentic workers: use subagent-driven-development or executing-plans to implement this plan task-by-task.

Goal: Remove hidden PA6 assumptions from IR entry routing while preserving generic peak analysis and explicit material hints.

Architecture: Keep IR deterministic algorithms and reference library intact. Change only the two default-value boundaries and test the shared route. Context projection is already provided by ComputeRunService for DSC and will be extended only if needed for an explicit IR hint.

Tech Stack: Python, dataclasses, pytest.

---

### Task 1: Regression tests

Files:
- Create: tests/test_ftir_no_pa6_default.py

- [ ] Test that the registered IR standard submodule config schema default is empty.
- [ ] Test that temperature-series analysis forwards an empty polymer hint when IRConfig.polymer_name is empty by monkeypatching the module-level analyzer.
- [ ] Run the focused test and observe failures against current PA6 defaults.

### Task 2: Remove defaults

Files:
- Modify: polynexus/core/ir.py
- Modify: polynexus/core/ir_engine/ir_temperature.py

- [ ] Replace the standard submodule default with an empty string.
- [ ] Replace the temperature-series PA6 fallback with an empty string.
- [ ] Run new and existing focused IR tests.

### Task 3: Verification and checkpoint

Files:
- Modify: docs/agent/memory/active-work.md

- [ ] Run the task verifier and git diff --check.
- [ ] Confirm no-context ComputeRun calls remain valid.
- [ ] Create the allowlisted local checkpoint.
