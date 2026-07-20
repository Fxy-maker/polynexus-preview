---
kind: task
status: completed
date: 2026-07-20
title: Add dry-run-first legacy worktree adoption
---

# Legacy worktree adoption

## Goal

Add an explicit `adopt-legacy` command that reports old Superpowers worktrees
and, only with `--apply`, archives dirty candidates or registers clean
`codex/*` candidates for cooldown-protected cleanup.

## Non-goals

- Do not delete worktrees or branches during adoption.
- Do not adopt paths outside the user-level PolyNexus Superpowers directory.
- Do not adopt the current repository worktree or non-`codex/*` branches.
- Do not overwrite existing registry records.

## Acceptance criteria

- [x] Default `adopt-legacy` is a read-only report.
- [x] `--apply` archives dirty candidates and registers them as `legacy_dirty`.
- [x] `--apply` registers clean candidates as `pending_cleanup` with a fresh
      cooldown, while preserving branch and HEAD metadata.
- [x] Existing `clean --apply` remains the only deletion path.
- [x] Focused tests and structured repository verification pass.

## Affected boundaries

- `scripts/worktree_manager.py` registry and lifecycle commands
- User-level structured WIP archives
- Worktree-management documentation and agent contract
- Worktree-manager regression tests

## Implementation plan

1. Add pure candidate filtering and adoption metadata helpers with failing
   tests first.
2. Add the dry-run/report and explicit apply CLI path.
3. Document the one-time migration command and its deletion boundary.
4. Run focused and repository verification, then commit only this task's files.

## Verification

```bash
pytest tests/test_worktree_manager.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-20-legacy-worktree-adoption.md --changed --types
python scripts/verify.py --changed --types
```

## Completion report

- Changed: added dry-run-first legacy candidate selection and explicit apply
  handling to `scripts/worktree_manager.py`; updated the agent contract and
  worktree-management guide; added focused regression coverage.
- Verification: `pytest tests/test_worktree_manager.py -q` passed (`8 passed`);
  structured verification passed, including `282` focused tests and `103`
  preprocessing tests.
- Runtime report: the current read-only scan found 47 eligible legacy
  candidates, including 3 dirty worktrees. No `--apply` operation was run.
- Safety: no registry, archive, worktree, or branch was changed by the report.
- Pre-existing changes left untouched: `.superpowers/`, the 2026-07-18 Origin
  drafts, and `.pytest_tmp_worktree_clean.txt`.
