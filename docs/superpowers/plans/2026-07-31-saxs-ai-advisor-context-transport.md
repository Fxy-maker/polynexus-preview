# SAXS AI Advisor Context Transport Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development. Execute each task in order and checkpoint only the explicit allowlist.

**Goal:** Carry the existing summary-only SAXS AI context through the real Advisor normalization path.

**Architecture:** `Advisor._normalize_case()` retains the optional context as a detached mapping field. The existing `PromptBuilder` sanitizer remains the only prompt boundary; no model or preprocessing authority changes.

**Tech Stack:** Python, existing `Advisor`, `PromptBuilder`, pytest.

---

### Task 1: Define the task boundary

**Files:**
- Create: `docs/superpowers/specs/2026-07-31-saxs-ai-advisor-context-transport-design.md`
- Create: `docs/superpowers/plans/2026-07-31-saxs-ai-advisor-context-transport.md`
- Create: `docs/agent/tasks/2026-07-31-saxs-ai-advisor-context-transport.md`

- [x] Record the transport-only decision and explicit allowlist.

### Task 2: Write and run the RED regression

**Files:**
- Test: `tests/test_advisor.py`

- [ ] Add a fake retriever/LLM test that calls `Advisor.advise()` with a SAXS summary context and asserts the actual `last_prompt` contains the context section.
- [ ] Run the focused test and observe failure because `_normalize_case()` drops the field.

### Task 3: Implement the minimal GREEN change

**Files:**
- Modify: `rag/advisor.py`

- [ ] Preserve only a mapping-valued `saxs_ai_context` in the normalized case.
- [ ] Leave all existing case fields and no-context behavior unchanged.
- [ ] Run Advisor and prompt regressions.

### Task 4: Verify and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-31-saxs-ai-advisor-context-transport.md`
- Create: `docs/acceptance/2026-07-31-saxs-ai-advisor-context-transport.md`

- [ ] Run focused Advisor/prompt/AI tests and the exact SAXS matrix.
- [ ] Run task-scoped verification and `git diff --check`.
- [ ] Run storage report and clean dry-run only.
- [ ] Create one explicit allowlist checkpoint with `scripts/auto_commit.py`.
