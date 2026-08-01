# SAXS AI 1D Method Evidence Context Implementation Plan

> **For agentic workers:** Use this plan task-by-task. This slice is test-first contract coverage; production code changes are allowed only if the focused regression proves the existing boundary is incomplete.

**Goal:** Lock the existing five-method SAXS evidence projection into the AI summary contract for Static, Temperature, and Strain.

**Architecture:** Reuse the current `metric_evidence` projection and sanitizer. Add only a focused parameterized regression and durable evidence; preserve all existing decision and publication authority.

**Tech Stack:** Python, pytest, PowerShell, and the repository structured verifier.

---

### Task 1: Add the method-family contract regression

**Files:**
- Modify: `tests/test_saxs_ai_summary_context.py`

- [x] **Step 1: Define the expected contract**

  For each mode in `static`, `temperature`, and `strain`, construct existing
  `metric_evidence` entries for `guinier`, `porod`, `kratky`, `invariant`, and
  `lamellar`, then assert every key survives under `context["series"]` and
  remains strict JSON.

- [x] **Step 2: Add the parameterized test**

  The test uses `SimpleNamespace` result/series objects and existing summary
  API only. It does not call a model or write a configuration.

- [x] **Step 3: Run the focused regression**

  Run:

  ```powershell
  python -m pytest -q tests/test_saxs_ai_summary_context.py tests/test_saxs_prompt_builder.py tests/test_advisor.py -o addopts=
  ```

  Expected: complete summary and exit code `0`. This is contract coverage, not
  a production behavior change; no production RED/GREEN claim is made.

### Task 2: Verify adjacent prompt and SAXS boundaries

**Files:**
- Read-only: existing SAXS AI, Advisor, prompt, and SAXS test files

- [x] **Step 1: Run the combined focused suite**

  ```powershell
  python -m pytest -q tests/test_saxs_ai_summary_context.py tests/test_saxs_ai_live_context.py tests/test_saxs_prompt_builder.py tests/test_advisor.py tests/test_saxs_ai_acceptance_audit_context.py -o addopts=
  ```

- [x] **Step 2: Run the complete SAXS matrix**

  ```powershell
  python -m pytest -q (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName }) -o addopts=
  ```

  A timeout or no-summary run is incomplete, never a pass.

### Task 3: Verify and checkpoint

**Files:**
- Create: `docs/acceptance/2026-08-01-saxs-ai-method-evidence-context.md`
- Modify: task/spec/plan files in the explicit allowlist

- [x] **Step 1: Run the structured verifier, storage dry-runs, and diff check**

  ```powershell
  python scripts/verify.py --task docs/agent/tasks/2026-08-01-saxs-ai-method-evidence-context.md --changed --types
  python scripts/test_storage.py report --json
  python scripts/test_storage.py clean --older-than-hours 24 --json
  git diff --check
  ```

- [x] **Step 2: Record exact evidence and limitations**

  Write complete summaries and exit codes into the acceptance record. Keep
  scientific approval, real detector interpretation, and release approval
  explicitly outside this automated slice.

- [x] **Step 3: Create the explicit checkpoint**

  ```powershell
  python scripts/auto_commit.py --message "test(saxs): cover AI method evidence context" --files tests/test_saxs_ai_summary_context.py docs/superpowers/specs/2026-08-01-saxs-ai-method-evidence-context-design.md docs/superpowers/plans/2026-08-01-saxs-ai-method-evidence-context.md docs/agent/tasks/2026-08-01-saxs-ai-method-evidence-context.md docs/acceptance/2026-08-01-saxs-ai-method-evidence-context.md
  ```

  Expected: one explicit allowlist commit and no push.
