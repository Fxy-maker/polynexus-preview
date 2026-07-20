# Legacy Worktree Adoption Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dry-run-first command that safely adopts eligible legacy Superpowers worktrees into the existing lifecycle registry.

**Architecture:** Extend `scripts/worktree_manager.py` with pure candidate-selection and metadata helpers, then add an `adopt-legacy` CLI command. The command only writes registry/archive metadata when `--apply` is explicit; deletion remains exclusively delegated to the existing cooldown-checked `clean --apply` path.

**Tech Stack:** Python 3.12+, `argparse`, JSON registry, Git porcelain records, `pytest`.

---

### Task 1: Define candidate and adoption contracts

**Files:**
- Modify: `scripts/worktree_manager.py`
- Modify: `tests/test_worktree_manager.py`

- [x] **Step 1: Write failing tests**

  Add tests proving that only unregistered paths under `REGISTRY_ROOT` with a
  `codex/` branch are candidates, and that current-root, non-codex, registered,
  and outside-root records are excluded. Add tests for clean and dirty adoption
  metadata, including `pending_cleanup` versus `legacy_dirty`.

- [x] **Step 2: Run the focused tests**

  Run `pytest tests/test_worktree_manager.py -q` and observe the expected import
  failures for the new helpers.

- [x] **Step 3: Implement pure helpers**

  Add `legacy_candidates(records, registry, current_root, managed_root)` and
  `adoption_metadata(record, task, dirty, now)` without touching the filesystem.

- [x] **Step 4: Run focused tests**

  Run `pytest tests/test_worktree_manager.py -q` and require all tests to pass.

### Task 2: Add report/apply command

**Files:**
- Modify: `scripts/worktree_manager.py`
- Modify: `tests/test_worktree_manager.py`

- [x] **Step 1: Add CLI behavior tests**

  Test that report mode does not save registry state and that apply mode writes
  clean adoption metadata while routing dirty candidates through the existing
  archive function.

- [x] **Step 2: Implement `adopt-legacy`**

  Add `--apply`, `--json`, and `--task-prefix` options. Report path, branch,
  HEAD, dirty state, and proposed action. In apply mode, archive dirty records,
  save `legacy_dirty` metadata, and save `pending_cleanup` metadata for clean
  records with `finished_at` set to the adoption time.

- [x] **Step 3: Run focused verification**

  Run `pytest tests/test_worktree_manager.py -q` and
  `python scripts/verify.py --task docs/agent/tasks/2026-07-20-legacy-worktree-adoption.md --changed --types`.

### Task 3: Document and checkpoint

**Files:**
- Modify: `AGENTS.md`
- Modify: `docs/agent/worktree-management.md`
- Modify: `docs/agent/tasks/2026-07-20-legacy-worktree-adoption.md`
- Modify: `docs/superpowers/specs/2026-07-20-legacy-worktree-adoption-design.md`
- Modify: `docs/superpowers/plans/2026-07-20-legacy-worktree-adoption.md`

- [x] **Step 1: Document the command**

  Add the dry-run and explicit apply examples, and state that adoption never
  deletes anything and that `clean --apply` remains the deletion boundary.

- [x] **Step 2: Run the default verifier**

  Run `python scripts/verify.py --changed --types` and inspect the full output.

- [x] **Step 3: Commit the allowlist**

  Use `scripts/auto_commit.py` with only the manager, its tests, the contract,
  and the four process documents.
