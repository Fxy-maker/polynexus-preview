# SAXS Condition Path-Candidate Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recover valid SAXS condition directories even when an earlier parent directory contains an invalid matching token.

**Architecture:** Keep `recover_condition_axis()` precedence and the existing pattern contract. Change only `_parse_condition_detail()` so path patterns validate each path component before accepting it, while filename patterns remain single-candidate.

**Tech Stack:** Python, pathlib, regular expressions, pytest, SAXS IO, `verify.py`, and `auto_commit.py`.

---

### Task 1: Reproduce the path-candidate failure

**Files:**
- Test: `tests/test_saxs_condition_recovery.py`

- [x] Run the directory-source regression with an external basetemp and confirm
  the expected unresolved-source assertion failure.
- [x] Run the metadata regression and confirm it fails for the same unresolved
  cause.

### Task 2: Validate each path component before accepting it

**Files:**
- Modify: `polynexus/core/saxs_engine/io.py:_parse_condition_detail`

- [x] Set `path_parts = entry.parts` for `search_path` patterns and `(entry.stem,)` otherwise.
- [x] For each part, retain the existing regex capture, lookup, numeric conversion, and validator expressions; continue only the part loop when a candidate is unusable.
- [x] Return the existing source, key, text, confidence, and value payload for the first valid candidate.

### Task 3: Verify and checkpoint

**Files:**
- Modify: task card, acceptance note, and durable active-work memory.

- [x] Run focused condition tests and the exact SAXS matrix, then run the task-scoped structured verifier and `git diff --check`.
- [x] Run storage report and dry-run cleanup; record that no test data was deleted.
- [x] Create one local checkpoint with `scripts/auto_commit.py` and exactly the explicit changed-file allowlist.
