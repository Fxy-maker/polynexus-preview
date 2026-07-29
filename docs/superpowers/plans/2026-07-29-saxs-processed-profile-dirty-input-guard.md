# SAXS ProcessedProfile dirty-input guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep the canonical SAXS processed-profile projection usable and explicit when individual numeric tokens are malformed.

**Architecture:** Add one private elementwise coercion helper in
`processed_profile.py`. `ProcessedProfile.__post_init__()` uses it for every
numeric layer and merges per-layer invalid counts into diagnostics. The SAXS
payload adapter uses the same helper for q/raw before its existing length checks;
all analysis inputs and scientific contracts remain untouched.

**Tech Stack:** Python dataclasses, NumPy, pytest, existing SAXS projection and
verification scripts.

---

### Task 1: Add the failing projection regressions

**Files:**
- Modify: `tests/test_saxs_processed_profile.py`

- [ ] **Step 1: Write the failing tests**

Add tests that construct a `ProcessedProfile` with one malformed token in each
numeric layer, assert same-position `NaN`, per-layer counts, `WARN`, and input
immutability. Add a payload-adapter test with malformed q/raw and one optional
layer, plus clean-input coverage for `OK`.

- [ ] **Step 2: Run the focused tests to verify RED**

Run:

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_processed_profile_dirty_red'
python -m pytest -q tests/test_saxs_processed_profile.py
```

Expected before implementation: the dirty `ProcessedProfile` construction and
dirty payload projection fail with the existing whole-array conversion error.

### Task 2: Implement the minimal projection guard

**Files:**
- Modify: `polynexus/core/saxs_engine/processed_profile.py`
- Modify: `polynexus/core/saxs.py`

- [ ] **Step 1: Add elementwise coercion**

Convert each element independently, placing `numpy.nan` on conversion failure;
return the invalid count to the caller without mutating the source object.

- [ ] **Step 2: Apply it to all projection layers**

Use the helper in `ProcessedProfile.__post_init__()`, merge nonzero counts into
`diagnostics["invalid_numeric_values"]`, and force `quality_status="WARN"`
when any count is nonzero.

- [ ] **Step 3: Apply it to q/raw in the payload adapter**

Use the same helper before the existing q/raw length and optional-layer checks;
preserve all existing mismatch diagnostics and provenance.

- [ ] **Step 4: Run the focused tests to verify GREEN**

Run the same focused command and confirm the clean and dirty projection tests
pass.

### Task 3: Verify and checkpoint

**Files:**
- Modify: `polynexus/core/saxs_engine/processed_profile.py`
- Modify: `polynexus/core/saxs.py`
- Modify: `tests/test_saxs_processed_profile.py`
- Add: `docs/agent/tasks/2026-07-29-saxs-processed-profile-dirty-input-guard.md`
- Add: `docs/superpowers/specs/2026-07-29-saxs-processed-profile-dirty-input-guard-design.md`
- Add: `docs/superpowers/plans/2026-07-29-saxs-processed-profile-dirty-input-guard.md`
- Modify: `docs/agent/memory/active-work.md`
- Add: `docs/acceptance/2026-07-29-saxs-processed-profile-dirty-input-guard.md`

- [ ] **Step 1: Run the focused and SAXS verification matrix**

Run the focused projection tests, the exact SAXS test-file matrix with an
external basetemp, and the structured verifier. Record timeout/no-summary as a
limitation rather than a pass.

- [ ] **Step 2: Review the scoped diff**

Run `git diff --check` and verify the explicit allowlist excludes all existing
parallel changes and generated test output.

- [ ] **Step 3: Update evidence and create the checkpoint**

Record exact outcomes in the task card, acceptance note, and active work; then
run `scripts/auto_commit.py` with only the explicit allowlist.
