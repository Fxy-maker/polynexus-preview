# SAXS melting-window status dirty-input guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `classify_melting_window_status()` tolerate dirty scalar and temperature-sequence inputs without changing its existing status/reason contract.

**Architecture:** Coerce consumed scalars with `_coerce_optional_float()`, normalize the optional temperature sequence through `_as_1d_float_array()` inside the existing margin helper, and preserve all classification branches unchanged.

**Tech Stack:** Python, NumPy, pytest, SAXS temperature analysis, `verify.py`, and `auto_commit.py`.

---

### Task 1: Write and run the failing regression

**Files:**
- Create: `tests/test_saxs_melting_window_status_dirty_input.py`

- [x] Add tests for numeric strings, malformed/non-finite Tm values, dirty
  temperature sequences, margin/expected-melt behavior, clean equivalence,
  and caller immutability.
- [x] Run the focused regression and record the expected pre-fix failures.

### Task 2: Apply the minimal evidence-boundary guard

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_temperature.py:298-386`

- [x] Replace direct temperature-sequence casting in `_temperature_window_margin()` with existing detached coercion.
- [x] Coerce classifier scalar inputs with `_coerce_optional_float()`.
- [x] Leave floors, sequence statuses, reason codes, and expected-melt branch logic unchanged.
- [x] Run the focused regression and confirm GREEN.

### Task 3: Verify, document, and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-28-saxs-melting-window-status-dirty-input-guard.md`
- Modify: `docs/superpowers/specs/2026-07-28-saxs-melting-window-status-dirty-input-guard-design.md`
- Modify: `docs/superpowers/plans/2026-07-28-saxs-melting-window-status-dirty-input-guard.md`
- Create: `docs/acceptance/2026-07-28-saxs-melting-window-status-dirty-input-guard.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] Run focused, temperature, exact SAXS, structured verifier, targeted
  lint/compile, diff, and storage report/dry-run checks.
- [x] Record unrelated changed-file verifier limitations if present and create
  one explicit allowlist checkpoint.
