# Real Evaluation Output Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Prevent real evaluation runs from writing generated artifacts into input data directories when an external output root is supplied.

**Architecture:** Add one optional harness-only case override at the runner boundary. The runner forwards it to the already-public engine `output_dir` parameter; no engine or scientific contract changes.

**Tech Stack:** Python, pytest, existing EvalRunner and NMR bridge test double.

---

### Task 1: Write the forwarding regression

**Files:**
- Modify: `tests/eval/test_nmr_vendor_real_case_registry.py`
- Create: `docs/superpowers/specs/2026-07-31-real-eval-output-isolation-design.md`
- Create: `docs/superpowers/plans/2026-07-31-real-eval-output-isolation.md`
- Create: `docs/agent/tasks/2026-07-31-real-eval-output-isolation.md`
- Create: `docs/acceptance/2026-07-31-real-eval-output-isolation.md`

- [x] **Step 1: Add a fake-engine forwarding test**

Load one registered NMR case, replace its `eval_output_dir` with `tmp_path`,
patch `polynexus.core.get_engine`, and assert the fake receives the exact
external output path. The test must not invoke the real engine.

- [x] **Step 2: Run RED**

Run `python -m pytest -q tests/eval/test_nmr_vendor_real_case_registry.py -k output_isolation -vv`: `1 failed, 6 deselected` because the runner passed an empty output directory.

### Task 2: Implement the harness-only forwarding

**Files:**
- Modify: `tests/eval/runner.py`

- [x] **Step 1: Forward the optional directory**

In `_run_real_engine`, compute `output_dir = str(case.config_overrides.get("eval_output_dir") or "")` and pass it to the existing `engine.run_pipeline` call. Do not pass the field into engine config aliases.

- [x] **Step 2: Run GREEN**

Run the isolation test, then the full registry plus bridge matrix. Confirm the
 four actual registry tests still write only under pytest-owned external paths.

### Task 3: Verify and checkpoint

**Files:**
- The runner, existing registry test, and four task documents only.

- [x] **Step 1: Run focused tests**

Run `python -m pytest -q tests/eval/test_nmr_vendor_real_case_registry.py tests/eval/test_runner_real_nmr.py -vv`: `8 passed in 143.03s`, exit code `0`.

- [x] **Step 2: Run structured checks**

Run `python scripts/verify.py --task docs/agent/tasks/2026-07-31-real-eval-output-isolation.md --changed --types`: exit code `0`; task-check, memory check, Ruff, compile, type baseline, quality gate (`297 passed`), preprocessing (`106 passed`), and whitespace checks passed. `git diff --check` also exited `0`.

- [x] **Step 3: Create one explicit checkpoint**

Use `scripts/auto_commit.py` with only the six allowlisted files. Do not
include parallel SAXS, memory, source data, or scratch directories.

Checkpoint creation is the final handoff action for this task.
