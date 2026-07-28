# SAXS Gibbs-Thomson dirty-input guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reuse the existing numeric coercion policy at the public
Gibbs-Thomson temperature/lc boundary without changing its scientific fit.

**Architecture:** Coerce both arrays into detached float arrays, align the
common prefix, and pass them through the current finite/positive mask and fit
body. No new missing-data policy or physical threshold is introduced.

**Tech Stack:** Python, NumPy, pytest, SAXS temperature analysis, `verify.py`,
and `auto_commit.py`.

---

### Task 1: Write and run the failing regression

**Files:**
- Create: `tests/test_saxs_gibbs_thomson_dirty_input.py`

- [ ] Add malformed-token, non-finite/non-positive, mismatched-length, clean
  survivor, empty-input, and immutability assertions.
- [ ] Run the focused test file and confirm the expected raw `TypeError` or
  mismatch failure before production code changes.

### Task 2: Apply existing numeric coercion at the helper boundary

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_temperature.py`

- [ ] Import the existing `_as_1d_float_array()` helper.
- [ ] Coerce and align local temperature/lc arrays before the current valid
  mask; leave the fit body, gates, and result dictionary unchanged.
- [ ] Run the focused regression and confirm GREEN.

### Task 3: Verify compatibility and checkpoint

**Files:**
- Modify: task/spec/plan, acceptance note, and
  `docs/agent/memory/active-work.md` for exact evidence.

- [ ] Run temperature, exact SAXS, structured verifier, diff, and storage
  dry-run checks.
- [ ] Record any full/boundary limitation only from actual command output.
- [ ] Create one `auto_commit.py` checkpoint using exactly the allowlist.
