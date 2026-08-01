# SAXS 2D AI Context Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transport the existing 2D reviewer DTO through SAXS summary context and the prompt sanitizer with no new AI authority.

**Architecture:** Reuse the existing 2D core projector for trusted result evidence and add a fixed, fail-closed sanitizer for untrusted prompt context. Extend only the optional SAXS summary envelope; Advisor and execution contracts remain unchanged.

**Tech Stack:** Python 3.12, existing SAXS context contracts, pytest, repository verifier.

---

### Task 1: Add RED bridge and sanitizer tests

**Files:**
- Create: `tests/test_saxs_2d_ai_context_bridge.py`

- [x] **Step 1: Test trusted static projection**

Build an existing static result with detector/orientation evidence and assert
`build_saxs_ai_summary_context()` contains `saxs_2d_review_context` with the
existing `saxs.2d` scope and no raw fields.

- [x] **Step 2: Test prompt-side sanitization**

Pass a context containing a valid 2D DTO plus q/I, pixel, path, and unknown
instruction fields. Assert the prompt sanitizer retains only the fixed DTO,
does not mutate the input, and serializes with `allow_nan=False`.

- [x] **Step 3: Test absence compatibility**

Assert a normal 1D or empty SAXS result has no 2D context field and existing
prompt construction remains unchanged.

- [x] **Step 4: Run RED**

```powershell
$env:POLYNEXUS_TEST_ROOT='C:\PolyNexus-test-runs-saxs-2d-ai-red-20260731'
$env:POLYNEXUS_TEST_RETENTION='review'
python -m pytest -q tests/test_saxs_2d_ai_context_bridge.py -o addopts=
```

Observed: `4 failed, 2 passed in 0.87s`; the failures were the expected
missing optional field and sanitizer bridge.

### Task 2: Bridge trusted context and prompt sanitizer

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_2d_review_context.py`
- Modify: `polynexus/core/saxs_engine/saxs_ai_rescue.py`
- Modify: `polynexus/core/saxs_engine/__init__.py`

- [x] **Step 1: Add fixed DTO sanitizer**

Implement `sanitize_saxs_2d_review_context()` by accepting only the existing
DTO envelope and fixed nested fields; force raw-data flags to `False` and
return `{}` for wrong technique/scope or malformed input.

- [x] **Step 2: Add mode-result projection**

In `build_saxs_ai_summary_context()`, project the existing static,
temperature, or strain mode result into the optional field only when 2D
evidence is available. Reuse the existing audit/review payload and do not
read q/I or detector arrays.

- [x] **Step 3: Preserve the optional field at the prompt boundary**

In `sanitize_saxs_ai_summary_context()`, include only the result of
`sanitize_saxs_2d_review_context()`; absence keeps the previous context shape.

- [x] **Step 4: Export and run GREEN**

Observed: bridge `6 passed`; final focused bridge/Advisor/prompt/live
regression `32 passed`.

Export the sanitizer from `polynexus.core.saxs_engine` and run:

```powershell
$env:POLYNEXUS_TEST_ROOT='C:\PolyNexus-test-runs-saxs-2d-ai-green-20260731'
$env:POLYNEXUS_TEST_RETENTION='review'
python -m pytest -q tests/test_saxs_2d_ai_context_bridge.py tests/test_saxs_ai_summary_context.py tests/test_saxs_ai_acceptance_audit_context.py tests/test_saxs_prompt_builder.py tests/test_advisor.py -o addopts=
```

### Task 3: Verify and checkpoint

**Files:**
- Update: `docs/agent/tasks/2026-07-31-saxs-2d-ai-context-bridge.md`
- Update: `docs/superpowers/specs/2026-07-31-saxs-2d-ai-context-bridge-design.md`
- Update: `docs/superpowers/plans/2026-07-31-saxs-2d-ai-context-bridge.md`

- [x] **Step 1: Run the full SAXS matrix**

```powershell
$env:POLYNEXUS_TEST_ROOT='C:\PolyNexus-test-runs-saxs-2d-ai-saxs-20260731'
$env:POLYNEXUS_TEST_RETENTION='review'
python -m pytest -q (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName }) -o addopts=
```

Only a complete summary and exit code `0` count as pass evidence.

Observed: latest fresh matrix `707 passed, 6 warnings in 486.94s`, exit code `0`.

- [x] **Step 2: Run structured verification and dry-runs**

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-2d-ai-context-bridge.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24 --json
git diff --check
```

No storage `--apply` is allowed.

Observed: structured verifier exit code `0`, quality `297 passed`,
preprocessing `106 passed`; storage dry-runs reported `142` artifacts,
`15,743,185,346` eligible bytes, `removed=0`; `git diff --check` passed.
The latest task-card focused regression returned `26 passed in 0.41s`.

- [x] **Step 3: Checkpoint the exact allowlist**

```text
polynexus/core/saxs_engine/saxs_2d_review_context.py
polynexus/core/saxs_engine/saxs_ai_rescue.py
polynexus/core/saxs_engine/__init__.py
tests/test_saxs_2d_ai_context_bridge.py
docs/superpowers/specs/2026-07-31-saxs-2d-ai-context-bridge-design.md
docs/superpowers/plans/2026-07-31-saxs-2d-ai-context-bridge.md
docs/agent/tasks/2026-07-31-saxs-2d-ai-context-bridge.md
```

```powershell
python scripts/auto_commit.py --message "feat(saxs): bridge 2d review context to ai" --files polynexus/core/saxs_engine/saxs_2d_review_context.py polynexus/core/saxs_engine/saxs_ai_rescue.py polynexus/core/saxs_engine/__init__.py tests/test_saxs_2d_ai_context_bridge.py docs/superpowers/specs/2026-07-31-saxs-2d-ai-context-bridge-design.md docs/superpowers/plans/2026-07-31-saxs-2d-ai-context-bridge.md docs/agent/tasks/2026-07-31-saxs-2d-ai-context-bridge.md
```
