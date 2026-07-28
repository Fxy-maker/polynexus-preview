# SAXS strain-helper dirty-input guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reuse the existing deterministic q/I sanitizer at the strain phase
and void helper boundaries without changing their scientific calculations.

**Architecture:** Keep `sanitize_1d_profile()` as the only data-preparation
policy. Replace local helper arrays with its detached survivors, then run the
existing phase and void code unchanged. The series caller and quality contract
remain outside this atomic change.

**Tech Stack:** Python, NumPy, pytest, SAXS quality contracts, `verify.py`, and
`auto_commit.py`.

---

### Task 1: Write and run the failing regression

**Files:**
- Create: `tests/test_saxs_strain_helper_dirty_input.py`

- [ ] Write tests for dirty profiles, aligned-prefix mismatch, empty input, and
  caller-array immutability.
- [ ] Run the focused test file and confirm failures are the expected raw-input
  `TypeError`/`IndexError`, not test setup errors.

### Task 2: Apply the existing sanitizer at both helper boundaries

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_strain.py`

- [ ] Add `sanitized = sanitize_1d_profile(q, I)` at the start of each helper.
- [ ] Rebind only local `q` and `I` to `sanitized.q` and
  `sanitized.intensity`; leave thresholds, windows, gates, and result keys
  unchanged.
- [ ] Run the focused file and confirm all regression tests pass.

### Task 3: Verify compatibility and checkpoint

**Files:**
- Modify: task/spec/plan, acceptance note, and
  `docs/agent/memory/active-work.md` for exact evidence.

- [ ] Run the focused strain matrix, exact SAXS matrix, structured verifier,
  storage report, and `git diff --check`.
- [ ] Record any full/boundary limitation only from the actual command result.
- [ ] Create one `auto_commit.py` checkpoint using only the explicit allowlist.
