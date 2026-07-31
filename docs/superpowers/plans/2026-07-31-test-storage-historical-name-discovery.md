# Historical Test Storage Name Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the test-storage inventory discover known historical PolyNexus test directories without weakening protected-path gates.

**Architecture:** Keep classification in `scripts/test_storage.py` at the existing `_is_known_legacy_name()` boundary. Exercise discovery through `discover_artifacts()` so the tests cover the public inventory behavior and protected-name precedence.

**Tech Stack:** Python, pytest, PowerShell CLI checks.

---

### Task 1: Add the discovery regression

**Files:**
- Modify: `tests/test_test_storage.py`

- [x] **Step 1: Write the failing test**

Add one discovery test containing the six observed disposable naming families and protected `测试数据`, review, evidence, baseline, and archive names.

- [x] **Step 2: Run the focused test**

Run `python -m pytest -q tests/test_test_storage.py::test_discover_historical_test_directories_but_protects_data_and_evidence -vv`.

Expected result before implementation: one failure showing the new families are missing from the discovered artifact list.

### Task 2: Implement bounded name matching

**Files:**
- Modify: `scripts/test_storage.py:523-535`

- [x] **Step 1: Add protected-name precedence**

Return `False` for the exact `测试数据` directory and existing protected words before evaluating test patterns.

- [x] **Step 2: Add the six historical families**

Recognize the explicit prefixes and family markers from the regression test while preserving all existing patterns.

- [x] **Step 3: Run focused and full storage tests**

Run `python -m pytest -q tests/test_test_storage.py` and require zero failures.

### Task 3: Review inventory and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-31-test-storage-historical-name-discovery.md`
- Modify: `docs/agent/memory/current-state.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] **Step 1: Run repository checks**

Run `python scripts/task_check.py --task docs/agent/tasks/2026-07-31-test-storage-historical-name-discovery.md`, `python scripts/verify.py --task docs/agent/tasks/2026-07-31-test-storage-historical-name-discovery.md --changed --types`, and `git diff --check`.

- [x] **Step 2: Run non-destructive storage review**

Run `python scripts/test_storage.py report --json` and `python scripts/test_storage.py clean --older-than-hours 24 --json`. Review every eligible path before any separately authorized `--apply`.

- [x] **Step 3: Create the explicit checkpoint**

Run `python scripts/auto_commit.py --message "fix(test-storage): discover historical test directories" --files scripts/test_storage.py tests/test_test_storage.py docs/superpowers/specs/2026-07-31-test-storage-historical-name-discovery-design.md docs/superpowers/plans/2026-07-31-test-storage-historical-name-discovery.md docs/agent/tasks/2026-07-31-test-storage-historical-name-discovery.md`.
