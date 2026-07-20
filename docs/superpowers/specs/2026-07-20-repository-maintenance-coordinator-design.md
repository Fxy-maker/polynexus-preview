---
kind: design
status: approved
date: 2026-07-20
title: Local repository maintenance coordinator
---

# Local repository maintenance coordinator

## Goal

Reduce routine agent-development work by providing one local command that
verifies a task, creates an allowlisted checkpoint commit, fast-forward merges
the source branch into a local target branch, and invokes the existing safe
worktree cleanup rules.

## Scope

The coordinator is a repository-local Python command. It does not call an AI
model and does not replace the future autonomous development loop. It composes
`scripts/verify.py`, `scripts/auto_commit.py`, and
`scripts/worktree_manager.py`.

The operation is local-only: it never pushes, deploys, deletes branches, or
uses `git add .`. The default target branch is `main`; merging is
`git merge --ff-only`, so a non-linear integration stops for human resolution.

## Flow

```text
preflight source and target
        |
verify --changed --types
        |
auto_commit.py --files <explicit allowlist>
        |
target worktree clean? ---- no ---> stop without merge
        |
git merge --ff-only <source branch>
        |
finish registered agent worktree + clean eligible worktrees
```

## Safety rules

- The source worktree must not have staged changes before the operation.
- The target worktree must be a distinct, existing worktree on the requested
  branch and must be clean before merging.
- The commit allowlist is passed unchanged to `auto_commit.py`.
- A failed verification or merge leaves the source commit/worktree intact and
  returns a non-zero exit code.
- Cleanup remains delegated to `worktree_manager.py`, including ownership,
  clean-state, branch/HEAD matching, archive, and cooldown checks.
- A registered agent-owned source worktree is marked `pending_cleanup` only
  after a successful merge; the default one-hour cooldown still applies.

## Test boundary

Pure command construction, worktree porcelain parsing, target resolution, and
preflight safety checks are unit tested. The existing repository verifier and
the focused script tests provide the final integration gate.
