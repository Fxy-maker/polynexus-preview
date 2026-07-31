# SAXS AI Finite Confidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reject non-finite AI confidence values before they enter the Advisor decision path.

**Architecture:** Reuse the existing `_normalize_advice()` and `Advisor.advise()` fallback boundary. Add `math.isfinite()` after conversion and before clamping; do not introduce a parallel response schema or policy.

**Tech Stack:** Python, Pytest, existing `rag.Advisor` and SAXS AI regressions.

---

### Task 1: Add the failing provider regression

**Files:**
- Modify: `tests/test_advisor.py`

- [x] **Step 1: Write the failing test**

Add a fake provider returning `confidence: "NaN"` and assert the existing
fallback response is returned by `Advisor.advise()`.

- [x] **Step 2: Run RED**

```powershell
python -m pytest -q tests/test_advisor.py::test_advisor_falls_back_on_nonfinite_provider_confidence -o addopts=
```

Expected result: failure because `float("NaN")` currently normalizes to a
non-finite value instead of entering the fallback.

### Task 2: Add the finite guard

**Files:**
- Modify: `rag/advisor.py`

- [x] **Step 1: Implement the minimal guard**

Import `math`, convert confidence as before, raise `ValueError` when the
converted value is not finite, then retain the existing `[0.0, 1.0]` clamp.

- [x] **Step 2: Run GREEN**

```powershell
python -m pytest -q tests/test_advisor.py tests/test_saxs_ai_live_context.py tests/test_saxs_ai_summary_context.py tests/test_saxs_prompt_builder.py -o addopts=
```

Expected result: complete summary and exit code `0`.

### Task 3: Verify and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-31-saxs-ai-finite-confidence.md`

- [x] **Step 1: Run the AI/preprocess and exact SAXS matrices**

```powershell
python -m pytest -q -o addopts= tests/test_advisor.py tests/test_saxs_ai_live_context.py tests/test_saxs_ai_summary_context.py tests/test_saxs_prompt_builder.py tests/test_saxs_ai_orchestrator_handoff.py tests/test_saxs_ai_rescue_bridge.py tests/test_saxs_ai_confirmed_rerun_safety.py tests/test_preprocess_replay_contract.py tests/test_preprocess_cross_technique_matrix.py tests/test_preprocess_ai_off_compat.py tests/test_preprocess_fault_injection.py
python -m pytest -q -o addopts= (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName })
```

- [x] **Step 2: Run structured verification and dry-runs**

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-ai-finite-confidence.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24 --json
git diff --check
```

Do not run `test_storage.py --apply`.

- [x] **Step 3: Create the explicit checkpoint**

```powershell
python scripts/auto_commit.py --message "fix(saxs): reject nonfinite ai confidence" --files rag/advisor.py tests/test_advisor.py docs/superpowers/specs/2026-07-31-saxs-ai-finite-confidence-design.md docs/superpowers/plans/2026-07-31-saxs-ai-finite-confidence.md docs/agent/tasks/2026-07-31-saxs-ai-finite-confidence.md
```
