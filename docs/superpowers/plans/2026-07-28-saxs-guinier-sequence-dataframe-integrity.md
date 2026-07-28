# SAXS Guinier sequence DataFrame integrity projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Each task keeps its own focused evidence and explicit allowlist checkpoint.

**Goal:** Make existing Guinier sequence integrity facts visible in the
temperature DataFrame without changing scientific analysis or evidence levels.

**Architecture:** Keep `GuinierSequenceEvidence` authoritative and add a
small private presentation adapter beside the existing DataFrame method. The
adapter copies only already-emitted fields; it does not inspect q/I data or
recompute source validity.

**Tech Stack:** Python, pandas, Pytest, strict JSON-compatible evidence DTOs,
`scripts/verify.py`, and `scripts/auto_commit.py`.

---

### Task 1: Write the failing DataFrame projection tests

**Files:**
- Modify: `tests/test_saxs_temperature_guinier_evidence.py`

- [ ] Add a regression with a diagnostic sequence payload asserting all ten
  projected integrity fields and checking that the caller-owned payload is
  unchanged.
- [ ] Add a regression with no sequence payload asserting one row remains and
  the new fields are empty.
- [ ] Run the focused tests with an external basetemp and record the expected
  RED failure for the missing columns.

### Task 2: Implement the read-only projection

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_temperature.py`

- [ ] Add a private index-field formatter and sequence-evidence projection
  helper with fixed keys and deterministic `|` formatting.
- [ ] Merge the helper into the existing `TempSeriesResult.to_dataframe()` row
  after the current sequence level/reason fields.
- [ ] Preserve explicit boolean `False`, empty values, row order, and all
  existing columns.

### Task 3: Run focused GREEN and compatibility checks

**Files:**
- Modify: task/spec/plan and `docs/agent/memory/active-work.md` only for
  evidence records.

- [ ] Run the focused temperature/DataFrame matrix and exact `test_saxs_*.py`
  matrix with external basetemps.
- [ ] Run `python scripts/verify.py --task ... --changed --types` and
  `git diff --check`; classify timeouts/no-summary results as limitations.
- [ ] Update the task card and active memory with exact counts and untouched
  pre-existing paths.

### Task 4: Create the atomic checkpoint

- [ ] Review `git diff --stat`, `git diff --check`, and the explicit allowlist.
- [ ] Run `python scripts/auto_commit.py --message "feat(saxs): expose Guinier sequence integrity" --files ...` with only the listed files.
- [ ] Report the actual commit hash and leave the overall goal active.
