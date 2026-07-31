# SAXS AI Acceptance Audit Context Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development. Execute each task in order and checkpoint only the explicit allowlist.

**Goal:** Carry the existing SAXS scientific acceptance audit into the summary-only AI context without adding scientific authority.

**Architecture:** `saxs_ai_rescue.py` unwraps the existing engine/result boundary, projects the audit through a fixed summary whitelist, and keeps frame evidence on the established mode path. The existing PromptBuilder sanitizer consumes the same projection contract.

**Tech Stack:** Python, strict JSON mappings, existing SAXS evidence contracts, pytest.

---

### Task 1: Define the contract

- [x] Record source selection, strict whitelist, raw-data exclusions, and non-goals in the task/spec artifacts.

### Task 2: Write and run RED tests

**Files:** `tests/test_saxs_ai_acceptance_audit_context.py`, `tests/test_saxs_ai_live_context.py`

- [ ] Assert an existing static audit is projected and detached.
- [ ] Assert an engine wrapper exposes its existing temperature audit while retaining series evidence.
- [ ] Assert malformed/missing audits are omitted and raw/unknown fields do not enter the context.
- [ ] Run the new focused tests and capture the expected RED before implementation.

### Task 3: Implement the minimal GREEN projection

**Files:** `polynexus/core/saxs_engine/saxs_ai_rescue.py`, `polynexus/orchestrator_state.py`

- [ ] Unwrap mode-specific series results without changing existing frame selection.
- [ ] Project only the existing scientific audit summary fields and strict-JSON-safe nested summaries.
- [ ] Pass the existing engine boundary from live SAXS state so temperature/strain audits are available.
- [ ] Run focused tests and Advisor/prompt regressions.

### Task 4: Verify and checkpoint

- [ ] Run the focused audit/live/Advisor/prompt suite.
- [ ] Run the exact SAXS matrix and classify only complete pytest summaries as pass evidence.
- [ ] Run the structured task verifier, storage report, storage dry-run clean, and `git diff --check`.
- [ ] Review the disjoint diff and create one explicit allowlist checkpoint with `scripts/auto_commit.py`.
