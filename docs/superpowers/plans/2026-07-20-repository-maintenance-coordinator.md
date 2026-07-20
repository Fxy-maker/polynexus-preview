# Repository Maintenance Coordinator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local-only command for verify → allowlisted commit → fast-forward merge → safe worktree cleanup.

**Architecture:** `scripts/repo_maintenance.py` owns orchestration and Git preflight checks. Existing `verify.py`, `auto_commit.py`, and `worktree_manager.py` remain the policy owners for verification, commit allowlists, and cleanup eligibility. Unit tests exercise pure parsing and safety helpers without mutating the real repository.

**Tech Stack:** Python 3.12+, `argparse`, `subprocess`, `pytest`, Git worktree porcelain output.

---

### Task 1: Define the coordinator contracts

**Files:**
- Create: `scripts/repo_maintenance.py`
- Test: `tests/test_repo_maintenance.py`

- [x] **Step 1: Write the failing tests**

  Add tests for `build_verify_command`, `parse_worktree_records`,
  `find_worktree_for_branch`, and `preflight_errors`. The tests must assert
  that verification includes `--changed --types`, target lookup returns the
  exact branch worktree, and staged/dirty-target conditions produce explicit
  errors.

- [x] **Step 2: Run the focused tests**

  Run `pytest tests/test_repo_maintenance.py -q`.

  Expected result before implementation: import errors for the missing module
  or missing helper functions.

- [x] **Step 3: Implement the pure helpers**

  Define typed helpers for building the verifier command, parsing `git worktree
  list --porcelain`, selecting a target record, and returning preflight errors.
  Keep all paths as `Path` values at the boundary and all subprocess arguments
  as lists rather than shell strings.

- [x] **Step 4: Run the focused tests again**

  Run `pytest tests/test_repo_maintenance.py -q` and require all tests to pass.

### Task 2: Compose the local finish operation

**Files:**
- Modify: `scripts/repo_maintenance.py`
- Modify: `tests/test_repo_maintenance.py`

- [x] **Step 1: Add subprocess composition tests**

  Test the operation with monkeypatched command execution so the assertions
  verify this order: verifier, `auto_commit.py`, target `git merge --ff-only`,
  optional registered-worktree finish, and cleanup. Add a failure test proving
  a dirty target prevents the merge command from being called.

- [x] **Step 2: Run the focused tests and observe the new failures**

  Run `pytest tests/test_repo_maintenance.py -q`. The new orchestration tests
  should fail until `finish` and its command wrappers exist.

- [x] **Step 3: Implement the CLI**

  Add `finish` arguments for `--root`, `--target`, `--files`, `--message`,
  `--task`, `--full`, `--boundary`, `--cleanup`, and
  `--cooldown-hours`. Require a clean staging area, locate a distinct clean
  target worktree, invoke verification, invoke `auto_commit.py`, merge the
  source branch with `--ff-only`, then delegate cleanup. Return non-zero on
  every failed subprocess and print each phase.

- [x] **Step 4: Run focused and structured verification**

  Run:

  ```bash
  pytest tests/test_repo_maintenance.py -q
  python scripts/verify.py --task docs/agent/tasks/2026-07-20-repository-maintenance-coordinator.md --changed --types
  ```

  Require exit code 0 and record the exact test counts in the task card.

### Task 3: Complete the checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-20-repository-maintenance-coordinator.md`
- Modify: `docs/superpowers/specs/2026-07-20-repository-maintenance-coordinator-design.md`
- Modify: `docs/superpowers/plans/2026-07-20-repository-maintenance-coordinator.md`

- [x] **Step 1: Run the default verifier**

  Run `python scripts/verify.py --changed --types` and inspect the full output.

- [x] **Step 2: Review the allowlist and diff**

  Confirm only the coordinator, its focused tests, and the three new process
  artifacts changed. Leave all pre-existing untracked files untouched.

- [x] **Step 3: Create the automatic checkpoint**

  Run:

  ```bash
  python scripts/auto_commit.py --message "feat(agent): add local repository maintenance coordinator" --files scripts/repo_maintenance.py tests/test_repo_maintenance.py docs/agent/tasks/2026-07-20-repository-maintenance-coordinator.md docs/superpowers/specs/2026-07-20-repository-maintenance-coordinator-design.md docs/superpowers/plans/2026-07-20-repository-maintenance-coordinator.md
  ```

  Require a successful commit and no push.
