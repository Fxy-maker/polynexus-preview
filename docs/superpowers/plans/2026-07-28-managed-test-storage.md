# Managed Test Storage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make pytest use an external per-run basetemp by default and provide safe stale-artifact reporting and cleanup.

**Architecture:** `conftest.py` calls pure path helpers from `scripts/test_storage.py` only when pytest has no explicit `--basetemp`. The storage CLI builds a read-only cleanup plan from legacy repository basetemps and managed run directories, then applies only candidates that pass Git, age, protected-path, and active-process checks.

**Tech Stack:** Python 3.12+, pytest configuration hooks, `pathlib`, `subprocess`, `argparse`, `pytest`.

---

### Task 1: Define safe storage contracts

**Files:**
- Create: `scripts/test_storage.py`
- Test: `tests/test_test_storage.py`

- [x] **Step 1: Write failing tests**

  Test `resolve_test_root` with an environment override and a project-drive
  default. Test legacy/managed artifact classification, retention eligibility,
  and active command-line path protection.

- [x] **Step 2: Run the focused tests**

  Run `pytest tests/test_test_storage.py -q` and observe import failures for the
  new module.

- [x] **Step 3: Implement pure helpers**

  Add typed artifact records, root resolution, legacy discovery, age checks, and
  active-path matching without deleting anything.

- [x] **Step 4: Run focused tests**

  Require `pytest tests/test_test_storage.py -q` to pass.

### Task 2: Wire pytest and CLI

**Files:**
- Create: `conftest.py`
- Modify: `pytest.ini`
- Modify: `scripts/test_storage.py`
- Modify: `tests/test_test_storage.py`

- [x] **Step 1: Add pytest hook and CLI tests**

  Assert that the hook leaves an explicit basetemp unchanged and assigns a
  unique managed path otherwise. Assert that report mode does not remove a
  directory and apply mode removes only an old eligible candidate.

- [x] **Step 2: Implement the hook and commands**

  Remove the repository-local `addopts --basetemp` setting. In the hook, assign
  one run directory under the resolved external pytest root. Add `report` and
  `clean` subcommands with `--root`, `--test-root`, `--older-than-hours`,
  `--apply`, and `--json` options.

- [x] **Step 3: Run focused verification**

  Run `pytest tests/test_test_storage.py -q` and the structured verifier using
  a dedicated external basetemp.

### Task 3: Document and checkpoint

**Files:**
- Modify: `AGENTS.md`
- Modify: `README.md`
- Modify: `docs/agent/tasks/2026-07-28-managed-test-storage.md`
- Modify: `docs/superpowers/specs/2026-07-28-managed-test-storage-design.md`
- Modify: `docs/superpowers/plans/2026-07-28-managed-test-storage.md`

- [x] **Step 1: Document standard commands**

  Document report/clean commands, the environment override, the default
  retention, and the explicit-basetemp exception.

- [x] **Step 2: Run the default verifier and inspect active processes**

  Confirm exact results and ensure the active pytest process's basetemp is not a
  cleanup candidate.

- [x] **Step 3: Apply only eligible stale cleanup**

  Run the dry-run report first, then use `--apply` with the approved retention
  threshold. Leave young, active, protected, and failed-removal paths intact.

- [x] **Step 4: Commit the explicit allowlist**

  Use `scripts/auto_commit.py` with only the storage implementation, hook,
  pytest config, tests, and process documentation.
