# SAXS Live Advisor Summary Context Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bind existing SAXS summary evidence to the live Advisor state for static, temperature, and strain modes.

**Architecture:** Add one private mode/result selector in `orchestrator_state.py`, then call the existing `build_saxs_ai_summary_context()` projection. Keep prompt rendering, intent validation, candidate execution, and decision authority in their existing modules.

**Tech Stack:** Python, `SimpleNamespace` test fixtures, pytest, existing SAXS strict-JSON context contract, Ruff, and repository verifier.

---

### Task 1: Add live-state regression coverage

**Files:**
- Create: `tests/test_saxs_ai_live_context.py`

- [ ] **Step 1: Write the failing tests**

Add tests that build a minimal `ParameterOrchestrator` state and assert:

```python
state = orchestrator._build_agent_state(engine, 1)
assert state["saxs_ai_context"]["mode"] == expected_mode
assert state["saxs_ai_context"]["candidate_only"] is True
assert state["saxs_ai_context"]["physical_validation_required"] is True
```

Cover static `engine.result`, temperature `_temperature_result`, strain
`_strain_result`, raw-field exclusion, and a projection exception returning
an empty context.

- [ ] **Step 2: Run RED**

Run `python -m pytest -q tests/test_saxs_ai_live_context.py -o addopts=`.
Expected: the tests fail because `_build_agent_state()` does not yet attach
`saxs_ai_context`.

### Task 2: Bind the existing projection into orchestrator state

**Files:**
- Modify: `polynexus/orchestrator_state.py`

- [ ] **Step 1: Implement mode/result selection**

Select `_temperature_result` first, `_strain_result` second, and `result`
otherwise. Map these to `temperature`, `strain`, and `static` respectively.

- [ ] **Step 2: Build the fail-closed context**

For SAXS only, call `build_saxs_ai_summary_context(selected_result, mode=mode)`
inside a narrow `TypeError`/`ValueError` guard; use `{}` on projection failure.
Add the detached context to the returned state as `saxs_ai_context`.

- [ ] **Step 3: Run GREEN and compatibility tests**

Run `python -m pytest -q tests/test_saxs_ai_live_context.py tests/test_advisor.py tests/test_saxs_prompt_builder.py tests/test_saxs_ai_summary_context.py -o addopts=`.
Expected: all tests pass and existing no-context behavior remains unchanged.

### Task 3: Verify and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-31-saxs-live-advisor-summary-context.md`

- [ ] **Step 1: Run the SAXS matrix and structured verifier**

Run the exact PowerShell-expanded SAXS matrix and
`python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-live-advisor-summary-context.md --changed --types`.

- [ ] **Step 2: Run storage dry-runs and diff check**

Run `python scripts/test_storage.py report --json`,
`python scripts/test_storage.py clean --older-than-hours 24 --json`, and
`git diff --check`. Do not run `test_storage.py --apply`.

- [ ] **Step 3: Create one explicit allowlist checkpoint**

Use `scripts/auto_commit.py` with only `orchestrator_state.py`, the focused
test, and this task/spec/plan. Leave existing memory, scratch, generated
outputs, and test-storage paths untouched.
