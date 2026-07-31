# Advisor Provider Failure Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep malformed provider responses inside the existing Advisor mock fallback while preserving explicit user cancellation.

**Architecture:** The existing `Advisor.advise()` exception boundary owns provider call, JSON parsing, and response normalization. The fallback remains the existing `_mock_response()` path; only the placement of `_normalize_advice()` changes. Tests use injected retriever/LLM doubles already established in `tests/test_advisor.py`.

**Tech Stack:** Python, pytest, existing `Advisor` and `LLMCancelledError` contracts.

---

### Task 1: Verify provider failure and cancellation contracts

**Files:**
- Modify: `rag/advisor.py`
- Test: `tests/test_advisor.py`

- [x] **Step 1: Add the malformed-response regression**

Use an injected provider returning a response that parses as JSON but fails
the existing numeric normalization, and assert the existing
`provider_unavailable` mock response with `llm_used=False`.

- [x] **Step 2: Add the cancellation regression**

Use an injected provider that raises `LLMCancelledError` and assert the same
exception escapes `Advisor.advise()`.

- [x] **Step 3: Move normalization into the ordinary provider exception boundary**

Keep the control-flow branch unchanged:

```python
try:
    parsed = self._parse_response(raw)
    parsed["llm_used"] = not self.llm_client.last_used_mock
    normalized = self._normalize_advice(parsed)
except LLMCancelledError:
    raise
except Exception as exc:
    fallback = self._mock_response(retrieved, str(exc))
    fallback["llm_used"] = False
    normalized = self._normalize_advice(fallback)
```

- [x] **Step 4: Run the focused regression**

Run:

```powershell
$env:POLYNEXUS_TEST_ROOT='D:\PolyNexus-test-runs-advisor-fallback'
$env:POLYNEXUS_TEST_RETENTION='ephemeral'
python -m pytest -q tests/test_advisor.py -o addopts=
```

Expected: all Advisor tests pass with a complete pytest summary and exit code
`0`.

### Task 2: Verify shared contracts and record the checkpoint

**Files:**
- Create: `docs/acceptance/2026-07-31-advisor-provider-fallback.md`
- Modify: `docs/agent/tasks/2026-07-31-advisor-provider-fallback.md`
- Include: `docs/superpowers/specs/2026-07-31-advisor-provider-fallback-design.md`
- Include: `docs/superpowers/plans/2026-07-31-advisor-provider-fallback.md`

- [x] **Step 1: Run the Advisor/shared focused matrix**

Run the focused Advisor, prompt, summary, and live-context tests with an
external basetemp and record the exact summary.

- [x] **Step 2: Run the structured verifier**

Run:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-31-advisor-provider-fallback.md --changed --types
git diff --check
```

Record the exact exit code and every selected gate count; a timeout or missing
summary remains incomplete.

- [x] **Step 3: Create one explicit allowlist checkpoint**

Use `scripts/auto_commit.py` with only the production file, regression test,
spec, plan, task, and acceptance files listed in the task card. Do not include
parallel memory, real data, scratch, or test-storage paths.
