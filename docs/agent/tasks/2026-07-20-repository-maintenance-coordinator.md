---
kind: task
status: completed
date: 2026-07-20
title: Add local repository maintenance coordinator
---

# Local repository maintenance coordinator

## Goal

Add one local command that verifies an atomic task, commits only its explicit
files, fast-forward merges the task branch into local `main`, and runs the
existing safe worktree cleanup.

## Non-goals

- Do not call an AI model or implement the autonomous coding loop.
- Do not push, deploy, delete branches, or use `git add .`.
- Do not auto-merge a dirty target or resolve non-fast-forward history.
- Do not alter business code or existing worktree ownership records.

## Acceptance criteria

- [x] `scripts/repo_maintenance.py finish` composes verification, allowlisted
      commit, local fast-forward merge, and safe cleanup in that order.
- [x] Staged source changes, a missing target branch, a dirty target worktree,
      and a non-fast-forward merge stop without silently changing unrelated
      files.
- [x] Tests cover command construction, porcelain parsing, target selection,
      and the safety checks.
- [x] `python scripts/verify.py --task docs/agent/tasks/2026-07-20-repository-maintenance-coordinator.md --changed --types`
      passes.

## Affected boundaries

- Repository-local development scripts
- Agent task and design documentation
- Focused script regression tests
- Local Git worktree and branch integration commands

## Implementation plan

1. Add the approved design and task card, then validate the task card.
2. Write failing unit tests for command construction, worktree parsing, and
   preflight safety decisions.
3. Implement the coordinator with subprocess boundaries that preserve explicit
   arguments and delegate commit and cleanup policy to existing helpers.
4. Run focused tests, structured verification, and the default verification;
   commit only the coordinator, tests, and this task documentation.

## Verification

```bash
pytest tests/test_repo_maintenance.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-20-repository-maintenance-coordinator.md --changed --types
python scripts/verify.py --changed --types
```

## Checkpoints

1. Pure coordinator helpers and focused tests.
2. CLI composition and structured verification.

## Completion report

- Changed: added `scripts/repo_maintenance.py`, six focused tests, and the
  task/spec/plan documentation; updated `AGENTS.md` with the usage contract.
- Verification: `pytest tests/test_repo_maintenance.py -q` passed (`6 passed`);
  both structured and default `python scripts/verify.py --changed --types`
  checks passed, including `282` focused tests and `103` preprocessing tests.
- Limitation: the coordinator's real merge command was not run against this
  worktree because the source branch contains existing history and the local
  `main` worktree is a separate integration point; the command ordering and
  safety stops are covered by focused tests.
- Pre-existing changes left untouched: `.superpowers/`, the 2026-07-18
  Origin design/task drafts, and `.pytest_tmp_worktree_clean.txt`.
