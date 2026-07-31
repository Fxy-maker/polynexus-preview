# SAXS AI Replay Application Binding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Synchronize SAXS AI replay rows with the final shared transaction decision and actual application result.

**Architecture:** Preserve candidate generation and evidence evaluation. Extend the generic replay audit with a backward-compatible application flag, and build SAXS replay rows after the existing commit decision so the audit reflects the final state.

**Tech Stack:** Python, dataclasses, pytest, existing SAXS preprocessing policy and orchestrator contracts.

---

### Task 1: Define the replay application contract

**Files:**
- Modify: `polynexus/core/preprocess_optimization/replay.py`
- Test: `tests/test_preprocess_replay_contract.py`

- [ ] **Step 1: Write the failing contract test**

Add a replay-builder test that passes `apply_performed=True` and asserts the
serialized audit preserves that value.

- [ ] **Step 2: Run the focused test and verify RED**

Run `python -m pytest -q tests/test_preprocess_replay_contract.py -k application`.
Expected: collection succeeds and the new call fails because the builder does
not yet accept `apply_performed`.

- [ ] **Step 3: Implement the minimal contract change**

Add `apply_performed: bool = False` to the builder after the existing required
arguments and pass `bool(apply_performed)` to `PreprocessReplayAudit`.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run `python -m pytest -q tests/test_preprocess_replay_contract.py`.
Expected: all replay contract tests pass.

### Task 2: Bind SAXS replay rows to the final commit result

**Files:**
- Modify: `polynexus/orchestrator_preprocess.py`
- Test: `tests/test_saxs_ai_orchestrator_handoff.py`

- [ ] **Step 1: Write the failing SAXS regression tests**

Cover a calibrated auto-accept trial and a forced commit failure. Assert the
selected replay row uses the final decision and application flag, while the
engine remains unchanged after failure.

- [ ] **Step 2: Run the focused tests and verify RED**

Run `python -m pytest -q tests/test_saxs_ai_orchestrator_handoff.py -k replay_application`.
Expected: the success case reports `apply_performed=False`, and the failure
case retains a stale auto-accept replay decision.

- [ ] **Step 3: Implement the minimal orchestration change**

Track whether the selected candidate committed successfully. Move SAXS replay
row construction after the existing auto-commit/confirmation branch, pass the
final decision payload, and pass the tracked application flag only for the
selected candidate.

- [ ] **Step 4: Run focused SAXS tests and verify GREEN**

Run `python -m pytest -q tests/test_saxs_ai_orchestrator_handoff.py tests/test_preprocess_replay_contract.py`.
Expected: all focused tests pass with no new warnings.

### Task 3: Verify and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-31-saxs-ai-replay-application-binding.md`

- [ ] **Step 1: Run the exact SAXS matrix**

Run the repository's SAXS test matrix with an external test root when needed;
record the exact pass count, warnings, duration, and exit code.

- [ ] **Step 2: Run the structured verifier and storage dry-run**

Run `python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-ai-replay-application-binding.md --changed --types`, `python scripts/test_storage.py report --json`, and `python scripts/test_storage.py clean --older-than-hours 24 --json`.

- [ ] **Step 3: Review the allowlist and create one checkpoint**

Run `git diff --check`, inspect the cumulative diff, then call
`python scripts/auto_commit.py` with only the production files, focused tests,
and this task/spec/plan card. Do not include existing memory changes, scratch,
generated output, or test-storage directories.
