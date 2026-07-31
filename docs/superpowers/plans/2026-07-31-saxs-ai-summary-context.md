# SAXS AI Summary Context Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development. Execute each task in order and checkpoint only the explicit allowlist.

**Goal:** Add a deterministic summary-only SAXS AI context contract and bind it to the existing SAXS prompt without changing analysis or decision authority.

**Architecture:** The SAXS rescue bridge owns the detached context projection by reusing its existing evidence projection and status assessment. `PromptBuilder` consumes the optional JSON-safe context and states its candidate-only boundary; validation and candidate decisions remain in the existing preprocessing contracts.

**Tech Stack:** Python, dataclasses/JSON, existing SAXS evidence contracts, pytest.

---

### Task 1: Define the task boundary

**Files:**
- Create: `docs/superpowers/specs/2026-07-31-saxs-ai-summary-context-design.md`
- Create: `docs/superpowers/plans/2026-07-31-saxs-ai-summary-context.md`
- Create: `docs/agent/tasks/2026-07-31-saxs-ai-summary-context.md`

- [x] Record the summary-only input decision, safety boundaries, affected files, and explicit allowlist.

### Task 2: Write and run RED tests

**Files:**
- Test: `tests/test_saxs_ai_summary_context.py`
- Test: `tests/test_saxs_prompt_builder.py`

- [ ] Add one test that builds a context from a synthetic temperature result and asserts strict JSON, existing gate statuses, and absence of q/I/raw detector fields.
- [ ] Add one test that unsupported mode or missing result is unavailable and does not fabricate frame evidence.
- [ ] Add one prompt test that supplied context appears with the no-raw-data and candidate-only boundary.
- [ ] Run the focused tests and confirm collection fails because the new context builder is not yet available.

### Task 3: Implement the minimal GREEN path

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_ai_rescue.py`
- Modify: `polynexus/core/saxs_engine/__init__.py`
- Modify: `rag/prompt_builder.py`

- [ ] Add `build_saxs_ai_summary_context(result, *, mode)` that reuses existing evidence projection/assessment and adds only the explicit input-boundary flags.
- [ ] Export the helper through the SAXS engine public module.
- [ ] In `_build_saxs_prompt`, render only an optional JSON context block and tell the model to return the existing intent JSON; keep the no-context prompt unchanged.
- [ ] Run the focused tests and confirm all pass.

### Task 4: Verify and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-31-saxs-ai-summary-context.md`
- Create: `docs/acceptance/2026-07-31-saxs-ai-summary-context.md`

- [ ] Run the focused summary/prompt tests.
- [ ] Run the exact SAXS matrix with a complete pytest summary and exit code.
- [ ] Run `python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-ai-summary-context.md --changed --types` and `git diff --check`.
- [ ] Run storage report and clean dry-run only; do not use `--apply`.
- [ ] Review the diff and create one explicit allowlist checkpoint with `scripts/auto_commit.py`.
