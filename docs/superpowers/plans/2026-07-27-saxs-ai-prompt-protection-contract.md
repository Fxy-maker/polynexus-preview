# SAXS AI Prompt Protection Contract Implementation Plan

> **For agentic workers:** Use test-driven development and verify before completion. Steps use checkbox syntax.

**Goal:** Tell the AI exactly which SAXS physical features must be protected
when emitting a preprocessing intent.

**Architecture:** Reuse the active `PreprocessPolicy` in the existing prompt
builder. Only the prompt contract changes; the SAXS bridge remains the final
validator.

**Tech Stack:** Python, PromptBuilder, pytest.

---

### Task 1: Lock the prompt contract

**Files:**
- Modify: `tests/test_saxs_prompt_builder.py`

- [x] Add a regression that requests SAXS preprocessing and asserts every
  policy-protected feature appears in the prompt.
- [x] Run the regression before implementation and observe the placeholder
  contract fail the assertion.

### Task 2: Render policy features

**Files:**
- Modify: `rag/prompt_builder.py`

- [x] Serialize `policy.allowed_protected_features` into the intent example.
- [x] Add SAXS wording requiring every listed feature while preserving generic
  wording for other techniques.
- [x] Run the focused prompt suite and the existing SAXS/preprocess matrix.

### Task 3: Verify and checkpoint

**Files:**
- Update: task card and durable memory.

- [x] Run the structured verifier and whitespace check.
- [ ] Create the allowlist-only checkpoint with `scripts/auto_commit.py`.
