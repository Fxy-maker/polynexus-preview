# SAXS AI 1D Method Prompt Transport Implementation Plan

> **For agentic workers:** Execute this plan in order. This is a test-only transport contract; production changes require a failing regression and explicit scope review.

**Goal:** Verify all five existing SAXS 1D evidence families in the actual Advisor prompt.

**Architecture:** Reuse the existing Advisor normalization, PromptBuilder, and SAXS sanitizer. Capture the real prompt with the existing test LLM and assert only transport and safety invariants.

**Tech Stack:** Python, pytest, PowerShell, and the repository structured verifier.

---

### Task 1: Add the Advisor prompt regression

**Files:**
- Modify: `tests/test_advisor.py`

- [x] **Step 1: Define the evidence payload**

  Construct detached `metric_evidence` mappings for `guinier`, `porod`,
  `kratky`, `invariant`, and `lamellar`, with only existing compact fields.

- [x] **Step 2: Exercise the real Advisor path**

  Call `Advisor.advise()` with the existing context LLM and inspect
  `advisor.last_prompt`; do not call a provider or execute a candidate.

- [x] **Step 3: Run the focused regression**

  ```powershell
  python -m pytest -q tests/test_advisor.py tests/test_saxs_prompt_builder.py tests/test_saxs_ai_summary_context.py tests/test_saxs_ai_live_context.py -o addopts=
  ```

  Expected: complete summary and exit code `0`.

### Task 2: Verify complete SAXS boundaries

**Files:**
- Read-only: existing Advisor, PromptBuilder, SAXS AI, and SAXS test files

- [x] **Step 1: Run the complete SAXS matrix**

  ```powershell
  python -m pytest -q (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName }) -o addopts=
  ```

  A timeout or no-summary run is incomplete, not a pass.

- [x] **Step 2: Run structured verification and storage dry-runs**

  ```powershell
  python scripts/verify.py --task docs/agent/tasks/2026-08-01-saxs-ai-method-prompt-transport.md --changed --types
  python scripts/test_storage.py report --json
  python scripts/test_storage.py clean --older-than-hours 24 --json
  git diff --check
  ```

### Task 3: Record and checkpoint

**Files:**
- Create: `docs/acceptance/2026-08-01-saxs-ai-method-prompt-transport.md`
- Modify: the task/spec/plan files in this allowlist

- [x] **Step 1: Record exact summaries and limitations**

  Include the actual prompt regression, matrix, verifier, storage, and diff
  outcomes. Keep model authority and scientific review boundaries explicit.

- [x] **Step 2: Create the explicit checkpoint**

  ```powershell
  python scripts/auto_commit.py --message "test(saxs): verify Advisor method evidence prompt" --files tests/test_advisor.py docs/superpowers/specs/2026-08-01-saxs-ai-method-prompt-transport-design.md docs/superpowers/plans/2026-08-01-saxs-ai-method-prompt-transport.md docs/agent/tasks/2026-08-01-saxs-ai-method-prompt-transport.md docs/acceptance/2026-08-01-saxs-ai-method-prompt-transport.md
  ```

  Expected: one explicit allowlist commit and no push.
